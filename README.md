# Binance Futures 실시간 데이터 파이프라인

Binance 선물 거래소의 실시간 호가 데이터를 수집하고, Kafka를 통해 Spark로 스트리밍 처리하는 데이터 파이프라인입니다.

## 아키텍처

```
Binance WebSocket ──→ Python Collector ──→ Kafka ──→ Spark Streaming ──→ ClickHouse
   (실시간 호가)        (데이터 수집)       (메시지 큐)    (스트림 처리)       (저장/분석)
```

| 컴포넌트 | 역할 | 기술 |
|---------|------|------|
| **Collector** | Binance WebSocket에서 실시간 데이터 수집 → Kafka 전송 | Python, websockets, kafka-python |
| **Kafka** | 메시지 브로커 (데이터 버퍼링 및 전달) | Confluent Kafka 7.3.0, ZooKeeper |
| **Spark** | Kafka에서 Micro-Batch로 데이터를 읽어 파싱/집계 | Spark 3.3.0 (Structured Streaming) |
| **ClickHouse** | 처리된 데이터 저장 및 분석 쿼리 | ClickHouse (column-oriented DB) |

## 프로젝트 구조

```
boaz/
├── collectors/                  # 데이터 수집기
│   ├── base_collector.py        #   WebSocket 연결 + Kafka 전송 (추상 클래스)
│   └── bookticker_depth.py      #   호가 Depth 수집기
├── common/                      # 공통 모듈
│   ├── config.py                #   설정 (Kafka 서버, 토픽 매핑)
│   └── kafka_utils.py           #   Kafka Producer 래퍼 (싱글톤)
├── utils/
│   └── binance_stream_enum.py   #   Binance 스트림 타입 Enum
├── spark_jobs/                  # Spark 작업
│   ├── kafka_reader.py          #   Kafka → Spark 스트리밍 읽기/파싱
│   ├── stream_aggregator.py     #   (예정) 1분봉 집계
│   ├── whale_detector.py        #   (예정) 고래 거래 감지
│   └── log4j.properties         #   Spark 로그 설정
├── infra/                       # 인프라 스크립트
│   ├── setup-kafka.sh           #   Kafka 토픽 생성 + 상태 검증
│   └── manage-kafka.sh          #   Kafka 관리 도구 (토픽 조회, 메시지 확인 등)
├── database/
│   └── clickhouse_schema.sql    #   ClickHouse 테이블 스키마
├── scripts/                     # 실행 스크립트
│   ├── start.sh                 #   전체 서비스 시작 (--clean 옵션 지원)
│   └── start-spark-job.sh       #   Spark Job 실행
├── tests/                       # Binance 스트림별 테스트 스크립트
├── docker-compose.yml           # Docker 서비스 정의
└── requirements.txt             # Python 의존성
```

## 사전 요구사항

- **Docker** & **Docker Compose**
- **Python 3.10+**

## 빠른 시작

### 1. Python 가상환경 설정

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 전체 서비스 시작

```bash
# 일반 시작 (Docker 서비스 + Kafka 토픽 생성 + Spark 준비)
./scripts/start.sh

# 클린 시작 (모든 데이터 초기화 후 시작) ← 문제 발생 시 권장
./scripts/start.sh --clean
```

이 스크립트가 자동으로 수행하는 작업:
1. Docker 컨테이너 실행 (Kafka, ZooKeeper, Spark, ClickHouse)
2. Kafka 준비 대기 및 상태 검증 (Topic ID 불일치 자동 복구)
3. Kafka 토픽 생성 (`binance-depth`)
4. Spark Master/Worker 상태 확인

### 3. 데이터 수집 시작

```bash
source venv/bin/activate
python3 -m collectors.bookticker_depth
```

정상 동작 시 출력:
```
🚀 BookTickerDepthCollector 시작 | 구독: [<BinanceStreamType.DEPTH: 'depth@100ms'>]
📥 [11:17:14] btcusdt@depth@100ms 샘플 데이터 확인
⏱️ TPS: 9.07 msgs/sec | 누적: 200
```

### 4. Spark Job 실행

새 터미널을 열고:
```bash
./scripts/start-spark-job.sh
```

정상 동작 시 출력:
```
+-------+---------+---------+--------------------+
| symbol|bid_price|ask_price|     kafka_timestamp|
+-------+---------+---------+--------------------+
|BTCUSDT|  68970.0|  68971.3|2026-02-11 02:18:...|
+-------+---------+---------+--------------------+
```

## 데이터 흐름 상세

### Collector → Kafka

1. `BookTickerDepthCollector`가 Binance Futures WebSocket (`wss://fstream.binance.com`)에 연결
2. `btcusdt@depth@100ms` 스트림 구독 (100ms 간격 호가 변경 데이터)
3. 수신 데이터를 JSON 직렬화하여 `binance-depth` 토픽으로 전송
4. 배치 최적화: `batch_size=32KB`, `linger_ms=10`, `gzip` 압축

Kafka 메시지 형식:
```json
{
  "symbol": "BTCUSDT",
  "stream": "btcusdt@depth@100ms",
  "data": {
    "e": "depthUpdate",
    "b": [["68970.00", "1.500"], ...],
    "a": [["68971.30", "2.000"], ...]
  },
  "ts": 1739233095000
}
```

### Kafka → Spark

1. Spark Structured Streaming이 `binance-depth` 토픽을 구독 (Micro-Batch 모드)
2. 1초마다 배치를 가져와 JSON 파싱
3. bid/ask price를 추출하여 콘솔에 출력 (이후 ClickHouse 저장 예정)

## Kafka 관리 도구

```bash
# 토픽 목록 조회
./infra/manage-kafka.sh list

# 토픽 상세 정보 (파티션, 리더, ISR)
./infra/manage-kafka.sh describe binance-depth

# 메시지 수신 확인 (최근 5개)
./infra/manage-kafka.sh consume binance-depth 5

# 토픽 오프셋 정보
./infra/manage-kafka.sh offsets binance-depth

# Consumer Group Lag 확인
./infra/manage-kafka.sh lag
```

## 웹 UI

| 서비스 | URL |
|--------|-----|
| Spark Master | http://localhost:8080 |
| ClickHouse HTTP | http://localhost:8123 |

## Docker 서비스

| 서비스 | 이미지 | 포트 |
|--------|--------|------|
| ZooKeeper | confluentinc/cp-zookeeper:7.3.0 | 2181 (내부) |
| Kafka | confluentinc/cp-kafka:7.3.0 | 9092 (외부), 29092 (내부) |
| Spark Master | apache/spark-py:v3.3.0 | 8080, 7077 |
| Spark Worker | apache/spark-py:v3.3.0 | - |
| ClickHouse | clickhouse/clickhouse-server:latest | 8123, 9000 |

## 트러블슈팅

### Kafka `NotLeaderForPartitionError`

**원인**: 토픽을 삭제/재생성했을 때 `data/kafka/`에 이전 Topic ID 로그가 남아있으면 발생

**해결**:
```bash
./scripts/start.sh --clean
```

### Spark에서 데이터를 못 읽는 경우

1. Collector가 실행 중인지 확인
2. Kafka에 데이터가 있는지 확인: `./infra/manage-kafka.sh consume binance-depth 3`
3. 데이터가 없으면 Kafka 상태 확인: `./infra/manage-kafka.sh describe binance-depth`

### 서비스 전체 재시작

```bash
docker-compose down
./scripts/start.sh --clean
```
