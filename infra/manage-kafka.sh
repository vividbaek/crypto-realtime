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
        [ -z "$2" ] && echo "사용법: $0 consume <토픽명> [개수]" && exit 1
        max_messages=${3:-10}
        echo "📥 $2 메시지 수신 중... (최대 ${max_messages}개)"
        docker exec -it kafka kafka-console-consumer \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --topic "$2" \
            --from-beginning \
            --max-messages $max_messages
        ;;
    lag)
        if [ -z "$2" ]; then
            echo "📊 모든 Consumer Group의 Lag:"
            docker exec kafka kafka-consumer-groups \
                --bootstrap-server $BOOTSTRAP_SERVER \
                --all-groups \
                --describe
        else
            echo "📊 Consumer Group '$2'의 Lag:"
            docker exec kafka kafka-consumer-groups \
                --bootstrap-server $BOOTSTRAP_SERVER \
                --group "$2" \
                --describe
        fi
        ;;
    groups)
        echo "📋 Consumer Group 목록:"
        docker exec kafka kafka-consumer-groups \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --list
        ;;
    offsets)
        if [ -z "$2" ]; then
            echo "❌ 사용법: $0 offsets <토픽명>"
            exit 1
        fi
        echo "📊 토픽 '$2'의 오프셋 정보:"
        docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
            --broker-list $BOOTSTRAP_SERVER \
            --topic "$2"
        ;;
    *)
        echo "Kafka 관리 스크립트"
        echo ""
        echo "사용법: $0 <명령> [옵션]"
        echo ""
        echo "명령:"
        echo "  list                    - 토픽 목록 조회"
        echo "  describe [토픽명]        - 토픽 상세 정보"
        echo "  consume <토픽명> [개수]  - 메시지 수신 (테스트)"
        echo "  groups                  - Consumer Group 목록"
        echo "  lag [그룹명]            - Consumer Lag 확인 (그룹명 없으면 전체)"
        echo "  offsets <토픽명>        - 토픽 오프셋 정보"
        echo ""
        echo "예시:"
        echo "  $0 list"
        echo "  $0 describe binance-depth"
        echo "  $0 offsets binance-depth"
        echo "  $0 consume binance-depth 5"
        exit 1
        ;;
esac