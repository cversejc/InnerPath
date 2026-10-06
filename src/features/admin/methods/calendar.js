import { getAllAdminUsers } from '../api.js'
import {
  archiveAdminCalendar,
  createAdminCalendar,
  createAdminCalendarDraft,
  getAdminCalendars,
  importAdminCalendar,
  publishAdminCalendar,
  updateAdminCalendar
} from '../../calendar/api.js'

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
  async loadCalendarUsers() {
      this.calendarUsersLoading = true
      try { const response = await getAllAdminUsers({ search: this.calendarUserSearch || undefined, size: 100 }); this.calendarUsers = response.items || [] } catch (error) { this.message = this.errorText(error) } finally { this.calendarUsersLoading = false }
    },
  updateCalendarImportJson(value) { this.calendarImportJson = value },
  updateCalendarUserSearch(value) { this.calendarUserSearch = value },
  async loadCalendarRequests() {
      this.calendarRequestsLoading = true
      try {
        const response = await getAdminCalendarRequests({ status: this.calendarRequestStatusFilter || undefined })
        this.calendarRequests = response.items || []
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.calendarRequestsLoading = false
      }
    },
  async setCalendarRequestStatusFilter(status) {
      this.calendarRequestStatusFilter = status
      await this.loadCalendarRequests()
    },
  async openCalendarForUser(user) { this.closeUserDetail({ restoreFocus: false }); this.activeTab = 'calendar'; this.selectedCalendarUser = user; this.calendarForm.visible = false; await this.loadCalendarUsers(); await this.loadCalendars(); this.syncAutoRefresh() },
  async selectCalendarUser(user) { this.selectedCalendarUser = user; this.cancelCalendarEdit(); await this.loadCalendars() },
  async loadCalendars() {
      if (!this.selectedCalendarUser) return
      this.calendarLoading = true
      try { this.calendars = (await getAdminCalendars(this.selectedCalendarUser.id)).items || [] } catch (error) { this.message = this.errorText(error) } finally { this.calendarLoading = false }
    },
  startNewCalendar() { this.calendarForm = { visible: true, id: null, title: '', note: '', start_date: '', end_date: '', status: 'draft', version_number: 1, entries: [] } },
  async prepareCalendarEdit(calendar) {
      try {
        let target = calendar
        if (calendar.status !== 'draft') { target = await createAdminCalendarDraft(calendar.id); this.calendars = [target, ...this.calendars.filter(item => item.id !== target.id)]; this.message = `已创建 v${target.version_number} 草稿` }
        this.editCalendar(target)
      } catch (error) { this.message = this.errorText(error) }
    },
  editCalendar(calendar) {
      this.calendarForm = { visible: true, id: calendar.id, title: calendar.title, note: '', start_date: calendar.start_date || '', end_date: calendar.end_date || '', status: calendar.status, version_number: calendar.version_number || 1, entries: (calendar.entries || []).map(entry => ({ ...createEntry(entry.entry_date), ...entry, _key: `entry-${entry.id || Date.now()}-${Math.random()}`, suitableText: (entry.suitable || []).join('，'), unsuitableText: (entry.unsuitable || []).join('，') })) }
    },
  cancelCalendarEdit() { this.calendarForm = { visible: false, id: null, title: '', note: '', start_date: '', end_date: '', status: '', version_number: 1, entries: [] } },
  addCalendarEntry() { const last = this.calendarForm.entries[this.calendarForm.entries.length - 1]?.entry_date; let next = this.calendarForm.start_date || todayKey(); if (last) { const date = new Date(`${last}T00:00:00`); date.setDate(date.getDate() + 1); next = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}` } this.calendarForm.entries.push(createEntry(next)) },
  removeCalendarEntry(index) { this.calendarForm.entries.splice(index, 1) },
  splitEntryText(value) { return (value || '').split(/[,，、\n]/).map(item => item.trim()).filter(Boolean) },
  validateCalendarEntries(entries, startDate, endDate) {
      if (startDate && endDate && startDate > endDate) throw new Error('日历开始日期不能晚于结束日期')
      if (entries.some(entry => !entry.entry_date)) throw new Error('每个日历条目都需要填写日期')
      const dates = entries.map(entry => entry.entry_date)
      if (new Set(dates).size !== dates.length) throw new Error('日历条目日期不能重复')
      if (startDate && dates.some(entryDate => entryDate < startDate)) throw new Error('存在早于日历开始日期的条目')
      if (endDate && dates.some(entryDate => entryDate > endDate)) throw new Error('存在晚于日历结束日期的条目')
    },
  async saveCalendar() {
      if (!this.selectedCalendarUser) return
      const entries = this.calendarForm.entries.map(({ _key, id, suitableText, unsuitableText, ...entry }) => ({ ...entry, suitable: this.splitEntryText(suitableText), unsuitable: this.splitEntryText(unsuitableText) }))
      const dates = entries.map(entry => entry.entry_date).filter(Boolean).sort()
      const payload = { title: this.calendarForm.title, start_date: this.calendarForm.start_date || dates[0] || null, end_date: this.calendarForm.end_date || dates[dates.length - 1] || null, entries }
      try {
        if (!payload.title.trim()) throw new Error('请填写日历标题')
        this.validateCalendarEntries(entries, payload.start_date, payload.end_date)
      } catch (error) {
        this.message = error.message
        return
      }
      this.calendarSaving = true
      try { if (this.calendarForm.id) await updateAdminCalendar(this.calendarForm.id, payload); else await createAdminCalendar(this.selectedCalendarUser.id, payload); this.message = '日历草稿已保存'; this.cancelCalendarEdit(); await this.loadCalendars() } catch (error) { this.message = this.errorText(error) } finally { this.calendarSaving = false }
    },
  async publishCalendar(calendar) {
      const confirmed = await this.confirmAction({
        title: '确认发布日历',
        message: `确认发布“${calendar.title}” v${calendar.version_number}？发布后用户端将看到这版内容。`,
        confirmButtonText: '确认发布'
      })
      if (!confirmed) return
      try {
        await publishAdminCalendar(calendar.id)
        this.message = '日历已发布'
        await this.loadCalendars()
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
  async archiveCalendar(calendar) {
      const confirmed = await this.confirmAction({
        title: '确认归档日历',
        message: `确认归档“${calendar.title}” v${calendar.version_number}？`,
        confirmButtonText: '确认归档'
      })
      if (!confirmed) return
      try {
        await archiveAdminCalendar(calendar.id)
        this.message = '日历已归档'
        await this.loadCalendars()
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
  toggleImportPanel() { this.showCalendarImport = !this.showCalendarImport },
  async importCalendarJson() {
      try { const parsed = JSON.parse(this.calendarImportJson); const entries = Array.isArray(parsed) ? parsed : parsed.entries; if (!this.selectedCalendarUser) throw new Error('请先选择用户'); if (!Array.isArray(entries) || !entries.length) throw new Error('导入内容中没有有效条目'); const startDate = Array.isArray(parsed) ? null : (parsed.start_date || null); const endDate = Array.isArray(parsed) ? null : (parsed.end_date || null); this.validateCalendarEntries(entries, startDate, endDate); await importAdminCalendar({ user_id: this.selectedCalendarUser.id, title: Array.isArray(parsed) ? `${this.selectedCalendarUser.name} 的导入日历` : (parsed.title || `${this.selectedCalendarUser.name} 的导入日历`), start_date: startDate, end_date: endDate, entries }); this.calendarImportJson = ''; this.showCalendarImport = false; this.message = 'JSON 日历已导入为草稿'; await this.loadCalendars() } catch (error) { this.message = error instanceof SyntaxError ? 'JSON 格式不正确' : (error.message || this.errorText(error)) }
    },
  exportCalendarJson(calendar) { const blob = new Blob([JSON.stringify({ title: calendar.title, start_date: calendar.start_date, end_date: calendar.end_date, entries: calendar.entries || [] }, null, 2)], { type: 'application/json;charset=utf-8' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `calendar-${calendar.user_id}-v${calendar.version_number}.json`; anchor.click(); URL.revokeObjectURL(url) }
}
