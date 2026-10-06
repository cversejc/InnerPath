import { Button as VanButton } from 'vant'
import customerRequestMethods from './methods/customer-requests.js'
import ServiceFeedbackControl from '../service-feedback/components/ServiceFeedbackControl.vue'
import { confirmAction } from '../../utils/confirmAction.js'

export default {
  name: 'ServiceRequests',
  components: { VanButton, ServiceFeedbackControl },
  data() {
    return {
      requests: [],
      loading: true,
      message: '',
      messageType: 'info',
      activeFilter: 'all',
      withdrawnId: null,
      followUpAnswers: {},
      followUpResponseKeys: {},
      supplementSubmittingId: null,
      retryingCalendarId: null,
      requestRefreshTimer: null,
      requestFetchInFlight: false,
      feedbackByRequestId: {},
      feedbackReady: false,
      feedbackLoadError: false,
      filters: [
        { id: 'all', label: '全部' },
        { id: 'report', label: '报告' },
        { id: 'calendar', label: '日历' }
      ]
    }
  },
  computed: {
    hasDeliveredReport() {
      return this.requests.some(item => item.service_type === 'report' && item.status === 'delivered' && item.result_type === 'report')
    },
    calendarActionPath() {
      return this.hasDeliveredReport ? '/pages/calendar/calendar?generate=1' : '/pages/assessment/assessment'
    },
    calendarActionLabel() {
      return this.hasDeliveredReport ? '生成决策日历' : '先申请报告'
    },
    filteredRequests() {
      if (this.activeFilter === 'all') return this.requests
      return this.requests.filter(item => item.service_type === this.activeFilter)
    }
  },
  async mounted() {
    await Promise.all([this.loadRequests(), this.loadFeedback()])
    if (this.$route.query.submitted) {
      this.message = this.$route.query.kind === 'calendar'
        ? '日历生成任务已启动，成功后会自动出现在日历中。'
        : '报告申请 #' + this.$route.query.submitted + ' 已提交，接下来等待咨询师接单。'
      this.messageType = 'info'
    }
    this.syncRequestPolling()
  },
  beforeUnmount() {
    if (this.requestRefreshTimer) window.clearInterval(this.requestRefreshTimer)
  },
  methods: {
    confirmAction,
    ...customerRequestMethods
  }
}
