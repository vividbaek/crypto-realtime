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

**Depth + 1분봉 + aggTrade 동시 수집** (1분봉·agg 데이터 확인용):

```bash
python3 -m collectors.depth_kline_aggtrade
```

- `binance-depth`: 호가 (고빈도)
- `binance-kline`: Binance 1분봉 (이미 1분 집계)
- `binance-trade`: aggTrade 체결

메시지 확인: `./infra/manage-kafka.sh consume binance-kline 3`, `./infra/manage-kafka.sh consume binance-trade 3`

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

**기본 (depth → 콘솔):**
```bash
./scripts/start-spark-job.sh
```
- `binance-depth` 구독 → bid/ask 파싱 → 1초마다 콘솔 출력

**전처리 (aggTrade → 1분봉 집계):**
```bash
./scripts/start-spark-job.sh preprocess
```
- `binance-trade`(aggTrade) 구독 → 1분 tumbling window로 OHLCV 집계 → 1분마다 콘솔 출력 (이후 ClickHouse 적재 확장 가능)

**데이터 초기화 후 1분봉 비교 (우리 집계 vs Binance 1분봉):**
1. `./scripts/start.sh --clean` — Kafka·Spark 체크포인트 초기화
2. 터미널 1: `python3 -m collectors.depth_kline_aggtrade` — 스트림 수집 → Kafka 적재
3. 터미널 2: `./scripts/start-spark-job.sh preprocess` — 초당(aggTrade) 데이터로 1분봉 정제 출력
4. 터미널 3: `python3 scripts/compare_binance_kline.py` — Kafka의 Binance 1분봉(kline_1m)을 봉 닫힐 때만 출력

같은 `window_start`(분) 기준으로 터미널 2(우리 1분봉)와 터미널 3(Binance 1분봉) 숫자를 비교하면 전처리 검증 가능.

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

### Spark submit 시 Ivy FileNotFoundException (`.ivy2/cache/...`)

**원인**: Ivy 캐시 디렉터리(`data/spark-ivy`)가 없거나 컨테이너에서 쓸 수 없음.

**해결**:
```bash
mkdir -p data/spark-ivy/cache data/spark-ivy/jars
chmod -R 777 data/spark-ivy
./scripts/start-spark-job.sh preprocess
```
그래도 실패하면: `sudo chmod -R 777 data/spark-ivy` 또는 `rm -rf data/spark-ivy` 후 다시 실행.

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

### 도커 재시작 후 "토픽이 안 맞아서" / 브로커 쪽 에러 (Topic ID 불일치)

**원인**: 토픽 이름·브로커 주소는 코드/설정으로 고정되어 **실행할 때마다 바뀌지 않습니다.**  
다만 `--clean` 또는 `data/kafka` 삭제 후 Kafka를 다시 띄우면 **토픽이 새 ID로 생성**되고, Spark 체크포인트에는 **예전 토픽 ID**가 남아 있습니다. Spark가 그 체크포인트로 브로커에 요청하면 브로커가 "topic ID does not match"로 거절합니다.

**해결**:

- **`./scripts/start.sh --clean`** 사용 시: Spark 체크포인트를 자동으로 삭제하도록 되어 있으므로, 재시작 후 다시 수집기·Spark Job만 실행하면 됩니다.
- **수동으로 Kafka만 초기화한 경우**: Spark 체크포인트를 지운 뒤 Spark Job을 다시 실행하세요.
  ```bash
  docker exec spark-master rm -rf /tmp/checkpoint-*
  ./scripts/start-spark-job.sh
  ```

### 서비스 전체 재시작

```bash
docker-compose down
./scripts/start.sh --clean
```
