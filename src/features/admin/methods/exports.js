import { downloadAdminExport } from '../api'

export default {
  async exportResource(resource) { try { let params = {}; if (resource === 'users') params = this.cleanParams(this.userFilters); if (resource === 'reports') params = this.cleanParams(this.reportFilters); if (resource === 'audit-logs') params = this.cleanParams(this.logFilters); if (resource === 'decision-logs') params = this.cleanParams(this.behaviorFilters); await downloadAdminExport(resource, params); this.message = '导出已开始' } catch (error) { this.message = this.errorText(error) } }
}
