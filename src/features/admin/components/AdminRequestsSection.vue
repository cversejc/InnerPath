<script setup>
import { Button as VanButton } from 'vant'
import {
  calendarRequestStatusText,
  formatDate,
  formatDateTime,
  pageCount,
  prettyJson,
  serviceRequestStatusText
} from '../formatters.js'
import { consultationTypeLabel } from '../../service-requests/formatters.js'

function reportStepLabel(stepKey) {
  const number = String(stepKey || '').match(/\d+/)?.[0]
  return number ? `第 ${number} 步` : '尚未开始'
}

function reportStepStatusLabel(status) {
  return {
    READY: '待开始',
    IN_REVIEW: '审阅中',
    EXECUTING: '处理中',
    WAITING_REVIEW: '待复核',
    COMPLETED: '已完成'
  }[status] || '待处理'
}

function reportCaseStatusLabel(status) {
  return {
    ACTIVE: '进行中',
    BLOCKED: '受阻',
    READY_TO_DELIVER: '待交付',
    DELIVERED: '已交付',
    CANCELLED: '已关闭'
  }[status] || ''
}

defineProps({
  calendarFilters: { type: Object, required: true },
  calendarRequests: { type: Object, required: true },
  consultants: { type: Array, default: () => [] },
  filters: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  requestKind: { type: String, default: 'consultant' },
  serviceRequests: { type: Object, required: true }
})

defineEmits([
  'change-kind',
  'change-page',
  'open-report',
  'open-user',
  'reset-filters',
  'search'
])
</script>

<template>
  <section class="content-view admin-requests-view">
    <div class="view-heading">
      <div>
        <p class="eyebrow">INTAKE / DELIVERY TRACKING</p>
        <h2>申请与交付</h2>
        <p>查看用户提交内容、负责人及每个处理节点的时间记录。</p>
      </div>
      <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="loading" :loading="loading" loading-text="刷新中…" @click="$emit('search')">
        <template #icon><IconMark name="refresh" /></template>
        刷新记录
      </VanButton>
    </div>

    <div class="request-kind-switch" role="group" aria-label="申请类型">
      <button type="button" :aria-pressed="requestKind === 'consultant'" :class="{ active: requestKind === 'consultant' }" @click="$emit('change-kind', 'consultant')">
        报告申请 <span>{{ requestKind === 'consultant' ? serviceRequests.total : '咨询师交付' }}</span>
      </button>
      <button type="button" :aria-pressed="requestKind === 'calendar'" :class="{ active: requestKind === 'calendar' }" @click="$emit('change-kind', 'calendar')">
        日历申请 <span>{{ requestKind === 'calendar' ? calendarRequests.total : 'AI 生成' }}</span>
      </button>
    </div>

    <template v-if="requestKind === 'consultant'">
      <div class="filter-bar">
        <input v-model.trim="filters.search" aria-label="搜索用户姓名或手机号" placeholder="搜索姓名或手机号" @keyup.enter="$emit('search')">
        <select v-model="filters.status" aria-label="按申请状态筛选">
          <option value="">全部状态</option>
          <option value="submitted">待接单</option><option value="accepted">已接单</option>
          <option value="ai_processing">生成初稿</option><option value="ai_ready">待审校</option>
          <option value="reviewing">审校中</option><option value="needs_info">待补充</option>
          <option value="failed">处理失败</option><option value="delivered">已交付</option>
          <option value="withdrawn">已撤回</option><option value="rejected">已关闭</option>
        </select>
        <select v-model="filters.consultant_id" aria-label="按咨询师筛选">
          <option value="">全部咨询师</option>
          <option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option>
        </select>
        <label class="date-filter"><span>提交自</span><input v-model="filters.date_from" type="date"></label>
        <label class="date-filter"><span>至</span><input v-model="filters.date_to" type="date"></label>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="$emit('search')">查询</VanButton>
        <VanButton class="filter-reset" type="default" plain native-type="button" @click="$emit('reset-filters')">清空</VanButton>
      </div>

      <div v-if="loading" class="list-loading" aria-label="正在加载报告申请"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ serviceRequests.total }} 份报告申请</span><span>接单与交付时间来自服务申请生命周期记录</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="报告申请列表，可横向滚动查看">
          <table class="admin-table admin-request-table">
            <thead><tr><th>申请 / 用户</th><th>咨询方向 / 关注内容</th><th>咨询师</th><th>状态与流程</th><th>提交</th><th>接单</th><th>交付</th><th>记录</th></tr></thead>
            <tbody>
              <tr v-for="item in serviceRequests.items" :key="item.id">
                <td><strong>申请 #{{ item.id }}</strong><small>{{ item.user_name || `用户 #${item.user_id}` }} · {{ item.user_phone || '—' }}</small><button type="button" class="detail-link" @click="$emit('open-user', { id: item.user_id, name: item.user_name })">查看用户</button></td>
                <td class="request-summary-cell"><strong>{{ consultationTypeLabel(item.consultation_type) }}</strong><small>{{ item.request_payload?.context?.current_challenge || item.request_payload?.calendar_goal || '未填写目标' }}</small><small>{{ item.request_payload?.selected_topics?.join('、') || item.request_payload?.context?.selected_topics?.join('、') || '未选择关注主题' }}</small></td>
                <td>{{ item.assigned_consultant_name || '待分配' }}<small v-if="item.assigned_consultant_id">#{{ item.assigned_consultant_id }}</small><small v-if="item.assigned_mingli_consultant_id">命理：{{ item.assigned_mingli_consultant_name || `#${item.assigned_mingli_consultant_id}` }}</small><small v-if="item.assigned_psychology_consultant_id">心理：{{ item.assigned_psychology_consultant_name || `#${item.assigned_psychology_consultant_id}` }}</small></td>
                <td><span :class="['status-badge', `request-${item.status}`]">{{ serviceRequestStatusText(item.status) }}</span><small v-if="item.current_step_key">{{ reportStepLabel(item.current_step_key) }} · {{ reportStepStatusLabel(item.current_step_status) }}</small><small v-if="item.report_case_status">工作流：{{ reportCaseStatusLabel(item.report_case_status) }}</small><small v-if="item.needs_info_reason" class="request-note">待补充：{{ item.needs_info_reason }}</small><small v-if="item.last_error" class="request-note error-cell">{{ item.last_error }}</small></td>
                <td>{{ formatDateTime(item.created_at) }}</td>
                <td>{{ formatDateTime(item.accepted_at) }}</td>
                <td>{{ formatDateTime(item.delivered_at) }}</td>
                <td>
                  <details class="request-payload-details"><summary>申请内容</summary><pre>{{ prettyJson(item.request_payload) }}</pre></details>
                  <button v-if="item.result_type === 'report' && item.result_id" type="button" class="detail-link" @click="$emit('open-report', { id: item.result_id })">查看报告 #{{ item.result_id }}</button>
                  <small v-else-if="item.result_id">交付结果 #{{ item.result_id }}</small>
                </td>
              </tr>
              <tr v-if="!serviceRequests.items.length"><td colspan="8" class="empty-cell">暂无符合条件的报告申请。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ page }} / {{ pageCount(serviceRequests.total, pageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page <= 1" @click="$emit('change-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page >= pageCount(serviceRequests.total, pageSize)" @click="$emit('change-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>

    <template v-else>
      <div class="filter-bar">
        <input v-model.trim="calendarFilters.search" aria-label="搜索用户姓名或手机号" placeholder="搜索姓名或手机号" @keyup.enter="$emit('search')">
        <select v-model="calendarFilters.status" aria-label="按日历申请状态筛选">
          <option value="">全部状态</option><option value="pending">待生成</option>
          <option value="processing">生成中</option><option value="delivered">已交付</option>
          <option value="failed">生成失败</option><option value="reviewing">审核中</option>
          <option value="fulfilled">已完成</option><option value="rejected">已退回</option><option value="cancelled">已取消</option>
        </select>
        <label class="date-filter"><span>提交自</span><input v-model="calendarFilters.date_from" type="date"></label>
        <label class="date-filter"><span>至</span><input v-model="calendarFilters.date_to" type="date"></label>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="$emit('search')">查询</VanButton>
        <VanButton class="filter-reset" type="default" plain native-type="button" @click="$emit('reset-filters')">清空</VanButton>
      </div>

      <div v-if="loading" class="list-loading" aria-label="正在加载日历申请"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ calendarRequests.total }} 份日历申请</span><span>包含来源报告、生成进度、重试次数及后台审核记录</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="日历申请列表，可横向滚动查看">
          <table class="admin-table admin-request-table calendar-request-table">
            <thead><tr><th>申请 / 用户</th><th>周期与关注</th><th>目标</th><th>生成状态</th><th>来源报告</th><th>提交 / 更新</th><th>记录</th></tr></thead>
            <tbody>
              <tr v-for="item in calendarRequests.items" :key="item.id">
                <td><strong>申请 #{{ item.id }}</strong><small>{{ item.user_name || `用户 #${item.user_id}` }} · {{ item.user_phone || '—' }}</small><button type="button" class="detail-link" @click="$emit('open-user', { id: item.user_id, name: item.user_name })">查看用户</button></td>
                <td>{{ formatDate(item.start_date) }} — {{ formatDate(item.end_date) }}<small>{{ item.focus_topics?.join('、') || '未选择关注领域' }}</small></td>
                <td class="request-summary-cell"><strong>{{ item.goal || '未填写目标' }}</strong><small>{{ item.usage_scenario || '未填写用途' }}</small></td>
                <td><span :class="['status-badge', `calendar-request-${item.status}`]">{{ calendarRequestStatusText(item.status) }}</span><small v-if="item.status === 'processing'">{{ item.progress }}% · 第 {{ item.retry_count + 1 }} 次</small><small v-if="item.generation_error" class="request-note error-cell">{{ item.generation_error }}</small></td>
                <td>{{ item.source_report_id ? `报告 #${item.source_report_id}` : '—' }}</td>
                <td>{{ formatDateTime(item.created_at) }}<small>更新 {{ formatDateTime(item.updated_at) }}</small></td>
                <td><details class="request-payload-details"><summary>申请内容</summary><pre>{{ prettyJson(item) }}</pre></details><small v-if="item.reviewed_at">审核 {{ formatDateTime(item.reviewed_at) }} · {{ item.reviewer_id ? `成员 #${item.reviewer_id}` : '—' }}</small><small v-if="item.review_note">{{ item.review_note }}</small><small v-if="item.calendar_id">日历 #{{ item.calendar_id }}</small></td>
              </tr>
              <tr v-if="!calendarRequests.items.length"><td colspan="7" class="empty-cell">暂无符合条件的日历申请。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ page }} / {{ pageCount(calendarRequests.total, pageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page <= 1" @click="$emit('change-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page >= pageCount(calendarRequests.total, pageSize)" @click="$emit('change-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>
  </section>
</template>
