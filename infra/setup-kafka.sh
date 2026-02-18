#!/bin/bash
# infra/setup-kafka.sh

# 스크립트 위치 기준으로 프로젝트 루트로 이동 (start.sh에서 호출해도 직접 실행해도 동작)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# docker-compose.yml에 container_name: kafka 사용 시 이 이름으로 exec
KAFKA_CONTAINER_NAME="kafka"
BOOTSTRAP_SERVER="localhost:9092"
PARTITIONS=3
REPLICATION_FACTOR=1

# Compose V2(docker compose) 우선, 없으면 V1(docker-compose). 프로젝트 디렉터리 명시로 호출 경로 독립
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose --project-directory $PROJECT_ROOT"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose --project-directory $PROJECT_ROOT"
else
    echo "❌ docker compose 또는 docker-compose를 찾을 수 없습니다."
    exit 1
fi

echo "⏳ Kafka 준비 대기 중... (프로젝트: $PROJECT_ROOT)"

# 스마트 대기: 준비될 때까지 확인 (개선된 버전)
MAX_WAIT=120
ELAPSED=0
CONTAINER_RUNNING_RETRIES=15
CONTAINER_RETRY=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Kafka 컨테이너: compose로 먼저, 없으면 이름으로 직접 찾기 (container_name: kafka)
    KAFKA_CID="$($COMPOSE_CMD ps -q kafka 2>/dev/null)"
    if [ -z "$KAFKA_CID" ]; then
        KAFKA_CID="$(docker ps -aq --filter "name=kafka" 2>/dev/null | head -1)"
    fi
    if [ -z "$KAFKA_CID" ]; then
        CONTAINER_RETRY=$((CONTAINER_RETRY + 1))
        if [ $CONTAINER_RETRY -ge $CONTAINER_RUNNING_RETRIES ]; then
            echo "❌ Kafka 서비스가 docker-compose에 없거나 아직 생성되지 않았습니다."
            echo ""
            echo "   현재 컨테이너 목록 (같은 프로젝트):"
            $COMPOSE_CMD ps -a 2>/dev/null || true
            echo ""
            echo "   이름에 'kafka' 포함된 컨테이너:"
            docker ps -a --filter "name=kafka" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
            exit 1
        fi
        echo "  Kafka 컨테이너 대기 중... (${CONTAINER_RETRY}/${CONTAINER_RUNNING_RETRIES})"
        sleep 2
        ELAPSED=$((ELAPSED + 2))
        continue
    fi

    # 컨테이너가 실행 중인지 확인 (Exited면 크래시)
    if ! docker inspect -f '{{.State.Running}}' "$KAFKA_CID" 2>/dev/null | grep -q "true"; then
        echo "❌ Kafka 컨테이너가 시작 후 종료되었습니다. 로그를 확인하세요."
        echo ""
        $COMPOSE_CMD logs kafka 2>&1 | tail -30
        exit 1
    fi

    # Kafka가 준비되었는지 확인 (에러 메시지도 출력)
    if docker exec "$KAFKA_CONTAINER_NAME" kafka-topics --list \
        --bootstrap-server $BOOTSTRAP_SERVER > /dev/null 2>&1; then
        echo "✅ Kafka 준비 완료! (${ELAPSED}초 소요)"
        break
    else
        # 에러 메시지 출력 (디버깅용)
        if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
            echo "  ⚠️  대기 중... ${ELAPSED}초 (Kafka 로그 확인 중...)"
            $COMPOSE_CMD logs kafka 2>&1 | tail -5 | grep -i "error\|exception" || echo "    로그에 에러 없음"
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
    $COMPOSE_CMD ps kafka
    echo ""
    echo "  2. Kafka 최근 로그:"
    $COMPOSE_CMD logs kafka | tail -20
    echo ""
    echo "  3. 직접 연결 테스트:"
    docker exec "$KAFKA_CONTAINER_NAME" kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null || echo "    연결 실패"
    echo ""
    exit 1
fi

# 토픽 생성 함수
create_topic() {
    local topic=$1
    local retention_ms=${2:-604800000}

    echo "📝 토픽 생성: $topic"
    if docker exec "$KAFKA_CONTAINER_NAME" kafka-topics --create \
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
echo "  Kafka 토픽 생성 (depth, kline, trade)"
echo "=========================================="

create_topic "binance-depth" 604800000
create_topic "binance-kline" 604800000
create_topic "binance-trade" 604800000
# TODO
## 스트림 데이터 

# 리더 선출 대기
echo ""
echo "⏳ 리더 선출 완료 대기 중... (15초)"
sleep 15

echo ""
echo "=========================================="
echo "  생성 결과"
echo "=========================================="
docker exec "$KAFKA_CONTAINER_NAME" kafka-topics --list --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "=========================================="
echo "  토픽 상세 정보"
echo "=========================================="
docker exec "$KAFKA_CONTAINER_NAME" kafka-topics --describe \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --topic binance-depth 2>/dev/null || echo "토픽 정보 조회 실패"

# Topic ID 불일치 검증
echo ""
echo "🔍 Topic ID 일관성 검증 중..."
TOPIC_ID_ERROR=$($COMPOSE_CMD logs kafka 2>&1 | grep -i "does not match the topic ID" | tail -1 || true)
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