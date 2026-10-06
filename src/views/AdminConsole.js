
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
import AdminLLMSection from '../features/admin/components/AdminLLMSection.vue'
import AdminDetailDrawers from '../features/admin/components/AdminDetailDrawers.vue'
import AdminIconButton from '../features/admin/components/AdminIconButton.vue'
import OperationsShell from '../components/OperationsShell.vue'
import dashboardMethods from '../features/admin/methods/dashboard.js'
import usersMethods from '../features/admin/methods/users.js'
import calendarMethods from '../features/admin/methods/calendar.js'
import reportsMethods from '../features/admin/methods/reports.js'
import activityMethods from '../features/admin/methods/activity.js'
import staffMethods from '../features/admin/methods/staff.js'
import exportsMethods from '../features/admin/methods/exports.js'
import adminRequestsMethods from '../features/admin/methods/requests.js'
import { Button as VanButton, Dialog as VanDialog, Field as VanField } from 'vant'
import { confirmAction } from '../utils/confirmAction.js'
import { authState } from '../stores/auth.js'

const EMPTY_PAGE = { total: 0, items: [] }

export default {
  name: 'AdminConsole',
  components: { AdminDashboardSection, AdminUsersSection, AdminRequestsSection, AdminReportsSection, AdminActivitySection, AdminCalendarSection, AdminStaffSection, AdminLLMSection, AdminDetailDrawers, AdminIconButton, OperationsShell, VanButton, VanDialog, VanField },
  data() {
    return {
      activeTab: 'overview',
      tabs: [
        { id: 'overview', index: '01', label: '总览', icon: 'compass', group: 'workspace', eyebrow: 'OPERATIONS OVERVIEW', description: '快速掌握用户、交付和系统运行状态。' },
        { id: 'requests', index: '02', label: '申请交付', icon: 'inbox', group: 'workspace', eyebrow: 'REQUESTS / DELIVERY', description: '跟进用户申请、负责人和每个交付节点。' },
        { id: 'users', index: '03', label: '用户', icon: 'person', group: 'data', eyebrow: 'USER DIRECTORY', description: '管理账户状态、角色和用户关联数据。' },
        { id: 'calendar', index: '04', label: '日历', icon: 'calendar', group: 'data', eyebrow: 'DECISION CALENDAR', description: '维护已交付日历和用户行动计划。' },
        { id: 'reports', index: '05', label: '报告', icon: 'reports', group: 'data', eyebrow: 'REPORT PIPELINE', description: '查看报告版本、生成状态和异常任务。' },
        { id: 'logs', index: '06', label: '日志', icon: 'document', group: 'system', eyebrow: 'AUDIT / ACTIVITY', description: '追踪关键操作、决策记录和任务运行轨迹。' },
        { id: 'staff', index: '07', label: '后台成员', icon: 'group', group: 'system', eyebrow: 'STAFF ACCESS', description: '管理后台成员、咨询方向和邀请权限。' },
        { id: 'models', index: '08', label: '模型配置', icon: 'settings', group: 'system', eyebrow: 'MODEL CONTROL', description: '维护 AI 服务商、模型和运行参数。' }
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
      requestKind: 'consultant',
      adminServiceRequests: { ...EMPTY_PAGE },
      adminCalendarRequests: { ...EMPTY_PAGE },
      requestFilters: { search: '', status: '', consultant_id: '', date_from: '', date_to: '' },
      calendarRequestFilters: { search: '', status: '', date_from: '', date_to: '' },
      requestPage: 1,
      requestPageSize: 20,
      requestsLoading: false,
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
      userEdit: {},
      profileSaving: false,
      userPanelData: { reports: null, calendars: null, decisions: null, activity: null, applications: null },
      reportDetail: null,
      logDetail: null,
      drawerTrigger: null,
      calendarUsers: [],
      calendarUserSearch: '',
      selectedCalendarUser: null,
      calendars: [],
      calendarLoading: false,
      calendarUsersLoading: false,
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
    adminNavGroups() {
      const groups = [
        { id: 'workspace', label: '运营工作台' },
        { id: 'data', label: '数据管理' },
        { id: 'system', label: '系统设置' }
      ]
      return groups.map(group => ({ ...group, items: this.tabs.filter(tab => tab.group === group.id) }))
    },
    operationsNavGroups() {
      return [
        ...this.adminNavGroups.map(group => ({
          ...group,
          items: group.items.map(item => ({
            ...item,
            active: this.activeTab === item.id
          }))
        })),
        {
          id: 'workbenches',
          label: '协作工作台',
          items: [
            { id: 'consultant-workbench', label: '咨询师工作台', icon: 'group', to: '/staff' },
            { id: 'skill-studio', label: '技能工作台', icon: 'spark', to: { path: '/skills', query: { return_to: '/admin' } } }
          ]
        }
      ]
    },
    activeTabInfo() {
      return this.tabs.find(tab => tab.id === this.activeTab) || this.tabs[0]
    },
    operatorName() {
      return authState.user?.name || '管理员'
    },
    activeLoading() {
      return this.dashboardLoading || this.calendarSaving || this.userPanelLoading || this.usersLoading || this.requestsLoading || this.reportsLoading || this.tasksLoading || this.auditLoading || this.decisionLoading || this.calendarLoading || this.calendarUsersLoading || this.staffLoading || this.profileSaving || this.inviteSaving || this.consultantSpecialtySavingId !== null || this.passwordDialog.submitting
    },
    dashboardViewModel() {
      return createDashboardViewModel(this.dashboard)
    },
    userPanelTabs() {
      return [
        { id: 'profile', label: '资料' },
        { id: 'applications', label: '申请' },
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
    logDetail: 'syncDrawerBodyLock',
    'passwordDialog.visible': 'clearPasswordDialog'
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
    ...adminRequestsMethods
  }
}
