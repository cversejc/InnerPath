import { getCurrentUser } from '../../users/service.js'
import {
  createServiceRequest,
  getMyServiceRequest,
  resubmitServiceRequest,
  updateServiceRequest
} from '../api.js'
import {
  buildCalendarRequestPayload,
  validateCalendarRequestForm
} from '../calendar-form.js'

export default {
  applyUserProfile(user) {
    this.form.name = user.name || this.form.name
    this.form.gender = user.gender || this.form.gender
    this.form.birth_year = user.birth_year || this.form.birth_year
    this.form.birth_month = user.birth_month || this.form.birth_month
    this.form.birth_day = user.birth_day || this.form.birth_day
    this.form.birth_hour = user.birth_hour ?? this.form.birth_hour
    this.form.birth_minute = user.birth_minute ?? this.form.birth_minute
    this.form.birth_place = user.birth_place || this.form.birth_place
    if (user.birth_hour !== null && user.birth_hour !== undefined) this.form.time_accuracy = 'approximate'
  },
  applyRequest(request) {
    const payload = request.request_payload || {}
    const profile = payload.profile || {}
    this.form = {
      ...this.form,
      ...profile,
      start_date: payload.start_date || this.form.start_date,
      calendar_goal: payload.calendar_goal || '',
      additional_info: payload.additional_info || ''
    }
  },
  selectTimeAccuracy(value) {
    this.form.time_accuracy = value
    if (value === 'unknown') {
      this.form.birth_hour = null
      this.form.birth_minute = null
    }
  },
  validate() {
    const errors = validateCalendarRequestForm(this.form)
    this.errors = errors
    return !Object.keys(errors).length
  },
  requestPayload() {
    return buildCalendarRequestPayload(this.form)
  },
  async submitRequest() {
    this.formMessage = ''
    if (this.submitting || !this.validate()) return
    this.submitting = true
    try {
      const payload = this.requestPayload()
      let result
      if (this.editing) {
        await updateServiceRequest(this.requestId, payload)
        result = await resubmitServiceRequest(this.requestId)
      } else {
        this.idempotencyKey = this.idempotencyKey
          || 'calendar-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10)
        result = await createServiceRequest({
          service_type: 'calendar',
          ...payload,
          idempotency_key: this.idempotencyKey
        })
      }
      await this.$router.push('/pages/requests/requests?submitted=' + result.id)
    } catch (error) {
      this.formMessage = this.errorText(error)
    } finally {
      this.submitting = false
    }
  },
  errorText(error) {
    return error.response?.data?.detail || '申请提交失败，请检查资料后重试'
  },
  async loadRequestForm() {
    this.requestId = this.$route.query.requestId ? Number(this.$route.query.requestId) : null
    try {
      const user = await getCurrentUser()
      this.applyUserProfile(user)
      if (this.requestId) {
        const request = await getMyServiceRequest(this.requestId)
        if (request.service_type !== 'calendar' || request.status !== 'needs_info') {
          this.requestId = null
          this.formMessage = '这份申请当前不需要补充资料。'
        } else {
          this.applyRequest(request)
        }
      }
    } catch (error) {
      this.formMessage = this.errorText(error)
    } finally {
      this.ready = true
    }
  }
}
