property reminderListName : "AI转型计划"
property oldProjectTitle : "下一步：创建 FastAPI 最小项目并完成健康检查接口"
property projectTitle : "项目：7月28日实现文本切分和 Chunk 元数据"
property oldKnowledgeTitle : "知识储备：完成本周 RAG 知识卡"
property knowledgeTitle : "知识储备：8月2日完成首周复盘"

on scheduledDate(yearValue, monthValue, dayValue, hourValue)
	set targetDate to current date
	set year of targetDate to yearValue
	set month of targetDate to monthValue
	set day of targetDate to dayValue
	set time of targetDate to hourValue * hours
	return targetDate
end scheduledDate

tell application "Reminders"
	if not (exists list reminderListName) then
		make new list with properties {name:reminderListName}
	end if
	tell list reminderListName
		if exists reminder projectTitle then
			set projectReminder to first reminder whose name is projectTitle
		else if exists reminder oldProjectTitle then
			set projectReminder to first reminder whose name is oldProjectTitle
		else
			set projectReminder to make new reminder with properties {name:projectTitle}
		end if
		set name of projectReminder to projectTitle
		set body of projectReminder to "首周第 3 次项目时段：实现固定长度与重叠窗口切分，并保留 document_id、chunk_index 和来源位置。"
		set remind me date of projectReminder to my scheduledDate(2026, July, 28, 20)

		if exists reminder knowledgeTitle then
			set knowledgeReminder to first reminder whose name is knowledgeTitle
		else if exists reminder oldKnowledgeTitle then
			set knowledgeReminder to first reminder whose name is oldKnowledgeTitle
		else
			set knowledgeReminder to make new reminder with properties {name:knowledgeTitle}
		end if
		set name of knowledgeReminder to knowledgeTitle
		set body of knowledgeReminder to "记录一个未解决问题，确定下周唯一知识主题，并完成首周复盘。"
		set remind me date of knowledgeReminder to my scheduledDate(2026, August, 2, 20)
	end tell
end tell

return "首周提醒已调整为周二项目任务和下周日复盘。"
