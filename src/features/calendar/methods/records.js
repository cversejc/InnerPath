import { authState } from '../../../stores/auth.js'
import { createDecisionLog, deleteDecisionLog, getMyDecisionLogs } from '../api.js'

const DECISION_LOG_STORAGE_KEY = 'innerseek:decision-logs'

export function createRecordDraft() {
  return {
    kind: 'action',
    status: 'done',
    content: '',
    note: ''
  }
}

export default {
  getRecordStorageKey() {
      const userKey = authState.user?.id || 'guest'
      return `${DECISION_LOG_STORAGE_KEY}:${userKey}`
    },
  normalizeDecisionLog(log) {
      return {
        id: log.id ?? log.localId ?? `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        date: log.log_date || log.date,
        kind: log.kind || log.type || 'action',
        status: log.status || 'done',
        content: log.content || '',
        note: log.note || '',
        createdAt: log.created_at || log.createdAt || new Date().toISOString()
      }
    },
  readLocalDecisionLogs() {
      try {
        const stored = window.localStorage.getItem(this.getRecordStorageKey())
        const parsed = stored ? JSON.parse(stored) : []
        return Array.isArray(parsed) ? parsed.map(record => this.normalizeDecisionLog(record)).filter(record => record.date && record.content) : []
      } catch (error) {
        return []
      }
    },
  persistLocalDecisionLogs(records = this.decisionLogs) {
      try {
        window.localStorage.setItem(this.getRecordStorageKey(), JSON.stringify(records))
      } catch (error) {
        // Local storage may be unavailable in private browsing; the page can still keep the in-memory record.
      }
    },
  async loadDecisionLogs() {
      const localRecords = this.readLocalDecisionLogs()
      try {
        const response = await getMyDecisionLogs({
          start_date: this.days[0]?.date,
          end_date: this.days[this.days.length - 1]?.date
        })
        this.decisionLogs = (response.items || []).map(record => this.normalizeDecisionLog(record)).filter(record => record.date && record.content)
        this.recordSource = 'api'
      } catch (error) {
        this.decisionLogs = localRecords
        this.recordSource = 'local'
      }
    },
  async persistDecisionLog(payload) {
      const localRecord = this.normalizeDecisionLog({
        ...payload,
        date: this.selectedDate,
        localId: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      })

      if (this.recordSource === 'api') {
        try {
          const response = await createDecisionLog({
            log_date: this.selectedDate,
            kind: payload.kind,
            status: payload.status,
            content: payload.content,
            note: payload.note || null
          })
          this.decisionLogs = [...this.decisionLogs, this.normalizeDecisionLog(response)]
          return
        } catch (error) {
          this.recordSource = 'local'
        }
      }

      this.decisionLogs = [...this.decisionLogs, localRecord]
      this.persistLocalDecisionLogs()
    },
  async loadRecordAndGiveFeedback(payload, message) {
      this.savingRecord = true
      this.recordError = ''
      try {
        await this.persistDecisionLog(payload)
        this.recordFeedback = message
      } catch (error) {
        this.recordError = '记录没有保存成功，请稍后再试。'
      } finally {
        this.savingRecord = false
      }
    },
  openRecordForm() {
      this.recordError = ''
      this.recordFeedback = ''
      this.showRecordForm = true
    },
  closeRecordForm() {
      this.showRecordForm = false
      this.recordError = ''
      this.recordDraft = createRecordDraft()
    },
  async saveDecisionLog() {
      const content = this.recordDraft.content.trim()
      if (!content) {
        this.recordError = '先写下今天实际发生的事。'
        return
      }

      await this.loadRecordAndGiveFeedback({
        kind: this.recordDraft.kind,
        status: this.recordDraft.status,
        content,
        note: this.recordDraft.note.trim()
      }, '已把这件事留在今天。')

      if (!this.recordError) {
        this.recordDraft = createRecordDraft()
        this.showRecordForm = false
      }
    },
  isQuickRecordSaved(item) {
      return this.selectedRecords.some(record => record.kind === 'action' && record.content === item && record.status !== 'skipped')
    },
  async quickRecord(item) {
      if (this.isQuickRecordSaved(item)) return
      await this.loadRecordAndGiveFeedback({ kind: 'action', status: 'done', content: item, note: '' }, '已把这条建议记为今天做过的事。')
    },
  async removeDecisionLog(record) {
      const confirmed = await this.confirmAction({
        title: '删除行动记录',
        message: '确定删除这条记录吗？删除后不可恢复。',
        confirmButtonText: '删除记录'
      })
      if (!confirmed) return
      this.recordError = ''
      try {
        if (typeof record.id === 'number') {
          await deleteDecisionLog(record.id)
        }
        this.decisionLogs = this.decisionLogs.filter(item => item.id !== record.id)
        if (this.recordSource === 'local' || typeof record.id !== 'number') this.persistLocalDecisionLogs()
        this.recordFeedback = '记录已移除。'
      } catch (error) {
        this.recordError = '删除没有成功，请稍后再试。'
      }
    }
}
