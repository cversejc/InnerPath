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
import AdminAssignmentDialog from './AdminAssignmentDialog.vue'
import { firstNonEmptyArray, topicLabel, usageScenarioLabel } from '../../../utils/displayLabels.js'

function requestTopicValues(payload) {
  return firstNonEmptyArray(
    payload?.selected_topics,
    payload?.context?.focus_topics,
    payload?.context?.selected_topics
  )
}

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
    COMPLETED: '已完成',
    FAILED: '处理失败'
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
  assignmentError: { type: String, default: '' },
  assignmentRequest: { type: Object, default: null },
  assignmentSavingKey: { type: String, default: '' },
  filters: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  consultantWorkloads: { type: Array, default: () => [] },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  requestKind: { type: String, default: 'consultant' },
  retryingRequestKey: { type: String, default: '' },
  serviceRequests: { type: Object, required: true }
})

defineEmits([
  'change-kind',
  'change-page',
  'assign-request',
  'close-assignment',
  'open-assignment',
  'open-report',
  'open-workflow',
  'open-user',
  'reset-filters',
  'retry-service-request',
  'retry-calendar-request',
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
        <select v-model="filters.queue_filter" aria-label="按运营待办筛选">
          <option value="">全部运营状态</option>
          <option value="incomplete_assignment">咨询师席位未完整分配</option>
          <option value="incomplete_assignment_over_24h">超过 24 小时未完成分配</option>
          <option value="stale_over_24h">旧流程申请超过 24 小时未更新</option>
          <option value="workflow_attention">报告协作节点失败或停滞</option>
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
                <td class="request-summary-cell"><strong>{{ consultationTypeLabel(item.consultation_type) }}</strong><small>{{ item.request_payload?.context?.current_challenge || item.request_payload?.calendar_goal || '未填写目标' }}</small><small>{{ topicLabel(requestTopicValues(item.request_payload), '未选择关注主题') }}</small></td>
                <td>
                  <div class="request-assignee-summary">
                    <span v-if="item.is_collaborative">命理：{{ item.assigned_mingli_consultant_name || '待分配' }}</span>
                    <span v-if="item.is_collaborative">心理：{{ item.assigned_psychology_consultant_name || '待分配' }}</span>
                    <span v-else>{{ item.assigned_consultant_name || '待分配' }}<small v-if="item.assigned_consultant_id">#{{ item.assigned_consultant_id }}</small></span>
                  </div>
                  <VanButton class="secondary-button compact-button request-assignment-button" type="default" plain native-type="button" :disabled="['delivered', 'withdrawn', 'rejected'].includes(item.status)" @click="$emit('open-assignment', item)">{{ item.is_collaborative ? '管理专业分工' : (item.assigned_consultant_id ? '改派负责人' : '分配负责人') }}</VanButton>
                </td>
                <td>
                  <span :class="['status-badge', `request-${item.status}`]">{{ serviceRequestStatusText(item.status) }}</span>
                  <small v-if="item.current_step_key">{{ reportStepLabel(item.current_step_key) }} · {{ reportStepStatusLabel(item.current_step_status) }}</small>
                  <small v-if="item.current_step_updated_at">节点更新 {{ formatDateTime(item.current_step_updated_at) }}</small>
                  <small v-if="item.current_step_error" class="request-note error-cell">{{ item.current_step_error }}</small>
                  <small v-if="item.report_case_status">工作流：{{ reportCaseStatusLabel(item.report_case_status) }}</small>
                  <small v-if="item.needs_info_reason" class="request-note">待补充：{{ item.needs_info_reason }}</small>
                  <small v-if="item.last_error" class="request-note error-cell">{{ item.last_error }}</small>
                  <VanButton
                    v-if="item.status === 'failed' && item.service_type === 'report' && !item.report_case_id"
                    class="secondary-button compact-button request-retry-button"
                    type="default"
                    plain
                    native-type="button"
                    :disabled="Boolean(retryingRequestKey)"
                    :loading="retryingRequestKey === `service-${item.id}`"
                    @click="$emit('retry-service-request', item.id)"
                  >重试初稿</VanButton>
                  <VanButton
                    v-if="filters.queue_filter === 'workflow_attention' && item.report_case_id"
                    class="secondary-button compact-button request-retry-button"
                    type="default"
                    plain
                    native-type="button"
                    @click="$emit('open-workflow', item)"
                  >打开报告工作区</VanButton>
                </td>
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
          <option value="queued">排队中</option><option value="generating">生成中</option>
          <option value="failed">生成失败</option><option value="fulfilled">已完成</option>
          <option value="rejected">已退回</option><option value="cancelled">已取消</option>
        </select>
        <select v-model="calendarFilters.stalled_only" aria-label="按日历生成时长筛选">
          <option :value="false">全部生成时长</option><option :value="true">生成超过 45 分钟</option>
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
                <td>{{ formatDate(item.start_date) }} — {{ formatDate(item.end_date) }}<small>{{ topicLabel(item.focus_topics, '未选择关注领域') }}</small></td>
                <td class="request-summary-cell"><strong>{{ item.goal || '未填写目标' }}</strong><small>{{ usageScenarioLabel(item.usage_scenario, '未填写用途') }}</small></td>
                <td><span :class="['status-badge', `calendar-request-${item.status}`]">{{ calendarRequestStatusText(item.status) }}</span><small v-if="item.status === 'generating'">{{ item.progress }}% · 第 {{ item.retry_count + 1 }} 次</small><small v-if="item.generation_error" class="request-note error-cell">{{ item.generation_error }}</small></td>
                <td>{{ item.source_report_id ? `报告 #${item.source_report_id}` : '—' }}</td>
                <td>{{ formatDateTime(item.created_at) }}<small>更新 {{ formatDateTime(item.updated_at) }}</small></td>
                <td><details class="request-payload-details"><summary>申请内容</summary><pre>{{ prettyJson(item) }}</pre></details><small v-if="item.reviewed_at">审核 {{ formatDateTime(item.reviewed_at) }} · {{ item.reviewer_id ? `成员 #${item.reviewer_id}` : '—' }}</small><small v-if="item.review_note">{{ item.review_note }}</small><small v-if="item.calendar_id">日历 #{{ item.calendar_id }}</small><VanButton v-if="item.status === 'failed'" class="secondary-button compact-button request-retry-button" type="default" plain native-type="button" :disabled="Boolean(retryingRequestKey)" :loading="retryingRequestKey === `calendar-${item.id}`" @click="$emit('retry-calendar-request', item.id)">重试生成</VanButton></td>
              </tr>
              <tr v-if="!calendarRequests.items.length"><td colspan="7" class="empty-cell">暂无符合条件的日历申请。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ page }} / {{ pageCount(calendarRequests.total, pageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page <= 1" @click="$emit('change-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page >= pageCount(calendarRequests.total, pageSize)" @click="$emit('change-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>
    <AdminAssignmentDialog
      :assignment-error="assignmentError"
      :assignment-saving-key="assignmentSavingKey"
      :consultants="consultants"
      :consultant-workloads="consultantWorkloads"
      :request="assignmentRequest"
      @close="$emit('close-assignment')"
      @save="$emit('assign-request', $event)"
    />
  </section>
</template>
