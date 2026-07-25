property calendarName : "AI转型计划"
property reminderListName : "AI转型计划"

on nextWeekday(targetWeekday)
	set d to current date
	set time of d to 0
	repeat until weekday of d is targetWeekday
		set d to d + (1 * days)
	end repeat
	return d
end nextWeekday

on addCalendarEvent(eventTitle, eventDate, durationMinutes, recurrenceRule)
	tell application "Calendar"
		if not (exists calendar calendarName) then
			make new calendar with properties {name:calendarName}
		end if
		tell calendar calendarName
			set existingEvents to (every event whose summary is eventTitle and start date is eventDate)
			if (count of existingEvents) is 0 then
				set eventStart to eventDate
				set eventEnd to eventStart + (durationMinutes * minutes)
				set newEvent to make new event at end of events with properties {summary:eventTitle, start date:eventStart, end date:eventEnd}
				set recurrence of newEvent to recurrenceRule
			end if
		end tell
	end tell
end addCalendarEvent

set tuesdayDate to nextWeekday(Tuesday)
set time of tuesdayDate to (20 * hours)
set thursdayDate to nextWeekday(Thursday)
set time of thursdayDate to (20 * hours)
set saturdayDate to nextWeekday(Saturday)
set time of saturdayDate to (9 * hours)
set sundayDate to nextWeekday(Sunday)
set time of sundayDate to (20 * hours)

addCalendarEvent("AI转型｜概念与知识卡", tuesdayDate, 90, "FREQ=WEEKLY;INTERVAL=1")
addCalendarEvent("AI转型｜官方文档与代码复现", thursdayDate, 90, "FREQ=WEEKLY;INTERVAL=1")
addCalendarEvent("AI转型｜RAG-CMS项目开发", saturdayDate, 210, "FREQ=WEEKLY;INTERVAL=1")
addCalendarEvent("AI转型｜测试、复盘与计划", sundayDate, 60, "FREQ=WEEKLY;INTERVAL=1")

tell application "Reminders"
	if not (exists list reminderListName) then
		make new list with properties {name:reminderListName}
	end if
	tell list reminderListName
		set reminderTitle to "下一步：创建 FastAPI 最小项目并完成健康检查接口"
		set existingReminders to (every reminder whose name is reminderTitle)
		if (count of existingReminders) is 0 then
			make new reminder with properties {name:reminderTitle, body:"来自 AI-Career-Manual/02-Projects/RAG-CMS/week-01.md。完成后勾选第 2 天任务并运行 ai-career-status.sh。", remind me date:(current date) + (1 * days)}
		end if
		set knowledgeTitle to "知识储备：完成本周 RAG 知识卡"
		set existingKnowledgeReminders to (every reminder whose name is knowledgeTitle)
		if (count of existingKnowledgeReminders) is 0 then
			make new reminder with properties {name:knowledgeTitle, body:"阅读一份 RAG 基础材料，完成知识卡并记录对 RAG-CMS 的一个可验证启发。", remind me date:(current date) + (1 * days)}
		end if
	end tell
end tell

return "AI 转型计划的 Calendar 周期安排和下一步提醒已创建。"
