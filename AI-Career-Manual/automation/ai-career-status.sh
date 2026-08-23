#!/bin/zsh
set -euo pipefail

WORKSPACE="${0:A:h:h}"
TASK_FILE=$(find "$WORKSPACE/02-Projects/RAG-CMS" -maxdepth 1 -type f -name 'week-*.md' -print | sort | tail -n 1)
KNOWLEDGE_FILE=$(find "$WORKSPACE/05-Weekly-Reviews" -maxdepth 1 -type f -name 'knowledge-week-*.md' -print | sort | tail -n 1)
CASE_FILE="$WORKSPACE/03-Architecture-Cases/case-plan.md"
REPORT_FILE="$WORKSPACE/04-Industry-Reports/report-plan.md"
OUTCOMES_FILE="$WORKSPACE/05-Weekly-Reviews/90-day-outcomes.md"
NOTIFY=true

case "${1:-}" in
  "") ;;
  --no-notify) NOTIFY=false ;;
  *)
    print -u2 "用法：$0 [--no-notify]"
    exit 2
    ;;
esac

if [[ -z "$TASK_FILE" || -z "$KNOWLEDGE_FILE" || ! -f "$TASK_FILE" || ! -f "$KNOWLEDGE_FILE" || ! -f "$CASE_FILE" || ! -f "$REPORT_FILE" || ! -f "$OUTCOMES_FILE" ]]; then
  print -u2 "找不到项目、知识、架构案例、行业报告或阶段成果计划文件"
  exit 1
fi

NEXT_TASK=$(awk '/^- \[ \] 第/{print; exit}' "$TASK_FILE")
DONE_COUNT=$(awk '/^- \[x\] 第/{count++} END {print count+0}' "$TASK_FILE")
TOTAL_COUNT=$(awk '/^- \[[ x]\] 第/{count++} END {print count+0}' "$TASK_FILE")
KNOWLEDGE_DONE=$(awk '/^- \[x\]/{count++} END {print count+0}' "$KNOWLEDGE_FILE")
KNOWLEDGE_TOTAL=$(awk '/^- \[[ x]\]/{count++} END {print count+0}' "$KNOWLEDGE_FILE")
NEXT_KNOWLEDGE=$(awk '/^- \[ \]/{print; exit}' "$KNOWLEDGE_FILE")
CASE_DONE=$(awk '/^- \[x\]/{count++} END {print count+0}' "$CASE_FILE")
CASE_TARGET=$(awk -F '：' '/^- 目标数量：/{print $2; exit}' "$CASE_FILE")
NEXT_CASE=$(awk '/^- \[ \]/{print; exit}' "$CASE_FILE")
REPORT_DONE=$(awk '/^- \[x\]/{count++} END {print count+0}' "$REPORT_FILE")
REPORT_TARGET=$(awk -F '：' '/^- 目标数量：/{print $2; exit}' "$REPORT_FILE")
NEXT_REPORT=$(awk '/^- \[ \]/{print; exit}' "$REPORT_FILE")
OUTCOMES_DONE=$(awk '/^- \[x\]/{count++} END {print count+0}' "$OUTCOMES_FILE")
OUTCOMES_TOTAL=$(awk '/^- \[[ x]\]/{count++} END {print count+0}' "$OUTCOMES_FILE")
NEXT_OUTCOME=$(awk '/^- \[ \]/{print; exit}' "$OUTCOMES_FILE")

if [[ -z "$CASE_TARGET" || -z "$REPORT_TARGET" ]]; then
  print -u2 "架构案例或行业报告计划缺少目标数量"
  exit 1
fi

format_next_item() {
  local item="$1"
  local fallback="$2"
  local current_date deadline
  if [[ -z "$item" ]]; then
    printf '%s\n' "$fallback"
    return
  fi

  item=$(printf '%s\n' "$item" | sed 's/^- \[ \] //')
  current_date=$(date +%F)
  deadline=$(printf '%s\n' "$item" | sed -nE 's/^([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/p')
  if [[ -n "$deadline" && "$deadline" < "$current_date" ]]; then
    printf '[已逾期] %s\n' "$item"
  else
    printf '%s\n' "$item"
  fi
}

if [[ -n "$NEXT_TASK" ]]; then
  NEXT_TASK=$(printf '%s\n' "$NEXT_TASK" | sed 's/^- \[ \] //')
else
  NEXT_TASK="最新项目周计划已完成，请复盘并创建下一周计划"
fi

if [[ -n "$NEXT_KNOWLEDGE" ]]; then
  NEXT_KNOWLEDGE=$(printf '%s\n' "$NEXT_KNOWLEDGE" | sed 's/^- \[ \] //')
else
  NEXT_KNOWLEDGE="最新知识周计划已完成，请复盘并创建下一周主题"
fi

NEXT_CASE=$(format_next_item "$NEXT_CASE" "架构案例未设置下一项，请先复盘再选择一个题目")
NEXT_REPORT=$(format_next_item "$NEXT_REPORT" "行业报告未设置下一项，请选择本月唯一报告")
NEXT_OUTCOME=$(format_next_item "$NEXT_OUTCOME" "90 天阶段检查已完成，请整理最终成果")

TITLE="AI 转型计划｜四轨与阶段检查"
MESSAGE="项目 ${DONE_COUNT}/${TOTAL_COUNT}；知识 ${KNOWLEDGE_DONE}/${KNOWLEDGE_TOTAL}；架构案例 ${CASE_DONE}/${CASE_TARGET}；行业报告 ${REPORT_DONE}/${REPORT_TARGET}；阶段成果 ${OUTCOMES_DONE}/${OUTCOMES_TOTAL}。"

if [[ "$NOTIFY" == true ]]; then
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'display notification "'"${MESSAGE//"/\\"}"'" with title "'"${TITLE//"/\\"}"'"'
  else
    print -u2 "提示：当前系统不支持 macOS 通知，仅输出检查结果。"
  fi
fi
printf '%s\n' "$TITLE"
printf '%s\n' "$MESSAGE"
printf '项目：%s\n' "$NEXT_TASK"
printf '知识：%s\n' "$NEXT_KNOWLEDGE"
printf '架构案例：%s\n' "$NEXT_CASE"
printf '行业报告：%s\n' "$NEXT_REPORT"
printf '阶段成果：%s\n' "$NEXT_OUTCOME"
printf '项目文件：%s\n知识文件：%s\n架构案例文件：%s\n行业报告文件：%s\n阶段成果文件：%s\n' \
  "$TASK_FILE" "$KNOWLEDGE_FILE" "$CASE_FILE" "$REPORT_FILE" "$OUTCOMES_FILE"
