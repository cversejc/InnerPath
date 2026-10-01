import customerRequestMethods from './methods/customer-requests.js'

export default {
  name: 'ServiceRequests',
  data() {
    return {
      requests: [],
      loading: true,
      message: '',
      messageType: 'info',
      activeFilter: 'all',
      withdrawnId: null,
      filters: [
        { id: 'all', label: '全部' },
        { id: 'report', label: '报告' },
        { id: 'calendar', label: '日历' }
      ]
    }
  },
  computed: {
    filteredRequests() {
      if (this.activeFilter === 'all') return this.requests
      return this.requests.filter(item => item.service_type === this.activeFilter)
    }
  },
  async mounted() {
    await this.loadRequests()
    if (this.$route.query.submitted) {
      this.message = '申请 #' + this.$route.query.submitted + ' 已提交，接下来等待咨询师接单。'
      this.messageType = 'info'
    }
  },
  methods: {
    ...customerRequestMethods
  }
}
