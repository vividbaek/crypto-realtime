#!/bin/bash
# scripts/stop.sh
# 프로젝트 전체 종료 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 서비스 종료 중..."
docker-compose down
echo "✅ 종료 완료"