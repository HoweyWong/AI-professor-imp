property reminderListName : "AI转型计划"
property oldTitle : "项目：7月28日实现文本切分和 Chunk 元数据"
property newTitle : "项目：8月1日完成检索、问答与引用"

set targetDate to current date
set year of targetDate to 2026
set month of targetDate to August
set day of targetDate to 1
set time of targetDate to 9 * hours

tell application "Reminders"
	if not (exists list reminderListName) then
		make new list with properties {name:reminderListName}
	end if
	tell list reminderListName
		if exists reminder newTitle then
			set projectReminder to first reminder whose name is newTitle
		else if exists reminder oldTitle then
			set projectReminder to first reminder whose name is oldTitle
		else
			set projectReminder to make new reminder with properties {name:newTitle}
		end if
		set name of projectReminder to newTitle
		set body of projectReminder to "首周第 5 次项目时段：实现余弦相似度 Top-K 检索、上下文拼接、问答调用和引用来源返回。"
		set remind me date of projectReminder to targetDate
	end tell
end tell

return "项目提醒已更新到 8 月 1 日。"
