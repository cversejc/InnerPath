
import {
  createStaffInvite,
  downloadAdminExport,
  getAdminAuditLogs,
  getAdminDashboard,
  getAdminUser,
  getAdminUserSummary,
  getAllAdminUsers,
  getAdminUsers,
  resetAdminUserPassword,
  updateAdminUserProfile,
  updateAdminUserRole,
  updateAdminUserStatus
} from '../features/admin/api'
import {
  archiveAdminCalendar,
  createAdminCalendar,
  createAdminCalendarDraft,
  getAdminCalendars,
  getAdminCalendarRequests,
  getAdminDecisionLogs,
  getAdminUserDecisionLogs,
  importAdminCalendar,
  publishAdminCalendar,
  updateAdminCalendar,
  updateAdminCalendarRequest
} from '../features/calendar/api'
import {
  getAdminReport,
  getAdminReportTasks,
  getAdminReports,
  retryAdminReportTask
} from '../features/reports/api'
import { logout as logoutUser } from '../stores/auth'

import navigationMethods from '../features/admin/methods/navigation.js'
import adminFormatters from '../features/admin/formatters.js'
import AdminDashboardSection from '../features/admin/components/AdminDashboardSection.vue'
import AdminUsersSection from '../features/admin/components/AdminUsersSection.vue'
import AdminCalendarRequestsSection from '../features/admin/components/AdminCalendarRequestsSection.vue'
import AdminReportsSection from '../features/admin/components/AdminReportsSection.vue'
import AdminActivitySection from '../features/admin/components/AdminActivitySection.vue'
import AdminCalendarSection from '../features/admin/components/AdminCalendarSection.vue'
import AdminStaffSection from '../features/admin/components/AdminStaffSection.vue'
import AdminDetailDrawers from '../features/admin/components/AdminDetailDrawers.vue'
import dashboardMethods from '../features/admin/methods/dashboard.js'
import usersMethods from '../features/admin/methods/users.js'
import calendarMethods from '../features/admin/methods/calendar.js'
import reportsMethods from '../features/admin/methods/reports.js'
import activityMethods from '../features/admin/methods/activity.js'
import staffMethods from '../features/admin/methods/staff.js'
import exportsMethods from '../features/admin/methods/exports.js'

const EMPTY_PAGE = { total: 0, items: [] }

function todayKey() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function createEntry(date = todayKey()) {
  return {
    _key: `entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    entry_date: date,
    day_pillar: '',
    tone: 'yellow',
    status_label: '',
    keyword: '',
    summary: '',
    suitableText: '',
    unsuitableText: '',
    time_window: '',
    admin_note: ''
  }
}

export default {
  name: 'AdminConsole',
  components: { AdminDashboardSection, AdminUsersSection, AdminCalendarRequestsSection, AdminReportsSection, AdminActivitySection, AdminCalendarSection, AdminStaffSection, AdminDetailDrawers },
  data() {
    return {
      activeTab: 'overview',
      tabs: [
        { id: 'overview', index: '01', label: '总览' },
        { id: 'users', index: '02', label: '用户' },
        { id: 'calendar-requests', index: '03', label: '日历申请' },
        { id: 'calendar', index: '04', label: '日历' },
        { id: 'reports', index: '05', label: '报告' },
        { id: 'logs', index: '06', label: '日志' },
        { id: 'staff', index: '07', label: '后台成员' }
      ],
      dashboardRanges: [{ id: '7d', label: '7 天' }, { id: '30d', label: '30 天' }, { id: '90d', label: '90 天' }],
      dashboardRange: '30d',
      dashboard: null,
      dashboardLoading: false,
      lastUpdated: '',
      autoRefresh: true,
      refreshTimer: null,
      users: { ...EMPTY_PAGE },
      usersLoading: false,
      userFilters: { search: '', role: '', is_active: '', created_from: '', created_to: '' },
      userPage: 1,
      userPageSize: 12,
      staffUsers: [],
      reports: { ...EMPTY_PAGE },
      reportsLoading: false,
      reportFilters: { search: '', status: '', ai_model: '', date_from: '', date_to: '' },
      reportPage: 1,
      reportPageSize: 12,
      reportSection: 'reports',
      reportTasks: { ...EMPTY_PAGE },
      tasksLoading: false,
      taskFilters: { search: '', status: '' },
      taskPage: 1,
      taskPageSize: 12,
      reportRetryLimit: 2,
      auditLogs: { ...EMPTY_PAGE },
      auditLoading: false,
      logFilters: { search: '', action: '', resource_type: '', actor_user_id: '', target_user_id: '', date_from: '', date_to: '' },
      logPage: 1,
      logPageSize: 20,
      decisionLogs: { ...EMPTY_PAGE },
      decisionLoading: false,
      decisionPage: 1,
      decisionPageSize: 20,
      behaviorFilters: { search: '', kind: '', status: '', date_from: '', date_to: '' },
      logSection: 'audit',
      detailUser: null,
      userSummary: null,
      userPanelTab: 'profile',
      userPanelLoading: false,
      userEdit: {},
      profileSaving: false,
      userPanelData: { reports: null, calendars: null, decisions: null, activity: null },
      reportDetail: null,
      logDetail: null,
      drawerTrigger: null,
      calendarUsers: [],
      calendarUserSearch: '',
      selectedCalendarUser: null,
      calendars: [],
      calendarLoading: false,
      calendarRequests: [],
      calendarRequestsLoading: false,
      calendarRequestStatusFilter: '',
      calendarUsersLoading: false,
      calendarForm: { visible: false, id: null, title: '', note: '', start_date: '', end_date: '', status: '', version_number: 1, entries: [] },
      calendarSaving: false,
      showCalendarImport: false,
      calendarImportJson: '',
      inviteForm: { phone: '', role: 'consultant' },
      inviteToken: '',
      inviteSaving: false,
      staffLoading: false,
      loggingOut: false,
      message: ''
    }
  },
  computed: {
    activeLoading() {
      return this.dashboardLoading || this.calendarSaving || this.userPanelLoading || this.usersLoading || this.reportsLoading || this.tasksLoading || this.auditLoading || this.decisionLoading || this.calendarLoading || this.calendarUsersLoading || this.calendarRequestsLoading || this.staffLoading || this.profileSaving || this.inviteSaving
    },
    metricCards() {
      const metrics = this.dashboard?.metrics || {}
      return [
        { key: 'users', label: '用户总数', value: metrics.user_total ?? 0, caption: `活跃 ${metrics.active_users ?? 0} · 本期新增 ${metrics.new_users ?? 0}`, mark: '人', tone: 'cinnabar' },
        { key: 'reports', label: '报告总数', value: metrics.report_total ?? 0, caption: `成功率 ${metrics.report_success_rate ?? 0}%`, mark: '笺', tone: 'gold' },
        { key: 'tasks', label: '报告任务', value: metrics.report_processing ?? 0, caption: `生成中 · 失败 ${metrics.report_failed ?? 0}`, mark: 'AI', tone: 'ink' },
        { key: 'calendars', label: '已发布日历', value: metrics.published_calendars ?? 0, caption: `用户行动记录 ${metrics.decision_logs ?? 0}`, mark: '历', tone: 'jade' }
      ]
    },
    trendMax() {
      const values = (this.dashboard?.trends || []).flatMap(item => [item.new_users, item.reports, item.decision_logs])
      return Math.max(1, ...values)
    },
    chartGridLines() {
      return [18, 67, 116, 165, 214]
    },
    trendSeries() {
      const trends = this.dashboard?.trends || []
      const series = [
        { key: 'new_users', label: '新增用户', color: '#b85c50' },
        { key: 'reports', label: '报告', color: 'var(--gold-deep, #8b5a14)' },
        { key: 'decision_logs', label: '行动记录', color: '#59483d' }
      ]
      return series.map(item => ({
        ...item,
        points: trends.map((point, index) => {
          const x = 28 + (index * 708 / Math.max(1, trends.length - 1))
          const y = 214 - ((point[item.key] || 0) / this.trendMax) * 196
          return `${x.toFixed(1)},${y.toFixed(1)}`
        }).join(' ')
      }))
    },
    trendTicks() {
      const trends = this.dashboard?.trends || []
      if (!trends.length) return []
      const step = Math.max(1, Math.ceil(trends.length / 6))
      return trends.map((point, index) => ({ index, x: 28 + (index * 708 / Math.max(1, trends.length - 1)), label: this.formatShortDate(point.date) })).filter((tick, index) => index % step === 0 || index === trends.length - 1)
    },
    distributionGroups() {
      const distributions = this.dashboard?.distributions || {}
      return [
        { key: 'roles', label: '用户角色', items: distributions.users_by_role || [] },
        { key: 'reports', label: '报告状态', items: distributions.reports_by_status || [] },
        { key: 'calendars', label: '日历状态', items: distributions.calendars_by_status || [] }
      ]
    },
    userPanelTabs() {
      return [
        { id: 'profile', label: '资料' },
        { id: 'reports', label: '报告' },
        { id: 'calendar', label: '日历' },
        { id: 'decisions', label: '行动记录' },
        { id: 'activity', label: '审计活动' }
      ]
    }
  },
  watch: {
    detailUser: 'syncDrawerBodyLock',
    reportDetail: 'syncDrawerBodyLock',
    logDetail: 'syncDrawerBodyLock'
  },
  async mounted() {
    document.addEventListener('visibilitychange', this.handleVisibilityChange)
    await Promise.all([this.loadDashboard(), this.loadUsers(), this.loadStaff()])
    this.syncAutoRefresh()
  },
  beforeUnmount() {
    document.removeEventListener('visibilitychange', this.handleVisibilityChange)
    this.clearRefreshTimer()
    document.body.classList.remove('dialog-open')
  },
  methods: {
    ...navigationMethods,
    ...adminFormatters,
    ...dashboardMethods,
    ...usersMethods,
    ...calendarMethods,
    ...reportsMethods,
    ...activityMethods,
    ...staffMethods,
    ...exportsMethods
  }
}
