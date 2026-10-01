import { getAdminAuditLogs } from '../api'
import { getAdminDecisionLogs } from '../../calendar/api'

export default {
  async setLogSection(section) { this.logSection = section; if (section === 'audit') await this.loadAuditLogs(); else if (section === 'behavior') await this.loadDecisionLogs(); else await this.loadReportTasks() },
  async loadAuditLogs() { this.auditLoading = true; try { this.auditLogs = await getAdminAuditLogs({ ...this.cleanParams(this.logFilters), page: this.logPage, size: this.logPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.auditLoading = false } },
  resetLogFilters() { this.logFilters = { search: '', action: '', resource_type: '', actor_user_id: '', target_user_id: '', date_from: '', date_to: '' }; this.logPage = 1; this.loadAuditLogs() },
  async changeLogPage(offset) { const next = this.logPage + offset; if (next < 1 || next > this.pageCount(this.auditLogs.total, this.logPageSize)) return; this.logPage = next; await this.loadAuditLogs() },
  async loadDecisionLogs() { this.decisionLoading = true; try { this.decisionLogs = await getAdminDecisionLogs({ ...this.cleanParams(this.behaviorFilters), page: this.decisionPage, size: this.decisionPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.decisionLoading = false } },
  async searchDecisionLogs() { this.decisionPage = 1; await this.loadDecisionLogs() },
  async changeDecisionPage(offset) { const next = this.decisionPage + offset; if (next < 1 || next > this.pageCount(this.decisionLogs.total, this.decisionPageSize)) return; this.decisionPage = next; await this.loadDecisionLogs() },
  openLogDetail(log) { this.drawerTrigger = document.activeElement; this.logDetail = log; this.focusDrawer('logDrawer') },
  closeLogDetail() { this.logDetail = null; this.restoreDrawerFocus() }
}
