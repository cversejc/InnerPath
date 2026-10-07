import { formatDate, formatDateTime } from '../../utils/dateTime.js'

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
  return { processing: '生成中', completed: '已完成', failed: '失败' }[value] || value || '—'
}

export function calendarStatusText(value) {
  return { draft: '草稿', published: '已发布', archived: '已归档' }[value] || value || '—'
}

export function decisionStatusText(value) {
  return { done: '已完成', doing: '进行中', skipped: '已跳过' }[value] || value || '—'
}

export function serviceRequestStatusText(value) {
  return {
    submitted: '待接单', accepted: '已接单', ai_processing: '生成初稿', ai_ready: '待审校',
    reviewing: '审校中', needs_info: '待补充', failed: '处理失败', delivered: '已交付',
    withdrawn: '已撤回', rejected: '已关闭'
  }[value] || value || '—'
}

export function calendarRequestStatusText(value) {
  return {
    pending: '待生成', processing: '生成中', delivered: '已交付', failed: '生成失败',
    reviewing: '审核中', fulfilled: '已完成', rejected: '已退回', cancelled: '已取消'
  }[value] || value || '—'
}

export function roleText(value) {
  return { user: '用户', consultant: '咨询师', admin: '管理员' }[value] || value || '—'
}

export function resourceLabel(value) {
  return { user: '用户', calendar: '日历', calendar_request: '日历申请', report: '报告', report_task: '报告任务', decision_log: '行动记录', service_request: '服务申请', staff_invite: '成员邀请', auth: '认证' }[value] || value || '—'
}

export function actionLabel(value) {
  return {
    'auth.register': '注册账号', 'auth.login.success': '登录成功', 'auth.login.failure': '登录失败', 'auth.logout': '退出登录',
    'user.profile.update': '更新资料', 'user.profile.update.admin': '管理员更新资料', 'user.status.update': '更新账号状态',
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
  roleText,
  resourceLabel,
  actionLabel,
  prettyJson
}
