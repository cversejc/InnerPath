import { hasRole } from '../../stores/auth.js'
import AccountSettingsPanel from './components/AccountSettingsPanel.vue'
import DecisionCalendarPanel from './components/DecisionCalendarPanel.vue'
import ProfileSettingsPanel from './components/ProfileSettingsPanel.vue'
import ReportsPanel from './components/ReportsPanel.vue'
import RequestsPanel from './components/RequestsPanel.vue'
import { createEmptyProfile } from '../users/profile.js'
import { buildCalendarCover } from '../calendar/cover.js'
import accountMethods from './methods/account.js'
import dashboardMethods from './methods/dashboard.js'
import navigationMethods from './methods/navigation.js'

export default {
  name: 'UserCenter',
  components: {
    AccountSettingsPanel,
    DecisionCalendarPanel,
    ProfileSettingsPanel,
    ReportsPanel,
    RequestsPanel
  },
  data() {
    return {
      userName: '用户',
      userType: '成长探索者',
      activeTab: 'reports',
      loading: true,
      message: '',
      tabs: [
        { id: 'reports', icon: 'reports', label: '报告' },
        { id: 'calendar', icon: 'calendar', label: '日历' },
        { id: 'requests', icon: 'document', label: '我的申请' },
        { id: 'profile', icon: 'person', label: '本人画像' },
        { id: 'settings', icon: 'settings', label: '账号设置' }
      ],
      reports: [],
      calendarCover: buildCalendarCover(null),
      requests: [],
      settings: createEmptyProfile(),
      optionalProfileExpanded: false,
      settingsErrors: {},
      settingsError: '',
      accountPhone: '',
      phoneChangeForm: { newPhone: '', code: '', currentPassword: '' },
      phoneChangeError: '',
      phoneChangeMessage: '',
      requestingPhoneCode: false,
      savingPhoneChange: false,
      passwordForm: { current: '', next: '' },
      savingSettings: false,
      savingPassword: false,
      loggingOut: false,
      deactivating: false,
      deactivationError: ''
    }
  },
  computed: {
    isAdmin() {
      return hasRole('admin')
    }
  },
  async mounted() {
    if (['reports', 'calendar', 'profile', 'settings'].includes(this.$route.query.tab)) {
      this.activeTab = this.$route.query.tab
    }
    await this.loadDashboard()
  },
  methods: {
    ...dashboardMethods,
    ...navigationMethods,
    ...accountMethods
  }
}
