<script setup>
import { Button as VanButton } from 'vant'
import {
  actionLabel,
  decisionStatusText,
  formatDate,
  formatDateTime,
  pageCount,
  reportStatusText,
  resourceLabel
} from '../formatters.js'

defineProps({
  auditLoading: { type: Boolean, default: false },
  auditLogs: { type: Object, required: true },
  behaviorFilters: { type: Object, required: true },
  decisionLoading: { type: Boolean, default: false },
  decisionLogs: { type: Object, required: true },
  decisionPage: { type: Number, default: 1 },
  decisionPageSize: { type: Number, default: 20 },
  logFilters: { type: Object, required: true },
  logPage: { type: Number, default: 1 },
  logPageSize: { type: Number, default: 20 },
  logSection: { type: String, default: 'audit' },
  reportTasks: { type: Object, required: true },
  staffUsers: { type: Array, default: () => [] },
  taskFilters: { type: Object, required: true },
  taskPage: { type: Number, default: 1 },
  taskPageSize: { type: Number, default: 12 },
  tasksLoading: { type: Boolean, default: false }
})

defineEmits([
  'change-decision-page',
  'change-log-page',
  'change-task-page',
  'export',
  'load-audit-logs',
  'open-log',
  'reset-log-filters',
  'search-decision-logs',
  'search-tasks',
  'select-section'
])
</script>

<template>
  <section class="content-view">
    <div class="view-heading"><div><p class="eyebrow">TRACE / AUDIT &amp; BEHAVIOR</p><h2>日志中心</h2><p>关键变更、用户行动与任务状态都留下可追溯的痕迹。</p></div><VanButton v-if="logSection !== 'tasks'" class="secondary-button" type="default" plain native-type="button" @click="$emit('export', logSection === 'audit' ? 'audit-logs' : 'decision-logs')"><IconMark name="download" /> <span>导出当前 CSV</span></VanButton></div>
    <div class="section-switch" role="group" aria-label="日志类型">
      <button type="button" :class="{ active: logSection === 'audit' }" :aria-pressed="logSection === 'audit'" @click="$emit('select-section', 'audit')">审计日志</button>
      <button type="button" :class="{ active: logSection === 'behavior' }" :aria-pressed="logSection === 'behavior'" @click="$emit('select-section', 'behavior')">用户行动记录</button>
      <button type="button" :class="{ active: logSection === 'tasks' }" :aria-pressed="logSection === 'tasks'" @click="$emit('select-section', 'tasks')">报告任务日志</button>
    </div>

    <template v-if="logSection === 'audit'">
      <div class="filter-bar">
        <input v-model.trim="logFilters.search" aria-label="搜索用户、详情或操作" placeholder="搜索用户、详情或操作" @keyup.enter="$emit('load-audit-logs')">
        <input v-model.trim="logFilters.action" aria-label="按操作类型筛选" placeholder="操作类型，例如 user.role.update">
        <input v-model.trim="logFilters.resource_type" aria-label="按资源类型筛选" placeholder="资源类型">
        <select v-model="logFilters.actor_user_id" aria-label="按操作者筛选"><option value="">全部操作者</option><option v-for="member in staffUsers" :key="member.id" :value="member.id">{{ member.name }}</option></select>
        <input v-model.trim="logFilters.target_user_id" type="number" min="1" aria-label="按目标用户 ID 筛选" placeholder="目标用户 ID">
        <label class="date-filter"><span>自</span><input v-model="logFilters.date_from" type="date"></label>
        <label class="date-filter"><span>至</span><input v-model="logFilters.date_to" type="date"></label>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="$emit('load-audit-logs')">查询</VanButton>
        <VanButton class="filter-reset" type="default" plain native-type="button" @click="$emit('reset-log-filters')">清空</VanButton>
      </div>
      <div v-if="auditLoading" class="list-loading" aria-label="正在加载审计日志"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ auditLogs.total }} 条审计记录</span><span>详情不包含密码、令牌或 AI Prompt</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
          <table class="admin-table audit-table">
            <thead><tr><th>时间</th><th>操作</th><th>资源</th><th>操作者</th><th>目标</th><th>请求</th><th>详情</th></tr></thead>
            <tbody>
              <tr v-for="log in auditLogs.items" :key="log.id">
                <td class="muted-text">{{ formatDateTime(log.created_at) }}</td>
                <td><span class="action-code">{{ actionLabel(log.action) }}</span><small>{{ log.action }}</small></td>
                <td>{{ resourceLabel(log.resource_type) }}{{ log.resource_id ? ` #${log.resource_id}` : '' }}</td>
                <td>{{ log.actor_name || log.actor_user_id || '系统' }}</td>
                <td>{{ log.target_user_name || log.target_user_id || '—' }}</td>
                <td><span class="mono-text">{{ log.request_id ? log.request_id.slice(0, 8) : '—' }}</span><small>{{ log.ip_address || '—' }}</small></td>
                <td><button type="button" class="detail-link" @click="$emit('open-log', log)">{{ log.details_json ? '查看 JSON' : (log.details || '—') }}</button></td>
              </tr>
              <tr v-if="!auditLogs.items.length"><td colspan="7" class="empty-cell">暂无审计记录。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ logPage }} / {{ pageCount(auditLogs.total, logPageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="logPage <= 1" @click="$emit('change-log-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="logPage >= pageCount(auditLogs.total, logPageSize)" @click="$emit('change-log-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>

    <template v-else-if="logSection === 'behavior'">
      <div class="filter-bar">
        <input v-model.trim="behaviorFilters.search" aria-label="搜索用户或记录内容" placeholder="搜索用户或记录内容" @keyup.enter="$emit('search-decision-logs')">
        <select v-model="behaviorFilters.kind" aria-label="按记录类型筛选"><option value="">全部类型</option><option value="action">行动</option><option value="decision">决策</option></select>
        <select v-model="behaviorFilters.status" aria-label="按记录状态筛选"><option value="">全部状态</option><option value="done">已完成</option><option value="doing">进行中</option><option value="skipped">已跳过</option></select>
        <label class="date-filter"><span>自</span><input v-model="behaviorFilters.date_from" type="date"></label>
        <label class="date-filter"><span>至</span><input v-model="behaviorFilters.date_to" type="date"></label>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="$emit('search-decision-logs')">查询</VanButton>
      </div>
      <div v-if="decisionLoading" class="list-loading" aria-label="正在加载用户行动记录"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ decisionLogs.total }} 条行动记录</span><span>管理员只读，内容来源于用户本人</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
          <table class="admin-table">
            <thead><tr><th>日期</th><th>用户</th><th>类型</th><th>状态</th><th>记录内容</th><th>备注</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="log in decisionLogs.items" :key="log.id">
                <td>{{ formatDate(log.log_date) }}</td><td>{{ log.user_name }}<small>#{{ log.user_id }}</small></td><td>{{ log.kind === 'decision' ? '决策' : '行动' }}</td>
                <td><span :class="['status-badge', `decision-${log.status}`]">{{ decisionStatusText(log.status) }}</span></td><td class="content-cell">{{ log.content }}</td><td class="content-cell">{{ log.note || '—' }}</td><td class="muted-text">{{ formatDateTime(log.created_at) }}</td>
              </tr>
              <tr v-if="!decisionLogs.items.length"><td colspan="7" class="empty-cell">暂无用户行动记录。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ decisionPage }} / {{ pageCount(decisionLogs.total, decisionPageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="decisionPage <= 1" @click="$emit('change-decision-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="decisionPage >= pageCount(decisionLogs.total, decisionPageSize)" @click="$emit('change-decision-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>

    <template v-else>
      <div class="filter-bar">
        <input v-model.trim="taskFilters.search" aria-label="搜索用户或任务 ID" placeholder="搜索用户或任务 ID" @keyup.enter="$emit('search-tasks')">
        <select v-model="taskFilters.status" aria-label="按任务状态筛选"><option value="">全部状态</option><option value="processing">生成中</option><option value="completed">已完成</option><option value="failed">失败</option></select>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="$emit('search-tasks')">查询</VanButton>
      </div>
      <div v-if="tasksLoading" class="list-loading" aria-label="正在加载报告任务日志"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ reportTasks.total }} 个任务</span><span>旧版生成任务只读；新报告请在服务申请工作流中处理</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
          <table class="admin-table">
            <thead><tr><th>任务</th><th>用户</th><th>状态</th><th>进度</th><th>失败原因</th><th>更新时间</th></tr></thead>
            <tbody>
              <tr v-for="task in reportTasks.items" :key="task.task_id">
                <td><strong class="mono-text">{{ task.task_id.slice(0, 12) }}…</strong><small>{{ task.report_id ? `报告 #${task.report_id}` : '尚未生成报告' }}</small></td>
                <td>{{ task.user_name || `用户 #${task.user_id}` }}</td><td><span :class="['status-badge', `task-${task.status}`]">{{ reportStatusText(task.status) }}</span><small v-if="task.retry_count">第 {{ task.retry_count }} 次重试</small></td>
                <td>{{ task.progress }}%</td><td class="error-cell">{{ task.error || '—' }}</td><td class="muted-text">{{ formatDateTime(task.updated_at) }}</td>
              </tr>
              <tr v-if="!reportTasks.items.length"><td colspan="6" class="empty-cell">暂无报告任务日志。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ taskPage }} / {{ pageCount(reportTasks.total, taskPageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="taskPage <= 1" @click="$emit('change-task-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="taskPage >= pageCount(reportTasks.total, taskPageSize)" @click="$emit('change-task-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>
  </section>
</template>
