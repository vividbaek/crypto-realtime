#!/bin/bash
# infra/setup-kafka.sh
# 용도: Kafka 토픽 초기화 (프로젝트 처음 세팅할 때 1번 실행)

set -e

BOOTSTRAP_SERVER="localhost:9092"
PARTITIONS=3
REPLICATION_FACTOR=1  # 단일 브로커이므로 1 (브로커 추가 시 변경) 브로커 1대가 리더임

echo "⏳ Kafka 준비 대기 중..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec kafka kafka-broker-api-versions \
        --bootstrap-server $BOOTSTRAP_SERVER > /dev/null 2>&1; then
        echo "✅ Kafka 준비 완료!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  대기 중... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Kafka가 준비되지 않았습니다. docker-compose ps로 상태를 확인하세요."
    exit 1
fi

# 토픽 생성 함수
create_topic() {
    local topic=$1
    local retention_ms=${2:-604800000}  # 기본 7일

    echo "📝 토픽 생성: $topic (파티션: $PARTITIONS, 복제: $REPLICATION_FACTOR)"
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
echo "  Kafka 토픽 생성"
echo "=========================================="

# 고빈도 데이터 (7일 보관)
# create_topic "binance-trade"         604800000
# create_topic "binance-bookticker"    604800000
create_topic "binance-depth"         604800000

# 중빈도 데이터 (14일 보관)
# create_topic "binance-kline"         1209600000
# create_topic "binance-ticker"        1209600000

# # 저빈도 데이터 (30일 보관)
# create_topic "binance-fundingrate"   2592000000
# create_topic "binance-liquidation"   2592000000
# create_topic "binance-openinterest"  2592000000

echo ""
echo "=========================================="
echo "  생성 결과"
echo "=========================================="
docker exec kafka kafka-topics --list --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "🎉 완료! 토픽 상세 정보는 다음 명령어로 확인:"
echo "  ./infra/manage-kafka.sh describe <토픽명>"