#!/bin/bash
# scripts/start.sh
# 프로젝트 전체 시작 스크립트

set -e

cd /home/vividbaek/boaz

echo "=========================================="
echo "  🚀 프로젝트 시작"
echo "=========================================="

# 1. Docker 서비스 시작
echo ""
echo "📦 1단계: Docker 서비스 시작..."
docker-compose up -d
echo "✅ Docker 서비스 시작 완료"

# 2. Kafka 준비 대기
echo ""
echo "⏳ 2단계: Kafka 준비 대기 (15초)..."
sleep 15

# 3. 토픽 생성 (이미 있으면 건너뜀)
echo ""
echo "📝 3단계: Kafka 토픽 확인/생성..."
./infra/setup-kafka.sh

# 4. 상태 확인
echo ""
echo "📊 4단계: 서비스 상태 확인"
docker-compose ps

echo ""
echo "=========================================="
echo "  ✅ 준비 완료!"
echo "=========================================="
echo ""
echo "다음 명령어로 수집기를 시작하세요:"
echo "  python3 -m collectors.bookticker_depth"
echo ""
echo "다른 터미널에서 메시지 확인:"
echo "  ./infra/manage-kafka.sh consume binance-depth 5"