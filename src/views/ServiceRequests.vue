<template>
  <div class="requests-page">
    <BrandNav />

    <main class="requests-main">
      <header class="requests-hero">
        <div>
          <p class="section-kicker">MY REQUESTS / SERVICE FLOW</p>
          <h1>我的申请</h1>
          <p>申请提交后，会由咨询师接单、生成 AI 初稿并完成审校，最终结果只在交付后向你开放。</p>
        </div>
        <div class="hero-actions">
          <router-link class="secondary-button" to="/pages/assessment/assessment">申请人生说明书</router-link>
          <router-link class="primary-button" to="/pages/requests/new?type=calendar">申请决策日历</router-link>
        </div>
      </header>

      <p v-if="message" class="page-message" :class="{ error: messageType === 'error' }" role="status" aria-live="polite">{{ message }}</p>

      <section class="request-toolbar paper-card" aria-label="申请筛选">
        <div class="filter-copy">
          <span class="eyebrow">REQUEST LEDGER</span>
          <strong>申请记录</strong>
          <small>{{ filteredRequests.length }} 项记录</small>
        </div>
        <div class="request-filters" role="group" aria-label="按类型筛选">
          <button v-for="filter in filters" :key="filter.id" type="button" :class="{ active: activeFilter === filter.id }" :aria-pressed="activeFilter === filter.id" @click="activeFilter = filter.id">{{ filter.label }}</button>
        </div>
      </section>

      <section v-if="loading" class="request-loading" aria-label="正在加载申请">
        <i v-for="index in 3" :key="index"></i>
      </section>

      <section v-else-if="!filteredRequests.length" class="empty-request paper-card">
        <span class="empty-seal" aria-hidden="true">申</span>
        <div>
          <p class="eyebrow">A QUIET START</p>
          <h2>还没有申请记录</h2>
          <p>从一份人生说明书，或一段 30 天的决策日历开始。</p>
        </div>
        <div class="empty-actions">
          <router-link class="primary-button" to="/pages/assessment/assessment">申请报告</router-link>
          <router-link class="secondary-button" to="/pages/requests/new?type=calendar">申请日历</router-link>
        </div>
      </section>

      <section v-else class="request-list" aria-label="我的申请列表">
        <article v-for="item in filteredRequests" :key="item.id" class="request-card paper-card" :class="`status-${item.status}`">
          <div class="request-card-head">
            <div class="request-type-mark" :class="`type-${item.service_type}`" aria-hidden="true"><IconMark :name="item.service_type === 'report' ? 'reports' : 'calendar'" /></div>
            <div class="request-card-title">
              <div class="request-kicker"><span>{{ serviceTypeLabel(item.service_type) }}</span><span>申请 #{{ item.id }}</span></div>
              <h2>{{ item.service_type === 'report' ? '人生说明书' : '决策日历' }}</h2>
              <p>提交于 {{ formatDateTime(item.created_at) }}<span v-if="item.service_type === 'calendar' && payload(item).start_date"> · {{ payload(item).start_date }} 起 30 天</span></p>
            </div>
            <span class="status-badge request-status" :class="`request-status-${item.status}`">{{ statusLabel(item.status) }}</span>
          </div>

          <div class="request-card-body">
            <p v-if="item.service_type === 'report'" class="request-summary">关注议题：{{ topicLabel(payload(item).selected_topics) }}</p>
            <p v-else class="request-summary">关注目标：{{ payload(item).calendar_goal || '尚未填写具体目标' }}</p>
            <p v-if="payload(item).additional_info" class="request-note">补充说明：{{ payload(item).additional_info }}</p>
            <div v-if="item.status === 'needs_info'" class="needs-info-note" role="alert">
              <strong>请补充资料</strong>
              <p>{{ item.needs_info_reason || '咨询师希望进一步了解你的需求。' }}</p>
            </div>
            <div v-if="item.status === 'failed'" class="needs-info-note failed-note" role="alert">
              <strong>初步分析暂未完成</strong>
              <p>咨询师会在工作台中重试，当前申请仍可继续跟进。</p>
            </div>
          </div>

          <footer class="request-card-actions">
            <router-link v-if="item.status === 'delivered' && item.result_type === 'report'" class="primary-button compact-button" :to="`/pages/report/detail?id=${item.result_id}`">查看报告</router-link>
            <router-link v-else-if="item.status === 'delivered' && item.result_type === 'calendar'" class="primary-button compact-button" to="/pages/calendar/calendar">打开日历</router-link>
            <router-link v-if="item.status === 'needs_info'" class="secondary-button compact-button" :to="editPath(item)">补充资料</router-link>
            <button v-if="canWithdraw(item.status)" type="button" class="text-button danger-text" :disabled="withdrawnId === item.id" @click="withdraw(item)">{{ withdrawnId === item.id ? '撤回中…' : '撤回申请' }}</button>
            <span v-if="item.status === 'delivered'" class="delivered-stamp">已由咨询师交付</span>
          </footer>
        </article>
      </section>
    </main>

    <BrandFooter />
  </div>
</template>

<script>
import { getMyServiceRequests, withdrawServiceRequest } from '../utils/serviceRequestService'

const STATUS_LABELS = {
  submitted: '等待咨询师接单',
  accepted: '咨询师已接单',
  ai_processing: '正在准备分析',
  ai_ready: '等待咨询师审校',
  reviewing: '咨询师审校中',
  needs_info: '需要补充资料',
  failed: '分析暂时失败',
  delivered: '已完成',
  withdrawn: '已撤回',
  rejected: '暂未受理'
}

export default {
  name: 'ServiceRequests',
  data() {
    return {
      requests: [],
      loading: true,
      message: '',
      messageType: 'info',
      activeFilter: 'all',
      withdrawnId: null,
      filters: [
        { id: 'all', label: '全部' },
        { id: 'report', label: '报告' },
        { id: 'calendar', label: '日历' }
      ]
    }
  },
  computed: {
    filteredRequests() {
      if (this.activeFilter === 'all') return this.requests
      return this.requests.filter(item => item.service_type === this.activeFilter)
    }
  },
  async mounted() {
    await this.loadRequests()
    if (this.$route.query.submitted) {
      this.message = `申请 #${this.$route.query.submitted} 已提交，接下来等待咨询师接单。`
      this.messageType = 'info'
    }
  },
  methods: {
    async loadRequests() {
      this.loading = true
      try {
        const response = await getMyServiceRequests()
        this.requests = response.items || []
      } catch (error) {
        this.message = this.errorText(error)
        this.messageType = 'error'
      } finally {
        this.loading = false
      }
    },
    payload(item) {
      return item.request_payload || {}
    },
    serviceTypeLabel(type) {
      return type === 'calendar' ? '决策日历申请' : '报告申请'
    },
    statusLabel(status) {
      return STATUS_LABELS[status] || status
    },
    topicLabel(topics) {
      const labels = {
        career: '职业发展',
        relationship: '亲密关系',
        family: '家庭议题',
        self: '自我价值',
        growth: '个人成长',
        stress: '压力焦虑'
      }
      return (topics || []).map(topic => labels[topic] || topic).join('、') || '综合自我探索'
    },
    formatDateTime(value) {
      return value ? new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'
    },
    canWithdraw(status) {
      return status === 'submitted' || status === 'needs_info'
    },
    editPath(item) {
      return item.service_type === 'report'
        ? `/pages/assessment/assessment?requestId=${item.id}`
        : `/pages/requests/new?type=calendar&requestId=${item.id}`
    },
    async withdraw(item) {
      if (!this.canWithdraw(item.status) || this.withdrawnId) return
      if (!window.confirm('确定撤回这份申请吗？撤回后需要重新提交才能继续。')) return
      this.withdrawnId = item.id
      try {
        const updated = await withdrawServiceRequest(item.id)
        const index = this.requests.findIndex(request => request.id === item.id)
        if (index > -1) this.requests.splice(index, 1, updated)
        this.message = '申请已撤回'
        this.messageType = 'info'
      } catch (error) {
        this.message = this.errorText(error)
        this.messageType = 'error'
      } finally {
        this.withdrawnId = null
      }
    },
    errorText(error) {
      return error.response?.data?.detail || '申请记录加载失败，请稍后重试'
    }
  }
}
</script>

<style scoped>
.requests-page { min-height: 100dvh; background: var(--paper, #f8f1e6); }
.requests-main { width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 76px 0 92px; }
.requests-hero { display: flex; align-items: end; justify-content: space-between; gap: 28px; margin-bottom: 28px; }
.requests-hero h1 { margin: 8px 0; font-size: clamp(36px, 7vw, 66px); line-height: 1.05; }
.requests-hero p:not(.section-kicker) { max-width: 620px; margin: 0; color: var(--muted, #7d6653); line-height: 1.75; }
.hero-actions, .empty-actions, .request-card-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.hero-actions { flex: 0 0 auto; }
.page-message { margin: 0 0 16px; color: var(--jade-deep, #356b59); }
.page-message.error { color: var(--cinnabar-deep, #9e3f35); }
.request-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 14px 18px; }
.filter-copy { display: grid; gap: 3px; }
.filter-copy strong { color: var(--ink, #3b2d24); font-size: 19px; }
.filter-copy small { color: var(--muted, #7d6653); }
.request-filters { display: flex; flex-wrap: wrap; gap: 6px; }
.request-filters button { min-height: 44px; border: 1px solid transparent; border-radius: 999px; padding: 0 15px; background: transparent; color: var(--muted, #7d6653); font: inherit; font-weight: 800; cursor: pointer; }
.request-filters button.active { border-color: rgba(184, 92, 80, .3); background: rgba(184, 92, 80, .1); color: var(--cinnabar-deep, #9e3f35); }
.request-loading { display: grid; gap: 12px; margin-top: 18px; }
.request-loading i { display: block; height: 140px; border-radius: 18px; background: linear-gradient(90deg, rgba(255, 250, 240, .8), rgba(255, 239, 222, .9), rgba(255, 250, 240, .8)); background-size: 240% 100%; animation: request-shimmer 1.4s ease infinite; }
@keyframes request-shimmer { to { background-position: -240% 0; } }
.empty-request { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 20px; margin-top: 18px; padding: 36px; }
.empty-seal { display: grid; place-items: center; width: 64px; height: 64px; border: 1px solid rgba(184, 92, 80, .35); border-radius: 50%; color: var(--cinnabar-deep, #9e3f35); font-size: 24px; font-weight: 900; }
.empty-request h2 { margin: 4px 0 7px; color: var(--ink, #3b2d24); }
.empty-request p:not(.eyebrow) { margin: 0; color: var(--muted, #7d6653); line-height: 1.7; }
.request-list { display: grid; gap: 14px; margin-top: 18px; }
.request-card { padding: 22px; overflow: hidden; }
.request-card-head { display: flex; align-items: flex-start; gap: 14px; }
.request-type-mark { display: grid; place-items: center; flex: 0 0 auto; width: 48px; height: 48px; border-radius: 14px; background: rgba(184, 92, 80, .1); color: var(--cinnabar-deep, #9e3f35); }
.request-type-mark.type-calendar { background: rgba(93, 145, 126, .13); color: var(--jade-deep, #356b59); }
.request-type-mark :deep(svg) { width: 24px; height: 24px; }
.request-card-title { min-width: 0; flex: 1; }
.request-kicker { display: flex; flex-wrap: wrap; gap: 10px; color: var(--muted, #7d6653); font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.request-card-title h2 { margin: 5px 0 4px; color: var(--ink, #3b2d24); font-size: 23px; }
.request-card-title p { margin: 0; color: var(--muted, #7d6653); font-size: 14px; }
.request-status { flex: 0 0 auto; border: 1px solid rgba(184, 92, 80, .22); background: rgba(184, 92, 80, .08); color: var(--cinnabar-deep, #9e3f35); }
.request-status-request-status-delivered, .request-status-delivered { border-color: rgba(93, 145, 126, .3); background: rgba(93, 145, 126, .12); color: var(--jade-deep, #356b59); }
.request-status-request-status-needs_info, .request-status-needs_info { border-color: rgba(196, 151, 57, .35); background: rgba(196, 151, 57, .12); color: #8a621b; }
.request-status-request-status-withdrawn, .request-status-withdrawn, .request-status-request-status-rejected, .request-status-rejected { border-color: rgba(125, 102, 83, .2); background: rgba(125, 102, 83, .08); color: var(--muted, #7d6653); }
.request-card-body { margin: 18px 0 16px 62px; padding: 14px 16px; border-left: 2px solid rgba(184, 92, 80, .2); background: rgba(255, 250, 240, .46); }
.request-summary, .request-note { margin: 0; color: var(--ink-soft, #51463d); line-height: 1.7; }
.request-note { margin-top: 7px; color: var(--muted, #7d6653); font-size: 14px; }
.needs-info-note { margin-top: 12px; border-radius: 10px; padding: 11px 13px; background: rgba(196, 151, 57, .11); color: #78561c; }
.needs-info-note strong { font-size: 14px; }
.needs-info-note p { margin: 4px 0 0; line-height: 1.6; }
.failed-note { background: rgba(158, 63, 53, .08); color: var(--cinnabar-deep, #9e3f35); }
.request-card-actions { margin-left: 62px; }
.text-button { min-height: 44px; border: 0; padding: 0 4px; background: transparent; font: inherit; font-weight: 800; cursor: pointer; }
.danger-text { color: var(--cinnabar-deep, #9e3f35); }
.text-button:disabled { opacity: .55; cursor: wait; }
.delivered-stamp { margin-left: auto; color: var(--jade-deep, #356b59); font-size: 13px; }
@media (max-width: 720px) {
  .requests-main { width: calc(100% - 24px); padding: 30px 0 calc(96px + var(--safe-bottom, 0px)); }
  .requests-hero { display: grid; align-items: initial; gap: 18px; }
  .hero-actions { display: grid; grid-template-columns: 1fr 1fr; }
  .hero-actions > * { width: 100%; text-align: center; }
  .request-toolbar { display: grid; align-items: initial; gap: 12px; padding: 13px; }
  .request-filters { overflow-x: auto; flex-wrap: nowrap; }
  .empty-request { grid-template-columns: auto 1fr; padding: 24px 18px; }
  .empty-actions { grid-column: 1 / -1; }
  .empty-actions > * { flex: 1; text-align: center; }
  .request-card { padding: 16px 13px; }
  .request-card-head { gap: 10px; }
  .request-type-mark { width: 42px; height: 42px; border-radius: 12px; }
  .request-status { align-self: flex-start; max-width: 116px; white-space: normal; text-align: center; }
  .request-card-title h2 { font-size: 20px; }
  .request-card-body, .request-card-actions { margin-left: 0; }
  .request-card-body { margin-top: 14px; }
  .request-card-actions { align-items: stretch; }
  .request-card-actions > .primary-button, .request-card-actions > .secondary-button { flex: 1; text-align: center; }
  .delivered-stamp { width: 100%; margin-left: 0; }
}
</style>
