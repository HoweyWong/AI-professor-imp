[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Arguments = @($Arguments | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
$notify = $true
if ($Arguments.Count -gt 0) {
    if ($Arguments.Count -ne 1 -or $Arguments[0] -notin @('-NoNotify', '--no-notify')) {
        [Console]::Error.WriteLine("用法：$($MyInvocation.MyCommand.Path) [-NoNotify|--no-notify]")
        exit 2
    }
    $notify = $false
}

$workspace = Split-Path -Parent $PSScriptRoot

function Get-LatestPlanFile {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][string]$Filter
    )

    $files = @(Get-ChildItem -LiteralPath $Directory -File -Filter $Filter | Sort-Object -Property Name)
    if ($files.Count -eq 0) {
        return $null
    }

    return $files[-1]
}

function Get-MatchingCount {
    param(
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]]$Lines = @(),
        [Parameter(Mandatory = $true)][string]$Pattern
    )

    return @($Lines | Where-Object { $_ -match $Pattern }).Count
}

function Get-FirstMatchingLine {
    param(
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]]$Lines = @(),
        [Parameter(Mandatory = $true)][string]$Pattern
    )

    $matchingLines = @($Lines | Where-Object { $_ -match $Pattern })
    if ($matchingLines.Count -eq 0) {
        return $null
    }

    return $matchingLines[0]
}

function Format-NextItem {
    param(
        [string]$Item,
        [Parameter(Mandatory = $true)][string]$Fallback
    )

    if ([string]::IsNullOrWhiteSpace($Item)) {
        return $Fallback
    }

    $formattedItem = $Item -replace '^- \[ \] ', ''
    if ($formattedItem -match '^(?<deadline>\d{4}-\d{2}-\d{2})') {
        $deadline = [datetime]::ParseExact(
            $Matches['deadline'],
            'yyyy-MM-dd',
            [Globalization.CultureInfo]::InvariantCulture
        )
        if ($deadline.Date -lt (Get-Date).Date) {
            return "[已逾期] $formattedItem"
        }
    }

    return $formattedItem
}

function Send-StatusNotification {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Message
    )

    try {
        if ($env:OS -ne 'Windows_NT') {
            throw '当前不是 Windows 会话'
        }

        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        Add-Type -AssemblyName System.Drawing -ErrorAction Stop
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.SystemIcons]::Information
        $notification.Visible = $true
        $notification.ShowBalloonTip(5000, $Title, $Message, [System.Windows.Forms.ToolTipIcon]::Info)
        Start-Sleep -Milliseconds 500
        $notification.Dispose()
    }
    catch {
        Write-Warning '提示：当前环境不支持 Windows 通知，仅输出检查结果。'
    }
}

$taskFile = Get-LatestPlanFile -Directory (Join-Path $workspace '02-Projects/RAG-CMS') -Filter 'week-*.md'
$knowledgeFile = Get-LatestPlanFile -Directory (Join-Path $workspace '05-Weekly-Reviews') -Filter 'knowledge-week-*.md'
$caseFile = Join-Path $workspace '03-Architecture-Cases/case-plan.md'
$reportFile = Join-Path $workspace '04-Industry-Reports/report-plan.md'
$outcomesFile = Join-Path $workspace '05-Weekly-Reviews/90-day-outcomes.md'

if ($null -eq $taskFile -or $null -eq $knowledgeFile -or -not (Test-Path -LiteralPath $caseFile -PathType Leaf) -or -not (Test-Path -LiteralPath $reportFile -PathType Leaf) -or -not (Test-Path -LiteralPath $outcomesFile -PathType Leaf)) {
    [Console]::Error.WriteLine('找不到项目、知识、架构案例、行业报告或阶段成果计划文件')
    exit 1
}

$taskLines = @(Get-Content -LiteralPath $taskFile.FullName)
$knowledgeLines = @(Get-Content -LiteralPath $knowledgeFile.FullName)
$caseLines = @(Get-Content -LiteralPath $caseFile)
$reportLines = @(Get-Content -LiteralPath $reportFile)
$outcomesLines = @(Get-Content -LiteralPath $outcomesFile)

$nextTask = Get-FirstMatchingLine -Lines $taskLines -Pattern '^- \[ \] 第'
$doneCount = Get-MatchingCount -Lines $taskLines -Pattern '^- \[x\] 第'
$totalCount = Get-MatchingCount -Lines $taskLines -Pattern '^- \[[ x]\] 第'

$nextKnowledge = Get-FirstMatchingLine -Lines $knowledgeLines -Pattern '^- \[ \]'
$knowledgeDone = Get-MatchingCount -Lines $knowledgeLines -Pattern '^- \[x\]'
$knowledgeTotal = Get-MatchingCount -Lines $knowledgeLines -Pattern '^- \[[ x]\]'

$nextCase = Get-FirstMatchingLine -Lines $caseLines -Pattern '^- \[ \]'
$caseDone = Get-MatchingCount -Lines $caseLines -Pattern '^- \[x\]'
$caseTargetLine = Get-FirstMatchingLine -Lines $caseLines -Pattern '^- 目标数量：'
$caseTargetMatch = [regex]::Match([string]$caseTargetLine, '^- 目标数量：\s*(.+?)\s*$')

$nextReport = Get-FirstMatchingLine -Lines $reportLines -Pattern '^- \[ \]'
$reportDone = Get-MatchingCount -Lines $reportLines -Pattern '^- \[x\]'
$reportTargetLine = Get-FirstMatchingLine -Lines $reportLines -Pattern '^- 目标数量：'
$reportTargetMatch = [regex]::Match([string]$reportTargetLine, '^- 目标数量：\s*(.+?)\s*$')

$nextOutcome = Get-FirstMatchingLine -Lines $outcomesLines -Pattern '^- \[ \]'
$outcomesDone = Get-MatchingCount -Lines $outcomesLines -Pattern '^- \[x\]'
$outcomesTotal = Get-MatchingCount -Lines $outcomesLines -Pattern '^- \[[ x]\]'

if (-not $caseTargetMatch.Success -or -not $reportTargetMatch.Success) {
    [Console]::Error.WriteLine('架构案例或行业报告计划缺少目标数量')
    exit 1
}

if ([string]::IsNullOrWhiteSpace($nextTask)) {
    $nextTask = '最新项目周计划已完成，请复盘并创建下一周计划'
}
else {
    $nextTask = $nextTask -replace '^- \[ \] ', ''
}

if ([string]::IsNullOrWhiteSpace($nextKnowledge)) {
    $nextKnowledge = '最新知识周计划已完成，请复盘并创建下一周主题'
}
else {
    $nextKnowledge = $nextKnowledge -replace '^- \[ \] ', ''
}

$nextCase = Format-NextItem -Item $nextCase -Fallback '架构案例未设置下一项，请先复盘再选择一个题目'
$nextReport = Format-NextItem -Item $nextReport -Fallback '行业报告未设置下一项，请选择本月唯一报告'
$nextOutcome = Format-NextItem -Item $nextOutcome -Fallback '90 天阶段检查已完成，请整理最终成果'

$title = 'AI 转型计划｜四轨与阶段检查'
$message = "项目 $doneCount/$totalCount；知识 $knowledgeDone/$knowledgeTotal；架构案例 $caseDone/$($caseTargetMatch.Groups[1].Value)；行业报告 $reportDone/$($reportTargetMatch.Groups[1].Value)；阶段成果 $outcomesDone/$outcomesTotal。"

if ($notify) {
    Send-StatusNotification -Title $title -Message $message
}

Write-Output $title
Write-Output $message
Write-Output "项目：$nextTask"
Write-Output "知识：$nextKnowledge"
Write-Output "架构案例：$nextCase"
Write-Output "行业报告：$nextReport"
Write-Output "阶段成果：$nextOutcome"
Write-Output "项目文件：$($taskFile.FullName)"
Write-Output "知识文件：$($knowledgeFile.FullName)"
Write-Output "架构案例文件：$caseFile"
Write-Output "行业报告文件：$reportFile"
Write-Output "阶段成果文件：$outcomesFile"
