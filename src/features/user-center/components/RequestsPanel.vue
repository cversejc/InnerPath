<template>
  <section id="user-panel-requests" class="content-section" role="tabpanel" aria-labelledby="user-tab-requests" tabindex="0">
    <div class="requests-section-heading">
      <div>
        <h3 class="section-title">我的申请</h3>
        <p>人生说明书由咨询师审阅；决策日历可基于已交付报告直接生成并交付</p>
      </div>
      <router-link class="btn-action" to="/pages/requests/requests">查看全部</router-link>
    </div>
    <div v-if="!requests.length" class="empty-state">
      <IconMark class="empty-icon" name="compass" />
      <p>还没有申请记录</p>
      <div class="request-quick-actions">
        <router-link class="btn-action" to="/pages/assessment/assessment">申请报告</router-link>
        <router-link class="btn-action secondary" to="/pages/user/user?tab=reports">查看已交付报告</router-link>
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
      </article>
    </div>
  </section>
</template>

<script>
import { formatUserCenterDate, requestEditPath, requestStatusLabel } from '../presentation'

export default {
  name: 'RequestsPanel',
  props: {
    requests: { type: Array, default: () => [] }
  },
  methods: {
    formatUserCenterDate,
    requestEditPath,
    requestStatusLabel
  }
}
</script>

<style scoped src="../styles/requests.css"></style>
