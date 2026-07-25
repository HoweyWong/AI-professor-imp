#!/bin/zsh
set -euo pipefail

WORKSPACE="${0:A:h:h}"
TASK_FILE="$WORKSPACE/02-Projects/RAG-CMS/week-01.md"
KNOWLEDGE_FILE="$WORKSPACE/05-Weekly-Reviews/knowledge-week-2026-07-25.md"

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

osascript -e 'display notification "'"${MESSAGE//"/\\"}"'" with title "'"${TITLE//"/\\"}"'"'
printf '%s\n' "$TITLE"
printf '%s\n' "$MESSAGE"
printf '项目文件：%s\n知识文件：%s\n' "$TASK_FILE" "$KNOWLEDGE_FILE"
