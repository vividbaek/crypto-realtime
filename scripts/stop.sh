#!/bin/bash
# scripts/stop.sh
# 프로젝트 전체 종료 스크립트

cd /home/vividbaek/boaz

echo "🛑 서비스 종료 중..."
docker-compose down
echo "✅ 종료 완료"