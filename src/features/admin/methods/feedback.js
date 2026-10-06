import {
  getAdminServiceFeedback,
  updateAdminServiceFeedback
} from '../../service-feedback/api.js'
import { getAdminReportQualityIssues } from '../../reports/api.js'

export default {
  async loadServiceFeedback() {
    this.feedbackLoading = true
    try {
      const result = await getAdminServiceFeedback({
        ...this.cleanParams(this.feedbackFilters),
        page: this.feedbackPage,
        size: this.feedbackPageSize
      })
      this.serviceFeedback = {
        ...result,
        items: (result.items || []).map(item => ({ ...item }))
      }
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.feedbackLoading = false
    }
  },
  async searchFeedback() {
    this.feedbackPage = 1
    await this.loadServiceFeedback()
  },
  async changeFeedbackPage(offset) {
    const next = this.feedbackPage + offset
    if (next < 1 || next > this.pageCount(this.serviceFeedback.total, this.feedbackPageSize)) return
    this.feedbackPage = next
    await this.loadServiceFeedback()
  },
  async setFeedbackView(view) {
    if (this.feedbackView === view) return
    this.feedbackView = view
    if (view === 'quality') {
      this.qualityPage = 1
      await this.loadQualityIssues()
    } else {
      await this.loadServiceFeedback()
    }
  },
  async loadQualityIssues() {
    this.qualityLoading = true
    try {
      const result = await getAdminReportQualityIssues({
        ...this.cleanParams(this.qualityFilters),
        page: this.qualityPage,
        size: this.qualityPageSize
      })
      this.qualityIssues = result
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.qualityLoading = false
    }
  },
  async searchQualityIssues() {
    this.qualityPage = 1
    await this.loadQualityIssues()
  },
  async changeQualityPage(offset) {
    const next = this.qualityPage + offset
    if (next < 1 || next > this.pageCount(this.qualityIssues.total, this.qualityPageSize)) return
    this.qualityPage = next
    await this.loadQualityIssues()
  },
  async saveFeedback(change) {
    if (this.feedbackSavingId !== null) return
    if (change.status === 'RESOLVED' && !(change.resolution || '').trim()) {
      this.message = '结案前请填写处理说明。'
      return
    }
    this.feedbackSavingId = change.id
    try {
      await updateAdminServiceFeedback(change.id, {
        status: change.status,
        assigned_to: change.assigned_to ? Number(change.assigned_to) : null,
        resolution: change.resolution || null
      })
      await this.loadServiceFeedback()
      this.message = `反馈 #${change.id} 已更新。`
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.feedbackSavingId = null
    }
  }
}
