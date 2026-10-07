import { CALENDAR_REQUEST_STATUS_LABELS } from '../../utils/displayLabels.js'

const stages = {
  'calendar.temporal_analysis': '分析30天时序',
  'calendar.monthly_tone': '整理月度总基调',
  'calendar.daily_authoring': '编写逐日决策建议',
  'calendar.calibration': '校准整月内容'
}
export function calendarGenerationText(request) {
  if (request.status === 'queued') return '已提交，等待开始生成'
  if (request.status === 'generating') return `${stages[request.generation_stage] || '正在准备日历'} · ${request.completed_runs || 0}/${request.total_runs || 8}`
  if (request.status === 'failed') return '生成未通过校验，可使用同一份资料重试'
  if (request.status === 'fulfilled') return '已生成并交付'
  if (request.status === 'delivered') return '已开放使用'
  return CALENDAR_REQUEST_STATUS_LABELS[request.status] || request.status
}
