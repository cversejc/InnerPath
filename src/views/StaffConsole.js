import { hasRole } from '../stores/auth'
import {
  SERVICE_REQUEST_STATUS_LABELS,
  birthSummary as formatBirthSummary,
  errorText,
  formatDate,
  genderLabel,
  prettyJson,
  requestGoal,
  topicLabel
} from '../features/service-requests/formatters.js'
import {
  calendarEditorFromPayload,
  reportEditorFromPayload
} from '../features/service-requests/payloads.js'
import assignmentMethods from '../features/service-requests/methods/assignment.js'
import queueMethods from '../features/service-requests/methods/queue.js'
import workflowMethods from '../features/service-requests/methods/workflow.js'

export default {
  name: 'StaffConsole',
  data() {
    const admin = hasRole('admin')
    return {
      admin,
      scope: admin ? 'all' : 'available',
      scopeOptions: admin
        ? [{ id: 'all', label: '全部申请' }, { id: 'available', label: '待接单' }, { id: 'mine', label: '我的处理中' }]
        : [{ id: 'available', label: '待接单' }, { id: 'mine', label: '我的处理中' }],
      serviceType: '',
      statusFilter: '',
      statusOptions: ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing', 'needs_info', 'failed', 'delivered'],
      requests: { total: 0, items: [] },
      selectedRequest: null,
      workspace: null,
      loading: false,
      accepting: false,
      aiStarting: false,
      saving: false,
      delivering: false,
      infoSaving: false,
      pollingTask: false,
      task: null,
      pollTimer: null,
      message: '',
      showInfoPanel: false,
      infoReason: '',
      reportEditor: reportEditorFromPayload(),
      calendarEditor: calendarEditorFromPayload(),
      consultants: [],
      assignmentId: null,
      assignmentSaving: false
    }
  },
  computed: {
    scopeDescription() {
      if (this.scope === 'available') return '仅展示还未被接单的申请。'
      if (this.scope === 'mine') return '展示分配给当前咨询师的申请。'
      return '管理员可查看全量申请并介入处理。'
    },
    birthSummary() {
      return formatBirthSummary(this.workspace)
    }
  },
  mounted() {
    this.loadRequests()
    this.loadConsultants()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    ...queueMethods,
    ...workflowMethods,
    ...assignmentMethods,
    addEntry() {
      this.calendarEditor.entries.push({
        _key: `new-${Date.now()}-${Math.random()}`,
        entry_date: '',
        tone: 'yellow',
        status_label: '',
        keyword: '',
        summary: '',
        suitableText: '',
        unsuitableText: '',
        time_window: '',
        admin_note: ''
      })
    },
    removeEntry(index) {
      this.calendarEditor.entries.splice(index, 1)
    },
    statusLabel(status) {
      return SERVICE_REQUEST_STATUS_LABELS[status] || status
    },
    genderLabel,
    topicLabel,
    requestGoal,
    formatDate,
    pretty: prettyJson,
    errorText
  }
}
