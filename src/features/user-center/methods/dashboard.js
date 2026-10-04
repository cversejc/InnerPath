import { getCurrentUser } from '../../users/service.js'
import { getUserReports } from '../../reports/api.js'
import { getMyServiceRequests } from '../../service-requests/api.js'
import { mapUserToProfile } from '../../users/profile.js'
import { formatUserCenterDate } from '../presentation.js'

export default {
  async loadDashboard() {
    this.loading = true
    try {
      const [user, reportResponse] = await Promise.all([
        getCurrentUser(),
        getUserReports()
      ])
      let requestResponse = { items: [] }
      try {
        requestResponse = await getMyServiceRequests()
      } catch (error) {
        // 申请分区不能阻断历史报告和账户设置的打开。
        this.message = this.message || '申请记录暂时无法同步，请稍后重试'
      }
      this.userName = user.name
      this.userType = user.role === 'admin' ? '管理员' : user.role === 'consultant' ? '咨询师' : '成长探索者'
      this.accountPhone = user.phone || ''
      this.settings = mapUserToProfile(user)
      this.optionalProfileExpanded = Number(user.profile_completion || 0) < 100
      this.reports = (reportResponse.items || []).map(report => ({
        id: report.id,
        title: report.title,
        date: formatUserCenterDate(report.created_at),
        energyType: report.energy_type || '综合型',
        coreTraits: report.core_traits || '—'
      }))
      this.requests = requestResponse.items || []
    } catch (error) {
      this.message = error.response?.data?.detail || '暂时无法打开你的个人空间，请稍后再试'
    } finally {
      this.loading = false
    }
  }
}
