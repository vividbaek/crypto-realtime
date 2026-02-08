#!/bin/bash
# infra/manage-kafka.sh
# 용도: Kafka 일상 관리 (토픽 조회, 메시지 확인 등)

BOOTSTRAP_SERVER="localhost:9092"

case "$1" in
    list)
        docker exec kafka kafka-topics --list \
            --bootstrap-server $BOOTSTRAP_SERVER
        ;;
    describe)
        docker exec kafka kafka-topics --describe \
            --bootstrap-server $BOOTSTRAP_SERVER \
            ${2:+--topic $2}
        ;;
    consume)
        [ -z "$2" ] && echo "사용법: $0 consume <토픽명>" && exit 1
        echo "📥 $2 메시지 수신 중... (Ctrl+C로 종료)"
        docker exec -it kafka kafka-console-consumer \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --topic "$2" --from-beginning --max-messages ${3:-10}
        ;;
    lag)
        docker exec kafka kafka-consumer-groups \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --list
        ;;
    *)
        echo "사용법: $0 {list|describe [토픽]|consume <토픽> [개수]|lag}"
        ;;
esac