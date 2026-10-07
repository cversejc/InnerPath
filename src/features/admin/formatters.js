import { formatDate, formatDateTime } from '../../utils/dateTime.js'

import {
  CALENDAR_REQUEST_STATUS_LABELS,
  CALENDAR_STATUS_LABELS,
  DECISION_STATUS_LABELS,
  REPORT_CASE_STATUS_LABELS,
  REPORT_STATUS_LABELS,
  ROLE_LABELS,
  SERVICE_REQUEST_STATUS_LABELS
} from '../../utils/displayLabels.js'

export { formatDate, formatDateTime }

export function pageCount(total, size) {
  return Math.max(1, Math.ceil((total || 0) / size))
}

export function distributionTotal(items) {
  return (items || []).reduce((sum, item) => sum + item.value, 0)
}

export function distributionWidth(item, items) {
  const max = Math.max(1, ...(items || []).map(value => value.value))
  return (item.value / max) * 100
}

export function formatShortDate(value) {
  return value ? `${String(value).slice(5, 7)}/${String(value).slice(8, 10)}` : '—'
}

export function reportStatusText(value) {
  return REPORT_STATUS_LABELS[value] || value || '—'
}

export function calendarStatusText(value) {
  return CALENDAR_STATUS_LABELS[value] || value || '—'
}

export function decisionStatusText(value) {
  return DECISION_STATUS_LABELS[value] || value || '—'
}

export function serviceRequestStatusText(value) {
  return SERVICE_REQUEST_STATUS_LABELS[value] || value || '—'
}

export function calendarRequestStatusText(value) {
  return CALENDAR_REQUEST_STATUS_LABELS[value] || value || '—'
}

export function roleText(value) {
  return ROLE_LABELS[value] || value || '—'
}

export function reportCaseStatusText(value) {
  return REPORT_CASE_STATUS_LABELS[value] || value || '—'
}

export function timezoneText(value) {
  return {
    'Asia/Shanghai': '中国标准时间（上海）',
    'Asia/Chongqing': '中国标准时间（重庆）',
    'Asia/Beijing': '中国标准时间（北京）'
  }[value] || value || '—'
}

export function resourceLabel(value) {
  return { user: '用户', calendar: '日历', calendar_request: '日历申请', report: '报告', report_task: '报告任务', decision_log: '行动记录', service_request: '服务申请', service_feedback: '服务反馈', report_quality_issue: '报告质检记录', audit_log: '审计日志', dashboard: '运营仪表盘', consultant_workload: '咨询师工作量', export: '管理数据导出', staff_invite: '成员邀请', auth: '认证' }[value] || value || '—'
}

export function actionLabel(value) {
  return {
    'auth.register': '注册账号', 'auth.login.success': '登录成功', 'auth.login.failure': '登录失败', 'auth.logout': '退出登录',
    'user.profile.update': '更新资料', 'user.profile.update.admin': '管理员更新资料', 'user.status.update': '更新账号状态',
    'admin.users.list': '管理员浏览用户列表', 'admin.user.read': '管理员查看用户资料', 'admin.user.summary.read': '管理员查看用户统计',
    'admin.user.timeline.read': '管理员查看用户时间线', 'admin.reports.list': '管理员浏览报告列表', 'admin.report.read': '管理员查看完整报告',
    'admin.report_tasks.list': '管理员浏览报告任务', 'admin.decision_logs.list': '管理员浏览行动记录',
    'admin.service_requests.list': '管理员浏览服务申请', 'admin.calendar_requests.list': '管理员浏览日历申请',
    'admin.calendar.read': '管理员查看用户日历', 'admin.service_feedback.list': '管理员浏览服务反馈',
    'admin.audit_logs.list': '管理员浏览审计日志', 'admin.dashboard.overview.read': '管理员查看运营仪表盘',
    'admin.consultant_workload.read': '管理员查看咨询师工作量',
    'admin.report_quality_issues.list': '管理员浏览报告质检记录', 'admin.export.csv': '管理员导出管理数据',
    'user.role.update': '更新角色', 'user.password.reset': '重置密码', 'user.password.change': '修改密码',
    'consultant.specialties.update': '调整咨询师服务方向',
    'calendar.create': '创建日历', 'calendar.import': '导入日历', 'calendar.update': '更新日历', 'calendar.revision.create': '创建日历版本',
    'calendar.publish': '发布日历', 'calendar.archive': '归档日历', 'calendar.request.create': '提交日历申请', 'calendar.request.update': '处理日历申请',
    'decision_log.create': '新增行动记录', 'decision_log.delete': '删除行动记录',
    'service_request.create': '提交报告申请', 'service_request.update': '修改申请资料', 'service_request.resubmit': '补充后重新提交',
    'service_request.withdraw': '撤回申请', 'service_request.accept': '咨询师接单', 'service_request.assignment.update': '调整咨询师分配',
    'service_request.ai.start': '启动 AI 初稿', 'service_request.ai.completed': 'AI 初稿完成', 'service_request.ai.failed': 'AI 初稿失败',
    'service_request.draft.save': '保存咨询师审校稿', 'service_request.needs_info': '请求用户补充资料',
    'service_request.deliver': '咨询师交付报告', 'service_request.reject': '关闭服务申请',
    'calendar.generation.retry': '重试日历生成',
    'report.task.create': '创建报告任务', 'report.task.completed': '报告生成完成', 'report.task.failed': '报告生成失败',
    'report.task.retry': '重试报告任务', 'report.delete': '删除报告', 'staff.invite.create': '创建成员邀请', 'staff.invite.accept': '接受成员邀请'
  }[value] || value || '未知操作'
}

export function prettyJson(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value
    }
  }
  return JSON.stringify(value, null, 2)
}

export default {
  pageCount,
  distributionTotal,
  distributionWidth,
  formatDate,
  formatShortDate,
  formatDateTime,
  reportStatusText,
  calendarStatusText,
  decisionStatusText,
  serviceRequestStatusText,
  calendarRequestStatusText,
  reportCaseStatusText,
  timezoneText,
  roleText,
  resourceLabel,
  actionLabel,
  prettyJson
}
