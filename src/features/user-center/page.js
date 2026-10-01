import { hasRole } from '../../stores/auth.js'
import AccountSettingsPanel from './components/AccountSettingsPanel.vue'
import DecisionCalendarPanel from './components/DecisionCalendarPanel.vue'
import ReportsPanel from './components/ReportsPanel.vue'
import RequestsPanel from './components/RequestsPanel.vue'
import ProfileGrowthCard from '../../components/ProfileGrowthCard.vue'
import { createEmptyProfile } from './profile.js'
import accountMethods from './methods/account.js'
import dashboardMethods from './methods/dashboard.js'
import navigationMethods from './methods/navigation.js'

export default {
  name: 'UserCenter',
  components: {
    AccountSettingsPanel,
    DecisionCalendarPanel,
    ProfileGrowthCard,
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
        { id: 'settings', icon: 'settings', label: '设置' }
      ],
      reports: [],
      requests: [],
      settings: createEmptyProfile(),
      profileCompletion: 0,
      profileLastConfirmedAt: null,
      optionalProfileExpanded: false,
      settingsErrors: {},
      settingsError: '',
      passwordForm: { current: '', next: '' },
      savingSettings: false,
      savingPassword: false,
      loggingOut: false
    }
  },
  computed: {
    isAdmin() {
      return hasRole('admin')
    }
  },
  async mounted() {
    if (['reports', 'calendar', 'settings'].includes(this.$route.query.tab)) {
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
