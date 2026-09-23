#!/bin/bash
# 최초 1회: GitHub에 빈 private 저장소를 만든 뒤 URL을 넣고 실행
#   bash push.sh https://github.com/사용자명/banseok-office-twin.git "커밋 메시지"
set -e
REPO="${1:?사용법: bash push.sh <저장소 URL> [커밋 메시지]}"
cd "$(dirname "$0")"
git init -b main 2>/dev/null || true
git add -A
git commit -m "${2:-반석 사무실 3D 운영 디지털 트윈}" || echo "변경 없음"
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO"
git push -u origin main
echo "완료: $REPO"
