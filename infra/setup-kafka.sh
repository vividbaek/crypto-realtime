#!/bin/bash
# infra/setup-kafka.sh

BOOTSTRAP_SERVER="localhost:9092"
PARTITIONS=3
REPLICATION_FACTOR=1

echo "⏳ Kafka 준비 대기 중..."

# 스마트 대기: 준비될 때까지 확인 (개선된 버전)
MAX_WAIT=120
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Kafka 컨테이너가 실행 중인지 확인
    if ! docker ps | grep -q "kafka"; then
        echo "❌ Kafka 컨테이너가 실행되지 않았습니다."
        exit 1
    fi
    
    # Kafka가 준비되었는지 확인 (에러 메시지도 출력)
    if docker exec kafka kafka-topics --list \
        --bootstrap-server $BOOTSTRAP_SERVER > /dev/null 2>&1; then
        echo "✅ Kafka 준비 완료! (${ELAPSED}초 소요)"
        break
    else
        # 에러 메시지 출력 (디버깅용)
        if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
            echo "  ⚠️  대기 중... ${ELAPSED}초 (Kafka 로그 확인 중...)"
            docker-compose logs kafka | tail -5 | grep -i "error\|exception" || echo "    로그에 에러 없음"
        fi
    fi
    
    if [ $((ELAPSED % 5)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        echo "  대기 중... ${ELAPSED}초"
    fi
    
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "❌ Kafka가 준비되지 않았습니다. (${MAX_WAIT}초 초과)"
    echo ""
    echo "📋 진단 정보:"
    echo "  1. Kafka 컨테이너 상태:"
    docker-compose ps kafka
    echo ""
    echo "  2. Kafka 최근 로그:"
    docker-compose logs kafka | tail -20
    echo ""
    echo "  3. 직접 연결 테스트:"
    docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 || echo "    연결 실패"
    echo ""
    exit 1
fi

# 토픽 생성 함수
create_topic() {
    local topic=$1
    local retention_ms=${2:-604800000}

    echo "📝 토픽 생성: $topic"
    if docker exec kafka kafka-topics --create \
        --if-not-exists \
        --bootstrap-server $BOOTSTRAP_SERVER \
        --topic "$topic" \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$retention_ms 2>&1; then
        echo "✅ 토픽 생성 성공: $topic"
    else
        echo "⚠️  토픽 생성 실패 또는 이미 존재: $topic"
    fi
}

echo ""
echo "=========================================="
echo "  Kafka 토픽 생성 (depth만)"
echo "=========================================="

create_topic "binance-depth" 604800000

# 리더 선출 대기
echo ""
echo "⏳ 리더 선출 완료 대기 중... (15초)"
sleep 15

echo ""
echo "=========================================="
echo "  생성 결과"
echo "=========================================="
docker exec kafka kafka-topics --list --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "=========================================="
echo "  토픽 상세 정보"
echo "=========================================="
docker exec kafka kafka-topics --describe \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --topic binance-depth 2>/dev/null || echo "토픽 정보 조회 실패"

# Topic ID 불일치 검증
echo ""
echo "🔍 Topic ID 일관성 검증 중..."
TOPIC_ID_ERROR=$(docker-compose logs kafka 2>&1 | grep -i "does not match the topic ID" | tail -1 || true)
if [ -n "$TOPIC_ID_ERROR" ]; then
    echo "⚠️  Topic ID 불일치 감지! stale 데이터가 남아있습니다."
    echo "   에러: $TOPIC_ID_ERROR"
    echo ""
    echo "   해결 방법: ./scripts/start.sh --clean 으로 재시작하세요."
    exit 1
else
    echo "✅ Topic ID 일관성 확인 완료"
fi

echo ""
echo "🎉 완료!"