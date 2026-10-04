import { getCurrentUser } from '../../users/service.js'
import { getUserReports } from '../../reports/api.js'
import { getMyServiceRequests } from '../../service-requests/api.js'
import { mapUserToProfile } from '../../users/profile.js'
import { getReportCoverTheme } from '../../reports/day-pillar-visual.js'
import { REPORT_COVER_MOCKS } from '../../reports/report-cover-mock.js'

const allowDemoReports = import.meta.env.DEV && import.meta.env.VITE_DEMO_REPORTS !== 'false'

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
      const apiReports = Array.isArray(reportResponse.items) ? reportResponse.items : []
      const reportsToDisplay = apiReports.length > 0
        ? apiReports
        : allowDemoReports
          ? REPORT_COVER_MOCKS
          : []

      this.reports = reportsToDisplay.map((report, index) => {
        const fallback = REPORT_COVER_MOCKS[index % REPORT_COVER_MOCKS.length]
        const dayPillar = String(report.day_pillar || report.dayPillar || '').trim() || fallback.dayPillar
        const pillarMock = REPORT_COVER_MOCKS.find(
          mock => getReportCoverTheme(mock.dayPillar) === getReportCoverTheme(dayPillar)
        ) || fallback
        const description = [report.cover_description, report.coverDescription, report.description]
          .find(value => typeof value === 'string' && value.trim())
          ?.trim() || pillarMock.description

        return {
          id: report.id,
          title: report.title || '辰鉴·人生说明书',
          description,
          dayPillar,
          coverTheme: getReportCoverTheme(dayPillar),
          isMock: Boolean(report.isMock)
        }
      })
      this.requests = requestResponse.items || []
    } catch (error) {
      this.message = error.response?.data?.detail || '暂时无法打开你的个人空间，请稍后再试'
    } finally {
      this.loading = false
    }
  }
}
