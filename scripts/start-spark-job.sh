#!/bin/bash
# scripts/start-spark-job.sh
# Spark Job 실행 스크립트

set -e

cd /home/vividbaek/boaz

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

# Ivy 캐시 디렉토리 준비 (볼륨 마운트로 해결됨)
echo "📦 Ivy 캐시 디렉토리 준비 중..."
# 호스트 디렉토리 생성 (권한 문제 해결)
mkdir -p data/spark-ivy 2>/dev/null || true
# 컨테이너 내부에서 서브디렉토리 생성 (볼륨이 마운트된 후)
docker exec spark-master bash -c "mkdir -p /opt/spark/.ivy2/cache /opt/spark/.ivy2/jars && chmod -R 777 /opt/spark/.ivy2" 2>/dev/null || true

echo "🚀 Kafka Reader Job 시작..."
echo "  (Ctrl+C로 중지)"
echo ""

# Spark Job 실행 (log4j 설정으로 불필요한 INFO 로그 제거)
docker exec -it spark-master bash -c "cd /opt/spark/work-dir && /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1 --conf 'spark.driver.extraJavaOptions=-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties' --conf 'spark.executor.extraJavaOptions=-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties' kafka_reader.py"