import { hasRole } from '../stores/auth'
import { Button as VanButton, Dialog as VanDialog, Field as VanField } from 'vant'
import {
  SERVICE_REQUEST_STATUS_LABELS,
  birthSummary as formatBirthSummary,
  consultationTypeLabel,
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
import { confirmAction } from '../utils/confirmAction.js'

export default {
  name: 'StaffConsole',
  components: { VanButton, VanDialog, VanField },
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
      rejectDialog: { visible: false, reason: '', error: '' },
      rejectSaving: false,
      reportEditor: reportEditorFromPayload(),
      calendarEditor: calendarEditorFromPayload(),
      consultants: [],
      assignmentId: null,
      consultationType: 'integrated',
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
    },
    assignableConsultants() {
      if (this.workspace?.request.service_type !== 'report') return this.consultants
      const required = this.consultationType === 'integrated'
        ? ['metaphysics', 'psychology']
        : [this.consultationType]
      return this.consultants.filter(consultant => required.every(
        specialty => (consultant.consultant_specialties || []).includes(specialty)
      ))
    },
    assignmentChanged() {
      if (!this.workspace) return false
      const request = this.workspace.request
      return Number(this.assignmentId || 0) !== Number(request.assigned_consultant_id || 0) || (
        request.service_type === 'report' && this.consultationType !== (request.consultation_type || 'integrated')
      )
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
    confirmAction,
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
    consultationTypeLabel,
    genderLabel,
    topicLabel,
    requestGoal,
    formatDate,
    pretty: prettyJson,
    errorText
  }
}
