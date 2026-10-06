<template>
  <section id="user-panel-requests" class="content-section" role="tabpanel" aria-labelledby="user-tab-requests" tabindex="0">
    <div class="requests-section-heading">
      <div>
        <h3 class="section-title">我的申请</h3>
        <p>报告由咨询师处理并交付；获得报告后，可基于报告自动生成并开放日历。</p>
      </div>
      <router-link class="btn-action" to="/pages/requests/requests">查看全部</router-link>
    </div>
    <div v-if="!requests.length" class="empty-state">
      <IconMark class="empty-icon" name="compass" />
      <p>还没有申请记录</p>
      <div class="request-quick-actions">
        <router-link class="btn-action" to="/pages/assessment/assessment">申请报告</router-link>
        <router-link class="btn-action secondary" to="/pages/assessment/assessment">先申请报告</router-link>
      </div>
    </div>
    <div v-else class="center-request-list">
      <article v-for="request in requests.slice(0, 5)" :key="`${request.workflow_type || request.service_type}:${request.id}`" class="center-request-card">
        <div>
          <span class="center-request-type">{{ request.workflow_type === 'calendar_generation' ? '日历生成' : request.service_type === 'calendar' ? '决策日历' : '人生说明书' }}</span>
          <strong>申请 #{{ request.id }}</strong>
          <small>{{ formatUserCenterDate(request.created_at) }}</small>
        </div>
        <span class="center-request-status">{{ requestStatusLabel(request.status, request.workflow_type) }}</span>
        <router-link v-if="request.status === 'needs_info'" class="center-request-action" :to="requestEditPath(request)">补充资料</router-link>
        <router-link v-else-if="request.status === 'delivered' && request.result_type === 'report'" class="center-request-action" :to="`/pages/report/detail?id=${request.result_id}`">查看报告</router-link>
        <router-link v-else-if="request.status === 'delivered' && request.result_type === 'calendar'" class="center-request-action" to="/pages/calendar/calendar">打开日历</router-link>
        <div v-if="isDeliveredReport(request) && feedbackReady" class="center-request-feedback">
          <ServiceFeedbackControl
            service-type="report"
            :source-id="request.id"
            :existing="feedbackByRequestId[request.id] || null"
            @submitted="saveRequestFeedback(request.id, $event)"
          />
        </div>
        <p v-else-if="isDeliveredReport(request) && feedbackLoadError" class="center-request-feedback-error" role="status">反馈状态暂时无法读取，请稍后刷新。</p>
      </article>
    </div>
  </section>
</template>

<script>
import { formatUserCenterDate, requestEditPath, requestStatusLabel } from '../presentation'
import ServiceFeedbackControl from '../../service-feedback/components/ServiceFeedbackControl.vue'
import { getMyServiceFeedback } from '../../service-feedback/api.js'

export default {
  name: 'RequestsPanel',
  components: { ServiceFeedbackControl },
  props: {
    requests: { type: Array, default: () => [] }
  },
  data() {
    return { feedbackByRequestId: {}, feedbackReady: false, feedbackLoadError: false }
  },
  async mounted() {
    try {
      const response = await getMyServiceFeedback()
      this.feedbackByRequestId = Object.fromEntries(
        (response.items || [])
          .filter(item => item.service_request_id)
          .map(item => [item.service_request_id, item])
      )
      this.feedbackReady = true
    } catch {
      this.feedbackReady = false
      this.feedbackLoadError = true
    }
  },
  methods: {
    formatUserCenterDate,
    requestEditPath,
    requestStatusLabel,
    isDeliveredReport(request) {
      return request.service_type === 'report' && request.status === 'delivered' && request.result_type === 'report'
    },
    saveRequestFeedback(requestId, feedback) {
      this.feedbackByRequestId = { ...this.feedbackByRequestId, [requestId]: feedback }
    }
  }
}
</script>

<style scoped src="../styles/requests.css"></style>
