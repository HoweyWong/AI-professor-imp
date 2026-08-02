#!/bin/zsh
set -euo pipefail

WORKSPACE="${0:A:h:h}"
TASK_FILE="$WORKSPACE/02-Projects/RAG-CMS/week-01.md"
KNOWLEDGE_FILE=$(find "$WORKSPACE/05-Weekly-Reviews" -maxdepth 1 -type f -name 'knowledge-week-*.md' -print | sort | tail -n 1)
NOTIFY=true

case "${1:-}" in
  "") ;;
  --no-notify) NOTIFY=false ;;
  *)
    print -u2 "用法：$0 [--no-notify]"
    exit 2
    ;;
esac

if [[ ! -f "$TASK_FILE" || ! -f "$KNOWLEDGE_FILE" ]]; then
  print -u2 "找不到项目或知识周计划文件"
  exit 1
fi

NEXT_TASK=$(awk '/^- \[ \] 第/{print; exit}' "$TASK_FILE")
DONE_COUNT=$(awk '/^- \[x\] 第/{count++} END {print count+0}' "$TASK_FILE")
TOTAL_COUNT=$(awk '/^- \[[ x]\] 第/{count++} END {print count+0}' "$TASK_FILE")
KNOWLEDGE_DONE=$(awk '/^- \[x\]/{count++} END {print count+0}' "$KNOWLEDGE_FILE")
KNOWLEDGE_TOTAL=$(awk '/^- \[[ x]\]/{count++} END {print count+0}' "$KNOWLEDGE_FILE")
NEXT_KNOWLEDGE=$(awk '/^- \[ \]/{print; exit}' "$KNOWLEDGE_FILE")

if [[ -n "$NEXT_TASK" ]]; then
  NEXT_TASK=$(printf '%s\n' "$NEXT_TASK" | sed 's/^- \[ \] //')
else
  NEXT_TASK="项目首周任务已完成，请进行评测和复盘"
fi

if [[ -n "$NEXT_KNOWLEDGE" ]]; then
  NEXT_KNOWLEDGE=$(printf '%s\n' "$NEXT_KNOWLEDGE" | sed 's/^- \[ \] //')
else
  NEXT_KNOWLEDGE="本周知识任务已完成，请记录下周主题"
fi

TITLE="AI 转型计划｜项目与知识检查"
MESSAGE="项目 ${DONE_COUNT}/${TOTAL_COUNT}；知识 ${KNOWLEDGE_DONE}/${KNOWLEDGE_TOTAL}。项目：${NEXT_TASK}。知识：${NEXT_KNOWLEDGE}。"

if [[ "$NOTIFY" == true ]]; then
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'display notification "'"${MESSAGE//"/\\"}"'" with title "'"${TITLE//"/\\"}"'"'
  else
    print -u2 "提示：当前系统不支持 macOS 通知，仅输出检查结果。"
  fi
fi
printf '%s\n' "$TITLE"
printf '%s\n' "$MESSAGE"
printf '项目文件：%s\n知识文件：%s\n' "$TASK_FILE" "$KNOWLEDGE_FILE"
