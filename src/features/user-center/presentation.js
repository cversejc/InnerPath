import { CALENDAR_REQUEST_STATUS_LABELS, SERVICE_REQUEST_STATUS_LABELS } from '../../utils/displayLabels.js'

export function formatUserCenterDate(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
}

export function requestStatusLabel(status, workflowType) {
  if (workflowType === 'calendar_generation') {
    return {
      ...CALENDAR_REQUEST_STATUS_LABELS,
      ai_processing: '日历生成中',
      delivered: '已开放使用',
      fulfilled: '已生成并交付'
    }[status] || status
  }
  return {
    ...SERVICE_REQUEST_STATUS_LABELS,
    ai_processing: '准备分析',
    delivered: '已完成',
    rejected: '暂未受理'
  }[status] || status
}

export function requestEditPath(request) {
  if (request.service_type === 'report') {
    return request.report_case_id
      ? `/pages/requests/requests#request-${request.id}-supplement`
      : `/pages/assessment/assessment?requestId=${request.id}`
  }
  return '/pages/calendar/calendar?generate=1'
}
