# Binance 실시간 데이터 파이프라인

Binance WebSocket으로부터 실시간 암호화폐 데이터를 수집하여 Kafka에 저장하고, Spark로 처리하는 실시간 데이터 파이프라인 프로젝트입니다.

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [아키텍처](#아키텍처)
- [사전 요구사항](#사전-요구사항)
- [설치 방법](#설치-방법)
- [시작 방법](#시작-방법)
- [사용법](#사용법)
- [프로젝트 구조](#프로젝트-구조)
- [문제 해결](#문제-해결)

## 🎯 프로젝트 개요

이 프로젝트는 다음과 같은 기능을 제공합니다:

- **실시간 데이터 수집**: Binance WebSocket API를 통해 실시간 암호화폐 시장 데이터 수집
- **데이터 스트리밍**: Kafka를 통한 고성능 데이터 스트리밍
- **데이터 처리**: Spark를 활용한 실시간 및 배치 데이터 처리
- **확장 가능한 아키텍처**: 마이크로서비스 기반의 확장 가능한 구조

## 🏗️ 아키텍처

```
┌─────────────┐
│   Binance   │
│  WebSocket  │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Python    │─────▶│    Kafka    │─────▶│    Spark    │
│  Collector  │      │   (Topic)   │      │  Processor  │
└─────────────┘      └─────────────┘      └─────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────┐
                                            │ ClickHouse  │
                                            │  (Storage)  │
                                            └─────────────┘
```

### 데이터 흐름

1. **수집 단계**: Python Collector가 Binance WebSocket에서 실시간 데이터 수신
2. **스토리징 단계**: 수집된 데이터를 Kafka 토픽에 저장
3. **처리 단계**: Spark가 Kafka에서 데이터를 읽어 실시간 처리
4. **저장 단계**: 처리된 데이터를 ClickHouse에 저장 (향후 구현)

## 📦 사전 요구사항

- **Docker** (20.10 이상)
- **Docker Compose** (2.0 이상)
- **Python** (3.8 이상)
- **Linux/macOS/WSL2** (Windows는 WSL2 권장)

## 🚀 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd boaz
```

### 2. Python 패키지 설치

```bash
# 가상환경 생성 (선택사항)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 스크립트 실행 권한 부여

```bash
chmod +x scripts/*.sh
chmod +x infra/*.sh
```

## 🎬 시작 방법

### 빠른 시작 (권장)

```bash
# 1. 전체 인프라 시작 (Docker + Kafka 토픽 생성)
./scripts/start.sh

# 2. 데이터 수집기 시작 (새 터미널)
source venv/bin/activate
python3 -m collectors.bookticker_depth
```

### 단계별 시작

#### 1단계: Docker 서비스 시작

```bash
docker-compose up -d
```

#### 2단계: Kafka 준비 대기

```bash
# Kafka가 완전히 시작될 때까지 대기 (약 30초)
sleep 30

# Kafka 상태 확인
docker-compose logs kafka | tail -20
```

#### 3단계: Kafka 토픽 생성

```bash
./infra/setup-kafka.sh
```

#### 4단계: 데이터 수집기 시작

```bash
source venv/bin/activate
python3 -m collectors.bookticker_depth
```

#### 5단계: (선택) Spark로 데이터 읽기

```bash
docker exec -it spark-master bash -c "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars && IVY_CACHE_DIR=/tmp/.ivy2 /opt/spark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1 /opt/spark/work-dir/kafka_reader.py"
```

## 📖 사용법

### 데이터 수집기 실행

```bash
# 기본 실행 (BTCUSDT depth 데이터)
python3 -m collectors.bookticker_depth

# 다른 심볼 사용하려면 코드 수정 필요
```

### Kafka 관리

```bash
# 토픽 목록 조회
./infra/manage-kafka.sh list

# 토픽 상세 정보
./infra/manage-kafka.sh describe binance-depth

# 메시지 수신 (테스트)
./infra/manage-kafka.sh consume binance-depth 5

# 오프셋 확인
./infra/manage-kafka.sh offsets binance-depth

# Consumer Group 목록
./infra/manage-kafka.sh groups

# Consumer Lag 확인
./infra/manage-kafka.sh lag
```

### Spark 작업 실행

```bash
# Kafka Reader 실행
docker exec -it spark-master bash -c "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars && IVY_CACHE_DIR=/tmp/.ivy2 /opt/spark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1 /opt/spark/work-dir/kafka_reader.py"
```

### 웹 UI 접속

- **Spark Master**: http://localhost:8080
- **ClickHouse**: http://localhost:8123

## 📁 프로젝트 구조

```
boaz/
├── collectors/          # 데이터 수집기
│   ├── base_collector.py      # 기본 수집기 클래스
│   └── bookticker_depth.py    # Depth 데이터 수집기
├── common/              # 공통 모듈
│   ├── config.py        # 설정 관리
│   ├── kafka_utils.py   # Kafka Producer 래퍼
│   └── logger.py        # 로깅 설정
├── infra/               # 인프라 관리 스크립트
│   ├── setup-kafka.sh   # Kafka 토픽 생성
│   └── manage-kafka.sh # Kafka 관리 도구
├── scripts/             # 프로젝트 스크립트
│   ├── start.sh         # 전체 시작 스크립트
│   └── stop.sh          # 전체 종료 스크립트
├── spark_jobs/          # Spark 작업
│   └── kafka_reader.py  # Kafka 데이터 읽기
├── utils/               # 유틸리티
│   └── binance_stream_enum.py  # Binance 스트림 타입 정의
├── data/                # 데이터 저장소 (Docker 볼륨)
│   ├── kafka/          # Kafka 데이터
│   └── clickhouse/     # ClickHouse 데이터
├── docker-compose.yml   # Docker Compose 설정
├── requirements.txt     # Python 패키지 목록
└── README.md           # 프로젝트 문서
```

## 🔧 설정

### Kafka 토픽 설정

`common/config.py`에서 토픽 매핑을 수정할 수 있습니다:

```python
TOPIC_MAP = {
    "depth": "binance-depth",
    # "bookTicker": "binance-bookticker",
    # "trade": "binance-trade",
}
```

### Kafka Producer 설정

`common/kafka_utils.py`에서 Producer 설정을 수정할 수 있습니다:

- `batch_size`: 배치 크기 (기본값: 32768)
- `linger_ms`: 대기 시간 (기본값: 10ms)
- `compression_type`: 압축 타입 (기본값: gzip)
- `acks`: 확인 설정 (기본값: 'all')

## 🛑 종료 방법

### 전체 종료

```bash
# 1. 데이터 수집기 중지 (Ctrl+C)

# 2. Spark 작업 중지 (Ctrl+C)

# 3. Docker 서비스 종료
docker-compose down

# 또는 스크립트 사용
./scripts/stop.sh
```

### 개별 서비스 종료

```bash
# 특정 서비스만 중지
docker-compose stop kafka
docker-compose stop spark-master spark-worker
```

## 🐛 문제 해결

### Kafka가 시작되지 않는 경우

```bash
# 1. Kafka 재시작
docker-compose restart kafka

# 2. 30초 대기
sleep 30

# 3. 로그 확인
docker-compose logs kafka | tail -30

# 4. 토픽 재생성
./infra/setup-kafka.sh
```

### Spark Worker가 연결되지 않는 경우

```bash
# 1. Spark 재시작
docker-compose restart spark-master spark-worker

# 2. 10초 대기
sleep 10

# 3. 상태 확인
docker-compose ps spark-master spark-worker

# 4. 웹 UI 확인
# 브라우저: http://localhost:8080
```

### Producer가 메시지를 보내지 않는 경우

```bash
# 1. Kafka 상태 확인
docker-compose ps kafka

# 2. 토픽 리더 확인
docker exec kafka kafka-topics --describe \
    --bootstrap-server localhost:9092 \
    --topic binance-depth

# 3. 토픽 재생성
docker exec kafka kafka-topics --delete \
    --bootstrap-server localhost:9092 \
    --topic binance-depth
./infra/setup-kafka.sh
```

### 메시지가 Kafka에 저장되지 않는 경우

```bash
# 1. 오프셋 확인
./infra/manage-kafka.sh offsets binance-depth

# 2. Producer 테스트
python3 << 'EOF'
from common.kafka_utils import KafkaProducerWrapper
from common.config import Config

kafka = KafkaProducerWrapper(Config.KAFKA_BOOTSTRAP_SERVERS)
future = kafka.send('binance-depth', {'test': 'message'}, 'TEST')
kafka.flush()
metadata = future.get(timeout=10)
print(f"✅ 성공: partition={metadata.partition}, offset={metadata.offset}")
EOF
```

## 📊 모니터링

### 서비스 상태 확인

```bash
# 모든 서비스 상태
docker-compose ps

# 특정 서비스 로그
docker-compose logs kafka
docker-compose logs spark-master
```

### Kafka 모니터링

```bash
# 오프셋 확인
./infra/manage-kafka.sh offsets binance-depth

# Consumer Lag 확인
./infra/manage-kafka.sh lag

# Consumer Group 목록
./infra/manage-kafka.sh groups
```

### Spark 모니터링

- 웹 UI: http://localhost:8080
- 실행 중인 애플리케이션 확인
- Worker 상태 확인

## 🔄 일일 작업 흐름

### 아침 시작

```bash
# 1. 프로젝트 디렉토리로 이동
cd /home/vividbaek/boaz

# 2. 전체 시작
./scripts/start.sh

# 3. 데이터 수집기 시작
source venv/bin/activate
python3 -m collectors.bookticker_depth
```

### 저녁 종료

```bash
# 1. 데이터 수집기 중지 (Ctrl+C)

# 2. 전체 종료
./scripts/stop.sh
```

## 📝 주요 명령어 요약

| 명령어 | 설명 |
|--------|------|
| `./scripts/start.sh` | 전체 인프라 시작 |
| `./scripts/stop.sh` | 전체 인프라 종료 |
| `./infra/setup-kafka.sh` | Kafka 토픽 생성 |
| `./infra/manage-kafka.sh list` | 토픽 목록 조회 |
| `./infra/manage-kafka.sh consume <토픽> <개수>` | 메시지 수신 |
| `python3 -m collectors.bookticker_depth` | 데이터 수집기 시작 |
| `docker-compose ps` | 서비스 상태 확인 |
| `docker-compose logs <서비스>` | 서비스 로그 확인 |

## 🚧 향후 계획

- [ ] ClickHouse 데이터 저장 구현
- [ ] 대시보드 구축
- [ ] 추가 스트림 타입 지원 (trade, kline 등)
- [ ] 배치 처리 작업 추가
- [ ] 모니터링 및 알림 시스템

## 📄 라이선스

이 프로젝트는 개인 학습 목적으로 제작되었습니다.

## 👥 기여

이슈 및 개선 사항은 언제든지 환영합니다!

---

**마지막 업데이트**: 2026-02-10

