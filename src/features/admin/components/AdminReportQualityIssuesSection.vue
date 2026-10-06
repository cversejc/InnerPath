<script setup>
import { Button as VanButton } from 'vant'
import { formatDateTime, pageCount } from '../formatters.js'

defineProps({
  filters: { type: Object, required: true },
  issues: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 }
})

const emit = defineEmits(['change-page', 'search'])

const severityText = value => ({ BLOCK: '阻断', MAJOR: '主要', MINOR: '提示' }[value] || value)
const issueStatusText = value => ({ OPEN: '待处理', RESOLVED: '已解决', ACCEPTED: '已接受', DISMISSED: '已忽略' }[value] || value)
const sourceTypeText = value => ({ PROGRAMMATIC: '规则检查', VALIDATOR: '语义检查' }[value] || value)
const caseStatusText = value => ({ CREATED: '新建', ACTIVE: '处理中', BLOCKED: '受阻', READY_TO_DELIVER: '待交付', DELIVERED: '已交付', CANCELLED: '已取消' }[value] || value)
</script>

<template>
  <div class="quality-issues-view">
    <form class="filter-bar" @submit.prevent="emit('search')">
      <input v-model.trim="filters.search" aria-label="搜索用户或质检问题" placeholder="搜索姓名、手机号、问题内容或案例编号">
      <select v-model="filters.status" aria-label="按质检状态筛选">
        <option value="">全部质检状态</option>
        <option value="OPEN">待处理</option>
        <option value="RESOLVED">已解决</option>
        <option value="ACCEPTED">已接受</option>
        <option value="DISMISSED">已忽略</option>
      </select>
      <select v-model="filters.severity" aria-label="按问题级别筛选">
        <option value="">全部级别</option>
        <option value="BLOCK">阻断</option>
        <option value="MAJOR">主要</option>
        <option value="MINOR">提示</option>
      </select>
      <select v-model="filters.source_type" aria-label="按检查来源筛选">
        <option value="">全部来源</option>
        <option value="PROGRAMMATIC">规则检查</option>
        <option value="VALIDATOR">语义检查</option>
      </select>
      <label class="date-filter"><span>创建自</span><input v-model="filters.date_from" type="date"></label>
      <label class="date-filter"><span>至</span><input v-model="filters.date_to" type="date"></label>
      <VanButton class="primary-button compact-button" type="primary" native-type="submit">查询</VanButton>
    </form>

    <div v-if="loading" class="list-loading" aria-label="正在加载报告质检问题" aria-busy="true">
      <i v-for="index in 4" :key="index"></i>
    </div>
    <div v-else class="table-panel">
      <div class="table-meta"><span>共 {{ issues.total }} 条质检问题</span><span>报告案例 · S6 质量环节</span></div>
      <div class="admin-table-wrap" tabindex="0" aria-label="报告质检列表，可横向滚动查看">
        <table class="admin-table quality-issues-table">
          <thead><tr><th>级别 / 状态</th><th>用户与案例</th><th>检查项</th><th>质检问题</th><th>处理记录</th><th>时间</th></tr></thead>
          <tbody>
            <tr v-for="item in issues.items" :key="item.id">
              <td>
                <span :class="['status-badge', `quality-severity-${item.severity.toLowerCase()}`]">{{ severityText(item.severity) }}</span>
                <small class="quality-source">{{ sourceTypeText(item.source_type) }}</small>
                <span :class="['status-badge', item.status === 'OPEN' ? 'report-failed' : 'success']">{{ issueStatusText(item.status) }}</span>
                <small>{{ item.is_current ? '当前报告版本' : '历史质检记录' }}</small>
              </td>
              <td>
                <strong>{{ item.user_name || `用户 #${item.user_id}` }}</strong>
                <small>{{ item.user_phone || '—' }}</small>
                <small>案例 #{{ item.report_case_id }} · {{ caseStatusText(item.report_case_status) }}</small>
                <small v-if="item.service_request_id">报告申请 #{{ item.service_request_id }}</small>
              </td>
              <td>
                <strong>{{ item.issue_type }}</strong>
                <small>{{ item.target_fragment_key || '全篇' }}</small>
                <small>问题 #{{ item.id }}</small>
              </td>
              <td class="quality-message-cell">
                <p>{{ item.message }}</p>
                <small v-if="item.suggestion">建议：{{ item.suggestion }}</small>
              </td>
              <td class="quality-message-cell">
                <span v-if="item.resolution">{{ item.resolution }}</span>
                <span v-else class="muted-text">尚无处理记录</span>
                <small v-if="item.resolved_at">{{ formatDateTime(item.resolved_at) }}</small>
              </td>
              <td class="muted-text">{{ formatDateTime(item.created_at) }}</td>
            </tr>
            <tr v-if="!issues.items.length"><td colspan="6" class="empty-cell">当前筛选下没有质检问题。</td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <span>第 {{ page }} / {{ pageCount(issues.total, pageSize) }} 页</span>
        <div>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page <= 1" @click="emit('change-page', -1)">上一页</VanButton>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="page >= pageCount(issues.total, pageSize)" @click="emit('change-page', 1)">下一页</VanButton>
        </div>
      </div>
    </div>
  </div>
</template>
