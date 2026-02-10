#!/bin/bash
# infra/setup-kafka.sh

BOOTSTRAP_SERVER="localhost:9092"
PARTITIONS=3
REPLICATION_FACTOR=1

echo "⏳ Kafka 준비 대기 중..."

# 스마트 대기: 준비될 때까지 확인
MAX_WAIT=120
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker exec kafka kafka-topics --list \
        --bootstrap-server $BOOTSTRAP_SERVER > /dev/null 2>&1; then
        echo "✅ Kafka 준비 완료! (${ELAPSED}초 소요)"
        break
    fi
    
    if [ $((ELAPSED % 5)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        echo "  대기 중... ${ELAPSED}초"
    fi
    
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "❌ Kafka가 준비되지 않았습니다."
    echo "로그 확인: docker-compose logs kafka"
    exit 1
fi

# 토픽 생성 함수
create_topic() {
    local topic=$1
    local retention_ms=${2:-604800000}

    echo "📝 토픽 생성: $topic"
    docker exec kafka kafka-topics --create \
        --if-not-exists \
        --bootstrap-server $BOOTSTRAP_SERVER \
        --topic "$topic" \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$retention_ms
}

echo ""
echo "=========================================="
echo "  Kafka 토픽 생성 (depth만)"
echo "=========================================="

create_topic "binance-depth" 604800000

echo ""
echo "=========================================="
echo "  생성 결과"
echo "=========================================="
docker exec kafka kafka-topics --list --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "🎉 완료!"