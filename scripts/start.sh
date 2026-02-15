#!/bin/bash
# scripts/start.sh
# 프로젝트 전체 시작 스크립트

set -e

# 스크립트 위치 기준으로 프로젝트 루트로 이동 (어느 사용자/경로에서도 동작)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# --clean 옵션 파싱
CLEAN_START=false
for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN_START=true
            shift
            ;;
    esac
done

echo "=========================================="
echo "  🚀 프로젝트 시작"
if [ "$CLEAN_START" = true ]; then
    echo "  🧹 클린 모드 (모든 데이터 초기화)"
fi
echo "=========================================="

# 0. 클린 스타트: 기존 데이터 전부 삭제
if [ "$CLEAN_START" = true ]; then
    echo ""
    echo "🧹 0단계: 클린 스타트 - 기존 데이터 초기화..."
    
    # Docker 서비스 먼저 중지
    docker-compose down 2>/dev/null || true
    
    # Kafka 데이터 삭제
    rm -rf data/kafka/* 2>/dev/null || true
    echo "  ✅ Kafka 데이터 삭제"
    
    # ClickHouse 데이터 삭제 (root 소유 가능)
    if [ -d "data/clickhouse" ] && [ "$(ls -A data/clickhouse 2>/dev/null)" ]; then
        docker run --rm -v "$(pwd)/data/clickhouse:/data" alpine sh -c "rm -rf /data/*" 2>/dev/null || rm -rf data/clickhouse/* 2>/dev/null || true
        echo "  ✅ ClickHouse 데이터 삭제"
    fi
    
    # Spark Ivy 캐시 삭제 (root 소유 가능)
    if [ -d "data/spark-ivy" ] && [ "$(ls -A data/spark-ivy 2>/dev/null)" ]; then
        docker run --rm -v "$(pwd)/data/spark-ivy:/data" alpine sh -c "rm -rf /data/*" 2>/dev/null || rm -rf data/spark-ivy/* 2>/dev/null || true
        echo "  ✅ Spark Ivy 캐시 삭제"
    fi
    
    # Python 캐시 삭제
    find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
    echo "  ✅ Python 캐시 삭제"
    
    # Spark 체크포인트 삭제 (컨테이너 내부이므로 down으로 충분)
    echo "  ✅ 클린 스타트 완료"
fi

# 1. 데이터 디렉터리 준비 (Kafka/ClickHouse/Spark 볼륨이 쓸 수 있도록)
echo ""
echo "📁 데이터 디렉터리 준비..."
mkdir -p data/kafka data/clickhouse data/spark-ivy
chmod 777 data/kafka data/clickhouse data/spark-ivy 2>/dev/null || true
echo "✅ 데이터 디렉터리 준비 완료"

# 2. Docker 서비스 시작
echo ""
echo "📦 2단계: Docker 서비스 시작..."
docker-compose up -d
echo "✅ Docker 서비스 시작 완료"

# 클린 스타트 시 Spark 체크포인트 삭제 (Kafka 토픽 ID가 바뀌면 Spark가 예전 ID로 요청해 브로커 에러 발생 방지)
if [ "$CLEAN_START" = true ]; then
    echo "🧹 Spark 체크포인트 초기화 (토픽 ID 변경 대비)..."
    sleep 10
    docker exec spark-master rm -rf /tmp/checkpoint-* 2>/dev/null || true
    echo "  ✅ Spark 체크포인트 초기화 완료"
fi

# 3. Kafka 준비 대기
echo ""
echo "⏳ 3단계: Kafka 준비 대기 (30초)..."
sleep 30

# 2-1. Kafka 에러 확인 및 자동 복구
echo ""
echo "🔍 Kafka 상태 확인 중..."

# Topic ID 불일치 또는 Cluster ID 불일치 감지
KAFKA_ERROR=$(docker-compose logs kafka 2>&1 | grep -iE "InconsistentClusterIdException|does not match the topic ID" | tail -1 || true)

if [ -n "$KAFKA_ERROR" ]; then
    echo "⚠️  Kafka 데이터 불일치 감지! 자동 복구 중..."
    echo "   에러: $KAFKA_ERROR"
    
    # 서비스 중지
    docker-compose stop kafka
    
    # Kafka 데이터 전체 삭제 (Topic ID 불일치 방지)
    rm -rf data/kafka/*
    echo "✅ Kafka 데이터 초기화 완료"
    
    # 재시작
    docker-compose up -d kafka
    echo "✅ Kafka 재시작 완료"
    
    # Spark 체크포인트 삭제 (토픽 ID가 바뀌었으므로 예전 체크포인트 사용 시 브로커 에러 방지)
    docker exec spark-master rm -rf /tmp/checkpoint-* 2>/dev/null || true
    echo "  ✅ Spark 체크포인트 초기화 완료"
    
    # 대기
    echo "⏳ Kafka 재시작 대기 중... (30초)"
    sleep 30
fi

# 3. 토픽 생성 (이미 있으면 건너뜀, 내부에서 리더 선출 15초 대기 포함)
echo ""
echo "📝 4단계: Kafka 토픽 확인/생성..."
./infra/setup-kafka.sh

# 4. 상태 확인
echo ""
echo "📊 5단계: 서비스 상태 확인"
docker-compose ps

# 5. Spark 상태 확인 및 준비
echo ""
echo "📊 6단계: Spark 상태 확인 및 준비..."
sleep 5

# Ivy 캐시 디렉토리 준비 (볼륨 마운트로 해결됨)
# 호스트 디렉토리 생성
mkdir -p data/spark-ivy 2>/dev/null || true
# 컨테이너 내부에서 서브디렉토리 생성 (볼륨이 마운트된 후)
docker exec spark-master bash -c "mkdir -p /opt/spark/.ivy2/cache /opt/spark/.ivy2/jars && chmod -R 777 /opt/spark/.ivy2" 2>/dev/null || true

# Spark Master 확인 (로그 기반)
if docker-compose logs spark-master 2>&1 | grep -q "MasterWebUI.*started"; then
    echo "✅ Spark Master 실행 중 (http://localhost:8080)"
else
    echo "⚠️  Spark Master 확인 실패 (로그 확인 중...)"
fi

# Spark Worker 확인 (로그 기반)
WORKER_COUNT=$(docker-compose logs spark-master 2>&1 | grep -c "Registering worker" || echo "0")
if [ "$WORKER_COUNT" -gt "0" ]; then
    echo "✅ Spark Worker 등록됨: ${WORKER_COUNT}개"
else
    echo "⚠️  Spark Worker 미등록 (잠시 후 자동 등록될 수 있음)"
fi

echo ""
echo "=========================================="
echo "  ✅ 준비 완료!"
echo "=========================================="
echo ""
echo "📥 데이터 수집기 시작:"
echo "  source venv/bin/activate"
echo "  python3 -m collectors.bookticker_depth"
echo ""
echo "⚡ Spark Job 실행:"
echo "  ./scripts/start-spark-job.sh"
echo ""
echo "🌐 Spark 웹 UI:"
echo "  http://localhost:8080"
echo ""
echo "📊 메시지 확인:"
echo "  ./infra/manage-kafka.sh consume binance-depth 5"