import { topicLabel } from './formatters.js'
import { formatDateTime } from '../../utils/dateTime.js'
import { SERVICE_TYPE_LABELS } from '../../utils/displayLabels.js'

export const CUSTOMER_SERVICE_REQUEST_STATUS_LABELS = {
  submitted: '等待咨询师接单',
  accepted: '咨询师已接单',
  ai_processing: '正在准备分析',
  processing: '处理中',
  ai_ready: '等待咨询师审校',
  reviewing: '咨询师审校中',
  needs_info: '需要补充资料',
  failed: '分析暂时失败',
  delivered: '已完成',
  workflow_complete: '内容审核完成',
  withdrawn: '已撤回',
  rejected: '暂未受理'
}

export function customerServiceTypeLabel(type) {
  return type === 'calendar' ? `${SERVICE_TYPE_LABELS.calendar}申请` : `${SERVICE_TYPE_LABELS.report}申请`
}

export function customerServiceRequestStatusLabel(status) {
  return CUSTOMER_SERVICE_REQUEST_STATUS_LABELS[status] || status
}

export { formatDateTime as formatCustomerServiceRequestDateTime }

export function canWithdrawServiceRequest(status) {
  return status === 'submitted' || status === 'needs_info'
}

export function serviceRequestEditPath(item) {
  if (item.service_type === 'report') {
    return item.report_case_id
      ? `/pages/requests/requests#request-${item.id}-supplement`
      : '/pages/assessment/assessment?requestId=' + item.id
  }
  return '/pages/calendar/calendar?generate=1'
}

export { topicLabel }
