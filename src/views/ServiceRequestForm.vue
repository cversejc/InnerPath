<template>
  <div class="request-form-page">
    <BrandNav />
    <main class="request-form-main">
      <header class="form-hero">
        <p class="section-kicker">TE / DECISION CALENDAR REQUEST</p>
        <h1>申请一段属于你的决策日历</h1>
        <p>选择起始日期，告诉咨询师你希望照看的议题。日历不要求先完成报告，提交后会经过 AI 初步分析与人工审校。</p>
      </header>

      <form v-if="ready" class="request-form paper-card" novalidate @submit.prevent="submitRequest">
        <section class="form-section" aria-labelledby="profile-title">
          <div class="section-heading">
            <p class="section-kicker">01 / PROFILE SNAPSHOT</p>
            <h2 id="profile-title">确认出生资料</h2>
            <p>这份资料会随本次申请保存为快照；接单后申请资料将锁定。</p>
          </div>

          <div class="form-grid two">
            <label class="field">
              <span>姓名 <b>*</b></span>
              <input v-model.trim="form.name" type="text" autocomplete="name" maxlength="50" required>
              <small v-if="errors.name" class="field-error">{{ errors.name }}</small>
            </label>
            <fieldset class="field choice-fieldset">
              <legend>性别 <b>*</b></legend>
              <div class="choice-row">
                <button type="button" :class="{ selected: form.gender === 'male' }" :aria-pressed="form.gender === 'male'" @click="form.gender = 'male'">男</button>
                <button type="button" :class="{ selected: form.gender === 'female' }" :aria-pressed="form.gender === 'female'" @click="form.gender = 'female'">女</button>
              </div>
              <small v-if="errors.gender" class="field-error">{{ errors.gender }}</small>
            </fieldset>
          </div>

          <div class="form-grid three">
            <label class="field"><span>出生年 <b>*</b></span><input v-model.number="form.birth_year" type="number" min="1900" max="2026" inputmode="numeric" required><small v-if="errors.birth" class="field-error">{{ errors.birth }}</small></label>
            <label class="field"><span>出生月 <b>*</b></span><input v-model.number="form.birth_month" type="number" min="1" max="12" inputmode="numeric" required></label>
            <label class="field"><span>出生日 <b>*</b></span><input v-model.number="form.birth_day" type="number" min="1" max="31" inputmode="numeric" required></label>
          </div>

          <div class="form-grid two">
            <fieldset class="field choice-fieldset">
              <legend>历法类型 <b>*</b></legend>
              <div class="choice-row"><button type="button" :class="{ selected: form.calendar_type === 'solar' }" :aria-pressed="form.calendar_type === 'solar'" @click="form.calendar_type = 'solar'">公历</button><button type="button" :class="{ selected: form.calendar_type === 'lunar' }" :aria-pressed="form.calendar_type === 'lunar'" @click="form.calendar_type = 'lunar'">农历</button></div>
            </fieldset>
            <label class="field"><span>出生地 <em>选填</em></span><input v-model.trim="form.birth_place" type="text" maxlength="100" placeholder="如：北京、上海"></label>
          </div>

          <fieldset class="field choice-fieldset">
            <legend>出生时间 <em>选填</em></legend>
            <div class="choice-row choice-row-wide"><button v-for="item in timeOptions" :key="item.value" type="button" :class="{ selected: form.time_accuracy === item.value }" :aria-pressed="form.time_accuracy === item.value" @click="selectTimeAccuracy(item.value)">{{ item.label }}</button></div>
            <div v-if="form.time_accuracy !== 'unknown'" class="time-row"><input v-model.number="form.birth_hour" type="number" min="0" max="23" placeholder="08" aria-label="出生时"><span>:</span><input v-model.number="form.birth_minute" type="number" min="0" max="59" placeholder="30" aria-label="出生分"></div>
          </fieldset>
        </section>

        <section class="form-section" aria-labelledby="calendar-title">
          <div class="section-heading"><p class="section-kicker">02 / REQUEST FOCUS</p><h2 id="calendar-title">告诉我们你想照看的节奏</h2><p>日历固定覆盖起始日期后的 30 天，咨询师会根据你的目标调整每日表达。</p></div>
          <div class="form-grid two">
            <label class="field"><span>起始日期 <b>*</b></span><input v-model="form.start_date" type="date" required><small class="field-hint">将生成 {{ dateRangeLabel }}</small><small v-if="errors.start_date" class="field-error">{{ errors.start_date }}</small></label>
            <label class="field"><span>关注目标 <b>*</b></span><input v-model.trim="form.calendar_goal" type="text" maxlength="500" placeholder="例如：安排转型、稳定作息、做重要决定" required><small v-if="errors.calendar_goal" class="field-error">{{ errors.calendar_goal }}</small></label>
          </div>
          <label class="field"><span>补充说明 <em>选填</em></span><textarea v-model.trim="form.additional_info" rows="5" maxlength="4000" placeholder="可以写下近期处境、希望被提醒的事项，或你对日历语气的期待。"></textarea><small class="field-hint">{{ form.additional_info.length }}/4000</small></label>
        </section>

        <div class="form-footer">
          <p class="privacy-note"><span aria-hidden="true">◆</span> 提交后先进入咨询师工作台，不会直接生成或展示给其他用户。</p>
          <div class="form-actions"><router-link class="secondary-button" to="/pages/requests/requests">返回我的申请</router-link><button class="primary-button" type="submit" :disabled="submitting" :aria-busy="submitting">{{ submitting ? '提交中…' : editing ? '更新并重新提交' : '提交日历申请' }}</button></div>
          <p v-if="formMessage" class="form-error" role="alert" aria-live="assertive">{{ formMessage }}</p>
        </div>
      </form>

      <section v-else class="loading-card paper-card" role="status" aria-live="polite">正在准备申请表…</section>
    </main>
    <BrandFooter />
  </div>
</template>

<script>
import { getCurrentUser } from '../utils/authService'
import {
  createServiceRequest,
  getMyServiceRequest,
  resubmitServiceRequest,
  updateServiceRequest
} from '../features/service-requests/api'

function localDateKey(date = new Date()) {
  const pad = value => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function addDays(dateKey, days) {
  const date = new Date(`${dateKey}T12:00:00`)
  date.setDate(date.getDate() + days)
  return localDateKey(date)
}

export default {
  name: 'ServiceRequestForm',
  data() {
    return {
      ready: false,
      requestId: null,
      idempotencyKey: null,
      submitting: false,
      formMessage: '',
      errors: {},
      timeOptions: [
        { value: 'unknown', label: '不知道' },
        { value: 'approximate', label: '大概时间' },
        { value: 'exact', label: '精确时间' }
      ],
      form: {
        name: '',
        gender: '',
        birth_year: null,
        birth_month: null,
        birth_day: null,
        birth_hour: null,
        birth_minute: null,
        birth_place: '',
        calendar_type: 'solar',
        time_accuracy: 'unknown',
        start_date: localDateKey(),
        calendar_goal: '',
        additional_info: ''
      }
    }
  },
  computed: {
    editing() {
      return Boolean(this.requestId)
    },
    dateRangeLabel() {
      return this.form.start_date ? `${this.form.start_date} 至 ${addDays(this.form.start_date, 29)}` : '起始日期待定'
    }
  },
  async mounted() {
    if (this.$route.query.type === 'report') {
      await this.$router.replace(this.$route.query.requestId
        ? `/pages/assessment/assessment?requestId=${this.$route.query.requestId}`
        : '/pages/assessment/assessment')
      return
    }
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
      this.ready = true
    } catch (error) {
      this.formMessage = this.errorText(error)
      this.ready = true
    }
  },
  methods: {
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
      const errors = {}
      if (!this.form.name) errors.name = '请填写姓名'
      if (!this.form.gender) errors.gender = '请选择性别'
      const year = Number(this.form.birth_year)
      const month = Number(this.form.birth_month)
      const day = Number(this.form.birth_day)
      if (!year || !month || !day) {
        errors.birth = '请填写完整出生日期'
      } else if (year < 1900 || year > 2026 || month < 1 || month > 12 || day < 1 || day > 31) {
        errors.birth = '出生日期格式不正确'
      } else if (this.form.calendar_type === 'solar') {
        const value = new Date(year, month - 1, day)
        if (value.getFullYear() !== year || value.getMonth() !== month - 1 || value.getDate() !== day) errors.birth = '出生日期不存在'
      } else if (day > 30) {
        errors.birth = '农历日期不能超过 30 日'
      }
      if (!this.form.start_date) errors.start_date = '请选择起始日期'
      if (!this.form.calendar_goal) errors.calendar_goal = '请填写本次关注目标'
      this.errors = errors
      return !Object.keys(errors).length
    },
    requestPayload() {
      return {
        profile: {
          name: this.form.name,
          gender: this.form.gender,
          birth_year: Number(this.form.birth_year),
          birth_month: Number(this.form.birth_month),
          birth_day: Number(this.form.birth_day),
          birth_hour: this.form.time_accuracy === 'unknown' ? null : Number(this.form.birth_hour),
          birth_minute: this.form.time_accuracy === 'unknown' ? null : Number(this.form.birth_minute || 0),
          birth_place: this.form.birth_place || null,
          calendar_type: this.form.calendar_type,
          time_accuracy: this.form.time_accuracy
        },
        selected_topics: [],
        calendar_goal: this.form.calendar_goal,
        start_date: this.form.start_date,
        additional_info: this.form.additional_info || null
      }
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
          this.idempotencyKey = this.idempotencyKey || `calendar-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
          result = await createServiceRequest({
            service_type: 'calendar',
            ...payload,
            idempotency_key: this.idempotencyKey
          })
        }
        await this.$router.push(`/pages/requests/requests?submitted=${result.id}`)
      } catch (error) {
        this.formMessage = this.errorText(error)
      } finally {
        this.submitting = false
      }
    },
    errorText(error) {
      return error.response?.data?.detail || '申请提交失败，请检查资料后重试'
    }
  }
}
</script>

<style scoped>
.request-form-page { min-height: 100dvh; background: var(--paper, #f8f1e6); }
.request-form-main { width: min(860px, calc(100% - 32px)); margin: 0 auto; padding: 72px 0 92px; }
.form-hero { max-width: 720px; margin-bottom: 28px; }
.form-hero h1 { margin: 8px 0 14px; font-size: clamp(36px, 7vw, 66px); line-height: 1.08; }
.form-hero p:not(.section-kicker) { margin: 0; color: var(--muted, #7d6653); line-height: 1.8; }
.request-form { padding: clamp(20px, 5vw, 42px); }
.form-section + .form-section { margin-top: 40px; padding-top: 34px; border-top: 1px solid rgba(80, 54, 32, .12); }
.section-heading { margin-bottom: 24px; }
.section-heading h2 { margin: 6px 0; color: var(--ink, #3b2d24); font-size: clamp(24px, 4vw, 34px); }
.section-heading p:not(.section-kicker) { margin: 0; color: var(--muted, #7d6653); line-height: 1.7; }
.form-grid { display: grid; gap: 18px; margin-bottom: 18px; }
.form-grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.form-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.field { display: grid; align-content: start; gap: 8px; min-width: 0; color: var(--ink-soft, #51463d); font-weight: 800; }
.field > span, .choice-fieldset > legend { color: var(--ink, #3b2d24); font-weight: 800; }
.field b, .choice-fieldset b { color: var(--cinnabar-deep, #9e3f35); }
.field em, .field-hint { color: var(--muted, #7d6653); font-size: 12px; font-style: normal; font-weight: 500; }
.field input, .field textarea { width: 100%; min-height: 48px; border: 1px solid rgba(80, 54, 32, .17); border-radius: 10px; background: rgba(255, 250, 240, .8); padding: 11px 12px; color: var(--ink, #3b2d24); font: inherit; font-weight: 500; }
.field textarea { min-height: 132px; resize: vertical; line-height: 1.7; }
.field input:focus, .field textarea:focus, .choice-row button:focus-visible { outline: 3px solid rgba(184, 92, 80, .18); outline-offset: 2px; border-color: var(--cinnabar, #b85c50); }
.choice-fieldset { min-width: 0; border: 0; padding: 0; }
.choice-fieldset > legend { width: 100%; padding: 0; }
.choice-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.choice-row-wide { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.choice-row button { min-height: 48px; border: 1px solid rgba(80, 54, 32, .16); border-radius: 10px; background: rgba(255, 250, 240, .75); color: var(--ink-soft, #51463d); font: inherit; font-weight: 800; cursor: pointer; }
.choice-row button.selected { border-color: rgba(184, 92, 80, .5); background: rgba(255, 239, 222, .9); color: var(--cinnabar-deep, #9e3f35); }
.time-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; max-width: 220px; }
.time-row input { text-align: center; }
.field-error { color: var(--cinnabar-deep, #9e3f35); font-size: 13px; font-weight: 700; line-height: 1.4; }
.form-footer { margin-top: 38px; padding-top: 22px; border-top: 1px solid rgba(80, 54, 32, .12); }
.privacy-note { margin: 0 0 16px; color: var(--muted, #7d6653); font-size: 13px; line-height: 1.6; }
.privacy-note span { color: var(--gold-deep, #8a621b); margin-right: 6px; }
.form-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 10px; }
.form-error { margin: 14px 0 0; color: var(--cinnabar-deep, #9e3f35); line-height: 1.6; }
.loading-card { padding: 38px; color: var(--muted, #7d6653); text-align: center; }
@media (max-width: 680px) {
  .request-form-main { width: calc(100% - 24px); padding: 30px 0 calc(96px + var(--safe-bottom, 0px)); }
  .request-form { padding: 20px 14px; border-radius: 16px; }
  .form-grid.two, .form-grid.three { grid-template-columns: 1fr; gap: 14px; }
  .choice-row-wide { grid-template-columns: 1fr; }
  .form-section + .form-section { margin-top: 30px; padding-top: 26px; }
  .form-actions { display: grid; grid-template-columns: 1fr 1fr; }
  .form-actions > * { width: 100%; text-align: center; }
}
</style>
