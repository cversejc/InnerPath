<script setup>
import { Button as VanButton } from 'vant'
import { formatDateTime } from '../formatters.js'

defineProps({
  calendarRequests: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  statusFilter: { type: String, default: '' }
})

defineEmits(['refresh', 'update-status-filter'])

function statusLabel(status) {
  return {
    generating: 'AI 生成中',
    fulfilled: '已生成并交付',
    failed: '生成失败',
    pending: '历史申请',
    reviewing: '历史申请',
    rejected: '已退回',
    cancelled: '已取消'
  }[status] || status
}
</script>

<template>
  <section class="content-view calendar-request-admin-view">
    <div class="view-heading">
      <div><p class="eyebrow">CALENDAR / DELIVERY HISTORY</p><h2>日历生成记录</h2><p>日历基于已交付报告自动生成并交付；此处仅供管理员查看。</p></div>
      <div class="filter-bar compact-filter">
        <select :value="statusFilter" aria-label="按生成状态筛选" @change="$emit('update-status-filter', $event.target.value)"><option value="">全部状态</option><option value="generating">AI 生成中</option><option value="fulfilled">已生成并交付</option><option value="failed">生成失败</option><option value="pending">历史申请</option></select>
        <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="loading" :aria-busy="loading" @click="$emit('refresh')">
          <template #icon><IconMark name="refresh" /></template>
          刷新申请
        </VanButton>
      </div>
    </div>
    <div v-if="loading" class="list-loading" aria-label="正在加载日历申请"><i v-for="index in 4" :key="index"></i></div>
    <div v-else class="calendar-request-admin-list">
      <article v-for="item in calendarRequests" :key="item.id" class="panel-surface calendar-request-admin-card">
        <div class="calendar-request-admin-head"><div><p class="eyebrow">REQUEST #{{ item.id }} · USER #{{ item.user_id }}</p><h3>{{ item.start_date }} — {{ item.end_date }}</h3><span>档案版本 v{{ item.profile_version }} · 提交于 {{ formatDateTime(item.created_at) }}</span></div><span :class="['status-badge', `request-${item._status}`]">{{ statusLabel(item._status) }}</span></div>
        <div class="calendar-request-admin-body"><div><span>来源报告</span><strong>#{{ item.source_report_id || '—' }}</strong></div><div><span>交付日历</span><strong>#{{ item.calendar_id || '—' }}</strong></div><div><span>关注领域</span><strong>{{ item.focus_topics?.join('、') || '—' }}</strong></div><div><span>日历用途</span><strong>{{ item.usage_scenario || '—' }}</strong></div><div class="request-goal"><span>当前决策目标</span><p>{{ item.goal || '—' }}</p></div><div class="request-goal"><span>生成状态</span><p>{{ item.generation_error || statusLabel(item.status) }}</p></div></div>
      </article>
      <p v-if="!calendarRequests.length" class="empty-cell">暂无符合条件的日历申请。</p>
    </div>
  </section>
</template>
