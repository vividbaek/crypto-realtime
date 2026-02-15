#!/bin/bash
# scripts/start-spark-job.sh
# Spark Job 실행 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "  ⚡ Spark Job 실행"
echo "=========================================="

# Spark Master 컨테이너 확인
if ! docker ps --format "{{.Names}}" | grep -q "^spark-master$"; then
    echo "❌ Spark Master 컨테이너가 실행되지 않았습니다."
    echo "먼저 ./scripts/start.sh를 실행하세요."
    exit 1
fi

# Spark Master 로그에서 시작 확인
if ! docker-compose logs spark-master 2>&1 | grep -q "MasterWebUI.*started"; then
    echo "⚠️  Spark Master가 아직 시작 중일 수 있습니다. 잠시 대기 중..."
    sleep 5
fi

echo "✅ Spark Master 확인 완료"
echo "  Master: http://localhost:8080"
echo ""

# Ivy 캐시 디렉토리 준비 (볼륨 마운트 = data/spark-ivy → /opt/spark/.ivy2)
echo "📦 Ivy 캐시 디렉토리 준비 중..."
mkdir -p data/spark-ivy/cache data/spark-ivy/jars
chmod -R 777 data/spark-ivy 2>/dev/null || true
# 컨테이너 내부에서도 권한 확보 (마운트된 경로)
docker exec spark-master bash -c "mkdir -p /opt/spark/.ivy2/cache /opt/spark/.ivy2/jars && chmod -R 777 /opt/spark/.ivy2" 2>/dev/null || true

# 인자로 job 선택 (기본: kafka_reader / preprocess: 1분봉 집계 / kline: Binance 1분봉)
JOB="${1:-kafka_reader}"
case "$JOB" in
  preprocess|stream_preprocess)
    JOB_SCRIPT="stream_preprocess.py"
    echo "🚀 전처리 Job 시작 (aggTrade → 1분봉 집계)..."
    ;;
  kline)
    JOB_SCRIPT="kline_console.py"
    echo "🚀 Binance 1분봉(kline_1m) 콘솔 출력 (비교용)..."
    ;;
  *)
    JOB_SCRIPT="kafka_reader.py"
    echo "🚀 Kafka Reader Job 시작 (depth → 콘솔)..."
    ;;
esac
echo "  (Ctrl+C로 중지)"
echo ""

# Spark Job 실행 (log4j 설정으로 불필요한 INFO 로그 제거)
docker exec -it spark-master bash -c "cd /opt/spark/work-dir && /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1 --conf 'spark.driver.extraJavaOptions=-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties' --conf 'spark.executor.extraJavaOptions=-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties' $JOB_SCRIPT"