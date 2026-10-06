<script setup>
import { ref, watch } from 'vue'
import { Button as VanButton } from 'vant'
import AdminReportQualityIssuesSection from './AdminReportQualityIssuesSection.vue'
import { formatDateTime, pageCount } from '../formatters.js'

const props = defineProps({
  assignees: { type: Array, default: () => [] },
  feedback: { type: Object, required: true },
  filters: { type: Object, required: true },
  view: { type: String, default: 'feedback' },
  loading: { type: Boolean, default: false },
  qualityFilters: { type: Object, required: true },
  qualityIssues: { type: Object, required: true },
  qualityLoading: { type: Boolean, default: false },
  qualityPage: { type: Number, default: 1 },
  qualityPageSize: { type: Number, default: 20 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  savingId: { type: Number, default: null }
})

const emit = defineEmits(['change-page', 'save', 'search', 'select-view', 'search-quality', 'change-quality-page'])
const editById = ref({})

watch(() => props.feedback.items, items => {
  editById.value = Object.fromEntries((items || []).map(item => [item.id, {
    status: item.status,
    assignedTo: item.assigned_to ? String(item.assigned_to) : '',
    resolution: item.resolution || ''
  }]))
}, { immediate: true })

const feedbackTypeText = value => ({
  PRAISE: '表扬',
  SUGGESTION: '建议',
  COMPLAINT: '投诉'
}[value] || value)

const feedbackStatusText = value => ({
  NEW: '待处理',
  IN_PROGRESS: '处理中',
  RESOLVED: '已结案'
}[value] || value)

function serviceTarget(item) {
  if (item.service_type === 'report') {
    return `报告申请 #${item.service_request_id}${item.service_result_id ? ` · 报告 #${item.service_result_id}` : ''}`
  }
  return `日历申请 #${item.calendar_request_id}${item.service_result_id ? ` · 日历 #${item.service_result_id}` : ''}`
}

function sourceStatusText(status) {
  return { delivered: '已交付', fulfilled: '已完成' }[status] || status
}

function saveItem(item) {
  const edit = editById.value[item.id]
  if (!edit) return
  emit('save', {
    id: item.id,
    status: edit.status,
    assigned_to: edit.assignedTo,
    resolution: edit.resolution
  })
}
</script>

<template>
  <section class="content-view feedback-admin-view">
    <div class="view-heading">
      <div>
        <p class="eyebrow">SERVICE QUALITY</p>
        <h2>服务质量</h2>
        <p>用户反馈 · 报告质检</p>
      </div>
    </div>

    <div class="section-switch" role="group" aria-label="服务质量视图">
      <button type="button" :aria-pressed="view === 'feedback'" :class="{ active: view === 'feedback' }" @click="emit('select-view', 'feedback')">用户反馈</button>
      <button type="button" :aria-pressed="view === 'quality'" :class="{ active: view === 'quality' }" @click="emit('select-view', 'quality')">报告质检</button>
    </div>

    <template v-if="view === 'feedback'">
    <form class="filter-bar" @submit.prevent="emit('search')">
      <input v-model.trim="filters.search" aria-label="搜索用户、反馈或记录编号" placeholder="搜索姓名、手机号、反馈内容或编号">
      <select v-model="filters.service_type" aria-label="按服务类型筛选">
        <option value="">全部服务</option>
        <option value="report">报告</option>
        <option value="calendar">日历</option>
      </select>
      <select v-model="filters.feedback_type" aria-label="按反馈类型筛选">
        <option value="">全部反馈类型</option>
        <option value="COMPLAINT">投诉</option>
        <option value="SUGGESTION">建议</option>
        <option value="PRAISE">表扬</option>
      </select>
      <select v-model="filters.status" aria-label="按处理状态筛选">
        <option value="">全部状态</option>
        <option value="NEW">待处理</option>
        <option value="IN_PROGRESS">处理中</option>
        <option value="RESOLVED">已结案</option>
      </select>
      <label class="date-filter"><span>创建自</span><input v-model="filters.date_from" type="date"></label>
      <label class="date-filter"><span>至</span><input v-model="filters.date_to" type="date"></label>
      <VanButton class="primary-button compact-button" type="primary" native-type="submit">查询</VanButton>
    </form>

    <div v-if="loading" class="list-loading" aria-label="正在加载服务反馈" aria-busy="true">
      <i v-for="index in 4" :key="index"></i>
    </div>
    <div v-else class="table-panel">
      <div class="table-meta">
        <span>共 {{ feedback.total }} 条反馈</span>
        <span>按待处理、处理中、已结案排序</span>
      </div>
      <div class="admin-table-wrap" tabindex="0" aria-label="反馈列表，可横向滚动查看">
        <table class="admin-table feedback-admin-table">
          <thead>
            <tr><th>反馈</th><th>用户</th><th>关联服务</th><th>内容</th><th>处理状态</th><th>负责人</th><th>处理说明</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in feedback.items" :key="item.id">
              <td>
                <strong>#{{ item.id }} · {{ feedbackTypeText(item.feedback_type) }}</strong>
                <small>{{ formatDateTime(item.created_at) }}</small>
                <small v-if="item.rating">评分 {{ item.rating }} / 5</small>
              </td>
              <td><strong>{{ item.user_name || `用户 #${item.user_id}` }}</strong><small>{{ item.user_phone || '—' }}</small></td>
              <td><strong>{{ serviceTarget(item) }}</strong><small>服务状态：{{ sourceStatusText(item.source_status) }}</small></td>
              <td class="feedback-comment-cell">{{ item.comment }}</td>
              <td>
                <span :class="['status-badge', editById[item.id]?.status === 'RESOLVED' ? 'success' : editById[item.id]?.status === 'IN_PROGRESS' ? 'calendar-draft' : 'report-failed']">{{ feedbackStatusText(editById[item.id]?.status || item.status) }}</span>
                <select v-model="editById[item.id].status" :aria-label="`反馈 #${item.id} 处理状态`">
                  <option value="NEW">待处理</option>
                  <option value="IN_PROGRESS">处理中</option>
                  <option value="RESOLVED">已结案</option>
                </select>
              </td>
              <td>
                <select v-model="editById[item.id].assignedTo" :aria-label="`反馈 #${item.id} 负责人`">
                  <option value="">未分派</option>
                  <option v-for="person in assignees" :key="person.id" :value="String(person.id)">{{ person.name || `管理员 #${person.id}` }}</option>
                </select>
                <small v-if="item.resolved_at">结案 {{ formatDateTime(item.resolved_at) }}</small>
              </td>
              <td>
                <textarea v-model.trim="editById[item.id].resolution" rows="3" :disabled="editById[item.id].status !== 'RESOLVED'" :aria-label="`反馈 #${item.id} 处理说明`" placeholder="结案时填写处理说明"></textarea>
              </td>
              <td><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :loading="savingId === item.id" :disabled="savingId !== null" @click="saveItem(item)">保存</VanButton></td>
            </tr>
            <tr v-if="!feedback.items.length"><td colspan="8" class="empty-cell">当前筛选下没有反馈记录。</td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <span>第 {{ page }} / {{ pageCount(feedback.total, pageSize) }} 页</span>
        <div>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page <= 1" @click="emit('change-page', -1)">上一页</VanButton>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page >= pageCount(feedback.total, pageSize)" @click="emit('change-page', 1)">下一页</VanButton>
        </div>
      </div>
    </div>
    </template>
    <AdminReportQualityIssuesSection
      v-else
      :filters="qualityFilters"
      :issues="qualityIssues"
      :loading="qualityLoading"
      :page="qualityPage"
      :page-size="qualityPageSize"
      @change-page="emit('change-quality-page', $event)"
      @search="emit('search-quality')"
    />
  </section>
</template>
