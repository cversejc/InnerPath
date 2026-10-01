export function formatUserCenterDate(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
}

export function requestStatusLabel(status) {
  return {
    submitted: '等待接单',
    accepted: '已接单',
    ai_processing: '准备分析',
    ai_ready: '等待审校',
    reviewing: '审校中',
    needs_info: '需补资料',
    failed: '分析失败',
    delivered: '已完成',
    withdrawn: '已撤回',
    rejected: '暂未受理'
  }[status] || status
}

export function requestEditPath(request) {
  return request.service_type === 'report'
    ? `/pages/assessment/assessment?requestId=${request.id}`
    : `/pages/requests/new?type=calendar&requestId=${request.id}`
}
