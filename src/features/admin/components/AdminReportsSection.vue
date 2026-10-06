<script setup>
import { Button as VanButton } from 'vant'
import { formatDateTime, pageCount, reportStatusText } from '../formatters.js'

const props = defineProps({
  pageSize: { type: Number, default: 12 },
  reportFilters: { type: Object, required: true },
  reportPage: { type: Number, default: 1 },
  reportSection: { type: String, default: 'reports' },
  reports: { type: Object, required: true },
  reportsLoading: { type: Boolean, default: false },
  reportTasks: { type: Object, required: true },
  taskFilters: { type: Object, required: true },
  taskPage: { type: Number, default: 1 },
  taskPageSize: { type: Number, default: 12 },
  tasksLoading: { type: Boolean, default: false }
})

const emit = defineEmits([
  'change-report-page',
  'change-task-page',
  'export',
  'open-report',
  'search-reports',
  'search-tasks',
  'select-section'
])
</script>

<template>
  <section class="content-view">
    <div class="view-heading"><div><p class="eyebrow">AI / REPORT PIPELINE</p><h2>报告与任务</h2><p>查看全局生成状态，失败任务可受控重试。</p></div><VanButton class="secondary-button" type="default" plain native-type="button" @click="emit('export', 'reports')"><IconMark name="download" /> <span>导出报告 CSV</span></VanButton></div>
    <div class="section-switch">
      <button type="button" :class="{ active: reportSection === 'reports' }" @click="emit('select-section', 'reports')">报告列表</button>
      <button type="button" :class="{ active: reportSection === 'tasks' }" @click="emit('select-section', 'tasks')">生成任务</button>
    </div>

    <template v-if="reportSection === 'reports'">
      <div class="filter-bar">
        <input v-model.trim="reportFilters.search" aria-label="搜索用户或报告标题" placeholder="搜索用户或报告标题" @keyup.enter="emit('search-reports')">
        <select v-model="reportFilters.status" aria-label="按报告状态筛选"><option value="">全部状态</option><option value="completed">已完成</option><option value="processing">生成中</option><option value="failed">失败</option></select>
        <input v-model.trim="reportFilters.ai_model" aria-label="按 AI 模型筛选" placeholder="AI 模型，例如 deepseek-chat" @keyup.enter="emit('search-reports')">
        <label class="date-filter"><span>创建自</span><input v-model="reportFilters.date_from" type="date"></label>
        <label class="date-filter"><span>至</span><input v-model="reportFilters.date_to" type="date"></label>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="emit('search-reports')">查询</VanButton>
      </div>
      <div v-if="reportsLoading" class="list-loading" aria-label="正在加载报告"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ reports.total }} 份报告</span><span>正文只读，生成任务独立追踪</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
          <table class="admin-table">
            <thead><tr><th>报告</th><th>用户</th><th>状态</th><th>模型/耗时</th><th>创建时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="report in reports.items" :key="report.id">
                <td><strong>{{ report.title }}</strong><small>#{{ report.id }} · {{ report.energy_type || '综合型' }}</small></td>
                <td>{{ report.user_name }}<small>{{ report.user_phone }}</small></td>
                <td><span :class="['status-badge', `report-${report.status}`]">{{ reportStatusText(report.status) }}</span></td>
                <td>{{ report.ai_model || '—' }}<small>{{ report.generation_time_ms ? `${report.generation_time_ms} ms` : '—' }}</small></td>
                <td class="muted-text">{{ formatDateTime(report.created_at) }}</td>
                <td><button type="button" class="row-open" @click="emit('open-report', report)">查看 →</button></td>
              </tr>
              <tr v-if="!reports.items.length"><td colspan="6" class="empty-cell">暂无报告记录。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ reportPage }} / {{ pageCount(reports.total, pageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportPage <= 1" @click="emit('change-report-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportPage >= pageCount(reports.total, pageSize)" @click="emit('change-report-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>

    <template v-else>
      <div class="filter-bar">
        <input v-model.trim="taskFilters.search" aria-label="搜索用户或任务 ID" placeholder="搜索用户或任务 ID" @keyup.enter="emit('search-tasks')">
        <select v-model="taskFilters.status" aria-label="按任务状态筛选"><option value="">全部状态</option><option value="processing">生成中</option><option value="completed">已完成</option><option value="failed">失败</option></select>
        <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="emit('search-tasks')">查询</VanButton>
      </div>
      <div v-if="tasksLoading" class="list-loading" aria-label="正在加载报告任务"><i v-for="index in 4" :key="index"></i></div>
      <div v-else class="table-panel">
        <div class="table-meta"><span>共 {{ reportTasks.total }} 个任务</span><span>旧版生成任务只读；新报告由服务申请工作流协作完成。</span></div>
        <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
          <table class="admin-table">
            <thead><tr><th>任务</th><th>用户</th><th>进度</th><th>状态</th><th>错误</th></tr></thead>
            <tbody>
              <tr v-for="task in reportTasks.items" :key="task.task_id">
                <td><strong class="mono-text">{{ task.task_id.slice(0, 12) }}…</strong><small>{{ task.report_id ? `报告 #${task.report_id}` : '尚未生成报告' }} · {{ formatDateTime(task.created_at) }}</small></td>
                <td>{{ task.user_name || `用户 #${task.user_id}` }}</td>
                <td><div class="progress-cell"><span>{{ task.progress }}%</span><i><b :style="{ width: `${task.progress}%` }"></b></i></div></td>
                <td><span :class="['status-badge', `task-${task.status}`]">{{ reportStatusText(task.status) }}</span><small v-if="task.retry_count">第 {{ task.retry_count }} 次重试</small></td>
                <td class="error-cell">{{ task.error || '—' }}</td>
              </tr>
              <tr v-if="!reportTasks.items.length"><td colspan="5" class="empty-cell">暂无报告任务。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination"><span>第 {{ taskPage }} / {{ pageCount(reportTasks.total, taskPageSize) }} 页</span><div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="taskPage <= 1" @click="emit('change-task-page', -1)">上一页</VanButton><VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="taskPage >= pageCount(reportTasks.total, taskPageSize)" @click="emit('change-task-page', 1)">下一页</VanButton></div></div>
      </div>
    </template>
  </section>
</template>
