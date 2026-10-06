<script setup>
import { computed } from 'vue'
import { Button as VanButton } from 'vant'

const props = defineProps({
  dashboardRange: { type: String, default: '30d' },
  summary: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['retry'])

const periodLabel = computed(() => ({ '7d': '7 天', '30d': '30 天', '90d': '90 天' }[props.dashboardRange] || '本期'))
const terminalRuns = computed(() => (props.summary?.completed_runs || 0) + (props.summary?.failed_runs || 0))

function formatRate(value) {
  return value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`
}

function formatDuration(value) {
  if (value === null || value === undefined) return '—'
  if (value < 1) return `${Math.round(value * 60)} 分钟`
  return `${Number(value).toFixed(1)} 小时`
}
</script>

<template>
  <article v-if="!summary" class="dashboard-panel generation-observability-panel generation-observability-unavailable" role="status" aria-labelledby="generation-observability-unavailable-title">
    <div>
      <h3 id="generation-observability-unavailable-title">生成链路观测暂不可用</h3>
      <p>其他总览数据仍可查看。刷新后可重新读取运行与队列状态。</p>
    </div>
    <VanButton class="secondary-button compact-button generation-retry-button" type="default" plain native-type="button" :disabled="loading" :loading="loading" loading-text="刷新中…" :aria-busy="loading" @click="emit('retry')">重试</VanButton>
  </article>

  <article v-else class="dashboard-panel generation-observability-panel" aria-labelledby="generation-observability-title">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">AI / WORKFLOW</p>
        <h3 id="generation-observability-title">生成链路观测</h3>
      </div>
      <span class="panel-note">{{ summary.range_start }} 至 {{ summary.range_end }}</span>
    </div>

    <dl class="generation-health-metrics">
      <div><dt>当前待执行 / 运行中</dt><dd>{{ summary.active_runs }}</dd></div>
      <div><dt>本期 AI 运行</dt><dd>{{ terminalRuns }} <small>完成 {{ summary.completed_runs }} · 失败 {{ summary.failed_runs }}</small></dd></div>
      <div><dt>本期运行成功率</dt><dd>{{ formatRate(summary.success_rate_percent) }}</dd></div>
      <div><dt>本期 AI 重试</dt><dd>{{ summary.retry_attempts }}</dd></div>
      <div><dt>待投递事件</dt><dd>{{ summary.outbox_pending }} <small>超 5 分钟 {{ summary.outbox_pending_over_5m }}</small></dd></div>
    </dl>

    <p class="generation-observability-definition">完成、失败、重试和耗时按完成时间计入所选周期；运行中任务及报告、日历和投递队列按当前状态统计。此处仅显示任务元数据，不含用户输入、模型输出或原始异常内容。</p>

    <section class="generation-stage-section" aria-labelledby="generation-stage-title">
      <div class="generation-section-heading"><h4 id="generation-stage-title">AI 阶段</h4><span>运行中为当前状态；完成、失败、重试与耗时按本期统计</span></div>
      <div class="admin-table-wrap generation-stage-table-wrap" tabindex="0" aria-label="AI 生成阶段运行情况，可横向滚动查看">
        <table class="admin-table generation-stage-table">
          <thead><tr><th>阶段</th><th>当前待执行 / 运行中</th><th>完成</th><th>失败</th><th>重试</th><th>运行耗时 P50 / P90</th></tr></thead>
          <tbody>
            <tr v-for="stage in summary.stages" :key="stage.stage_key">
              <th scope="row">{{ stage.label }}</th>
              <td>{{ stage.active_runs }}</td>
              <td>{{ stage.completed_runs }}</td>
              <td>{{ stage.failed_runs }}</td>
              <td>{{ stage.retry_attempts }}</td>
              <td>{{ formatDuration(stage.p50_duration_hours) }} / {{ formatDuration(stage.p90_duration_hours) }}</td>
            </tr>
            <tr v-if="!summary.stages.length"><td colspan="6" class="empty-cell">近 {{ periodLabel }} 没有 AI 阶段运行记录。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="generation-queue-status">
      <section aria-labelledby="generation-report-case-title">
        <div class="generation-section-heading"><h4 id="generation-report-case-title">报告流程</h4><span>全部实例当前状态</span></div>
        <dl>
          <div><dt>待启动</dt><dd>{{ summary.report_cases_created }}</dd></div>
          <div><dt>处理中</dt><dd>{{ summary.report_cases_active }}</dd></div>
          <div><dt>受阻</dt><dd>{{ summary.report_cases_blocked }}</dd></div>
          <div><dt>待交付</dt><dd>{{ summary.report_cases_ready_to_deliver }}</dd></div>
          <div><dt>已交付</dt><dd>{{ summary.report_cases_delivered }}</dd></div>
          <div><dt>已取消</dt><dd>{{ summary.report_cases_cancelled }}</dd></div>
        </dl>
      </section>
      <section aria-labelledby="generation-calendar-title">
        <div class="generation-section-heading"><h4 id="generation-calendar-title">日历生成</h4><span>全部请求当前状态</span></div>
        <dl>
          <div><dt>排队</dt><dd>{{ summary.calendar_queued }}</dd></div>
          <div><dt>生成中</dt><dd>{{ summary.calendar_generating }}</dd></div>
          <div><dt>失败</dt><dd>{{ summary.calendar_failed }}</dd></div>
          <div><dt>已交付</dt><dd>{{ summary.calendar_delivered }}</dd></div>
          <div><dt>生成中超 45 分钟</dt><dd>{{ summary.calendar_stalled }}</dd></div>
        </dl>
      </section>
      <section aria-labelledby="generation-outbox-title">
        <div class="generation-section-heading"><h4 id="generation-outbox-title">事件投递</h4><span>当前队列</span></div>
        <dl>
          <div><dt>待投递</dt><dd>{{ summary.outbox_pending }}</dd></div>
          <div><dt>超 5 分钟</dt><dd>{{ summary.outbox_pending_over_5m }}</dd></div>
          <div><dt>已投递</dt><dd>{{ summary.outbox_published }}</dd></div>
          <div><dt>投递失败</dt><dd>{{ summary.outbox_failed }}</dd></div>
          <div><dt>待投递重试</dt><dd>{{ summary.outbox_retry_attempts }}</dd></div>
        </dl>
      </section>
    </div>
  </article>
</template>
