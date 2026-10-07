<script setup>
import { computed } from 'vue'
import { Button as VanButton } from 'vant'
import { formatDateTime } from '../../../utils/dateTime.js'

const props = defineProps({ request: { type: Object, required: true } })
defineEmits(['view-analysis'])
const reportId = computed(() => Number(props.request.result_id))
const hasReport = computed(() => props.request.result_type === 'report'
  && Number.isSafeInteger(reportId.value) && reportId.value > 0)
</script>

<template>
  <section v-if="request.service_type === 'report' && request.status === 'delivered'" class="delivered-report-summary" aria-label="已交付最终报告">
    <div>
      <p class="section-kicker">交付成果</p>
      <h2>最终报告已交付</h2>
      <p>这里打开的是用户收到的最终正文。分析依据与审核记录仍保留在工作台中。</p>
      <small v-if="request.delivered_at">交付时间：{{ formatDateTime(request.delivered_at) }}</small>
    </div>
    <div class="delivery-links">
      <router-link v-if="hasReport" class="primary-button" :to="{ path: '/pages/report/detail', query: { id: String(reportId), request_id: String(request.id) } }">查看最终报告</router-link>
      <p v-else role="status">交付结果暂未关联报告，请联系管理员核对。</p>
      <VanButton v-if="request.report_case_id" type="default" plain native-type="button" @click="$emit('view-analysis')">查看分析过程</VanButton>
    </div>
  </section>
</template>

<style scoped>
.delivered-report-summary { display: flex; align-items: center; justify-content: space-between; gap: var(--space-5); padding: var(--space-5); margin-bottom: var(--space-5); background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-card); }
.delivered-report-summary h2 { margin: var(--space-2) 0; font-family: var(--font-display); font-size: var(--text-h3); }
.delivered-report-summary p { margin: var(--space-2) 0; line-height: var(--leading-body); }
.delivered-report-summary small { color: var(--muted); }
.delivery-links { display: flex; flex-wrap: wrap; gap: var(--space-3); flex-shrink: 0; }
@media (max-width: 720px) { .delivered-report-summary { align-items: stretch; flex-direction: column; } .delivery-links > * { flex: 1; text-align: center; } }
</style>
