
import navigationMethods from '../features/admin/methods/navigation.js'
import adminFormatters from '../features/admin/formatters.js'
import { createDashboardViewModel } from '../features/admin/dashboardViewModel.js'
import AdminDashboardSection from '../features/admin/components/AdminDashboardSection.vue'
import AdminUsersSection from '../features/admin/components/AdminUsersSection.vue'
import AdminRequestsSection from '../features/admin/components/AdminRequestsSection.vue'
import AdminReportsSection from '../features/admin/components/AdminReportsSection.vue'
import AdminActivitySection from '../features/admin/components/AdminActivitySection.vue'
import AdminCalendarSection from '../features/admin/components/AdminCalendarSection.vue'
import AdminStaffSection from '../features/admin/components/AdminStaffSection.vue'
import AdminServiceFeedbackSection from '../features/admin/components/AdminServiceFeedbackSection.vue'
import AdminDetailDrawers from '../features/admin/components/AdminDetailDrawers.vue'
import AdminIconButton from '../features/admin/components/AdminIconButton.vue'
import dashboardMethods from '../features/admin/methods/dashboard.js'
import usersMethods from '../features/admin/methods/users.js'
import calendarMethods from '../features/admin/methods/calendar.js'
import reportsMethods from '../features/admin/methods/reports.js'
import activityMethods from '../features/admin/methods/activity.js'
import staffMethods from '../features/admin/methods/staff.js'
import exportsMethods from '../features/admin/methods/exports.js'
import adminRequestsMethods from '../features/admin/methods/requests.js'
import feedbackMethods from '../features/admin/methods/feedback.js'
import { Button as VanButton, Dialog as VanDialog, Field as VanField } from 'vant'
import { confirmAction } from '../utils/confirmAction.js'

const EMPTY_PAGE = { total: 0, items: [] }

export default {
  name: 'AdminConsole',
  components: { AdminDashboardSection, AdminUsersSection, AdminRequestsSection, AdminReportsSection, AdminActivitySection, AdminCalendarSection, AdminStaffSection, AdminServiceFeedbackSection, AdminDetailDrawers, AdminIconButton, VanButton, VanDialog, VanField },
  data() {
    return {
      activeTab: 'overview',
      tabs: [
        { id: 'overview', index: '01', label: '总览' },
        { id: 'users', index: '02', label: '用户' },
        { id: 'requests', index: '03', label: '申请交付' },
        { id: 'calendar', index: '04', label: '日历' },
        { id: 'reports', index: '05', label: '报告' },
        { id: 'logs', index: '06', label: '日志' },
        { id: 'staff', index: '07', label: '后台成员' },
        { id: 'feedback', index: '08', label: '服务反馈' }
      ],
      dashboardRanges: [{ id: '7d', label: '7 天' }, { id: '30d', label: '30 天' }, { id: '90d', label: '90 天' }],
      dashboardRange: '30d',
      dashboard: null,
      dashboardLoading: false,
      dashboardLoadError: false,
      lastUpdated: '',
      autoRefresh: true,
      refreshTimer: null,
      users: { ...EMPTY_PAGE },
      usersLoading: false,
      userFilters: { search: '', role: '', is_active: '', created_from: '', created_to: '' },
      userPage: 1,
      userPageSize: 12,
      staffUsers: [],
      requestKind: 'consultant',
      adminServiceRequests: { ...EMPTY_PAGE },
      adminCalendarRequests: { ...EMPTY_PAGE },
      requestFilters: { search: '', status: '', consultant_id: '', queue_filter: '', date_from: '', date_to: '' },
      calendarRequestFilters: { search: '', status: '', stalled_only: false, date_from: '', date_to: '' },
      requestPage: 1,
      requestPageSize: 20,
      requestsLoading: false,
      consultantWorkloads: [],
      consultantWorkloadPeriodDays: 30,
      consultantWorkloadError: '',
      consultantWorkloadLoading: false,
      assignmentRequest: null,
      assignmentSavingKey: '',
      assignmentError: '',
      retryingRequestKey: '',
      serviceFeedback: { total: 0, page: 1, size: 20, items: [] },
      feedbackFilters: { search: '', status: '', feedback_type: '', service_type: '', date_from: '', date_to: '' },
      feedbackView: 'feedback',
      serviceQualitySummary: null,
      serviceQualityPeriodDays: 30,
      serviceQualityLoading: false,
      serviceQualityError: '',
      feedbackPage: 1,
      feedbackPageSize: 20,
      feedbackLoading: false,
      feedbackSavingId: null,
      qualityIssues: { total: 0, page: 1, size: 20, items: [] },
      qualityFilters: { search: '', status: 'OPEN', severity: '', source_type: '', date_from: '', date_to: '' },
      qualityPage: 1,
      qualityPageSize: 20,
      qualityLoading: false,
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
      userPanelPendingRequests: 0,
      userDetailLoadId: 0,
      userEdit: {},
      profileSaving: false,
      userPanelData: { timeline: null, reports: null, calendars: null, decisions: null, activity: null, applications: null },
      timelineLoading: false,
      timelineError: '',
      reportDetail: null,
      logDetail: null,
      drawerTrigger: null,
      calendarUsers: [],
      calendarUserSearch: '',
      selectedCalendarUser: null,
      calendars: [],
      calendarLoading: false,
      calendarUsersLoading: false,
      calendarPreviewId: null,
      calendarPreviewDecisionLogs: [],
      calendarPreviewError: '',
      calendarPreviewLoading: false,
      calendarPreviewRequestId: 0,
      calendarForm: { visible: false, id: null, title: '', note: '', start_date: '', end_date: '', status: '', version_number: 1, entries: [] },
      calendarSaving: false,
      showCalendarImport: false,
      calendarImportJson: '',
      inviteForm: { phone: '', role: 'consultant', consultant_type: 'mingli' },
      inviteToken: '',
      inviteSaving: false,
      consultantSpecialtySavingId: null,
      staffLoading: false,
      loggingOut: false,
      passwordDialog: { visible: false, user: null, password: '', showPassword: false, error: '', submitting: false },
      message: ''
    }
  },
  computed: {
    activeLoading() {
      return this.dashboardLoading || this.calendarSaving || this.userPanelLoading || this.usersLoading || this.requestsLoading || this.assignmentSavingKey !== '' || this.retryingRequestKey !== '' || this.feedbackLoading || this.serviceQualityLoading || this.feedbackSavingId !== null || this.qualityLoading || this.reportsLoading || this.tasksLoading || this.auditLoading || this.decisionLoading || this.calendarLoading || this.calendarUsersLoading || this.staffLoading || this.consultantWorkloadLoading || this.profileSaving || this.inviteSaving || this.consultantSpecialtySavingId !== null || this.passwordDialog.submitting
    },
    dashboardViewModel() {
      return createDashboardViewModel(this.dashboard)
    },
    userPanelTabs() {
      return [
        { id: 'overview', label: '概览' },
        { id: 'profile', label: '资料' },
        { id: 'applications', label: '申请' },
        { id: 'reports', label: '报告' },
        { id: 'calendar', label: '日历' },
        { id: 'decisions', label: '行动记录' },
        { id: 'activity', label: '审计活动' }
      ]
    },
    feedbackAssignees() {
      return this.staffUsers.filter(member => member.role === 'admin' && member.is_active)
    }
  },
  watch: {
    detailUser: 'syncDrawerBodyLock',
    reportDetail: 'syncDrawerBodyLock',
    logDetail: 'syncDrawerBodyLock',
    'passwordDialog.visible': 'clearPasswordDialog',
    activeTab(value) { if (value !== 'requests') this.assignmentRequest = null }
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
    confirmAction,
    ...navigationMethods,
    ...adminFormatters,
    ...dashboardMethods,
    ...usersMethods,
    ...calendarMethods,
    ...reportsMethods,
    ...activityMethods,
    ...staffMethods,
    ...exportsMethods,
    ...adminRequestsMethods,
    ...feedbackMethods
  }
}
