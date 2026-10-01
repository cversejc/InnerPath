<script setup>
import {
  actionLabel,
  distributionTotal,
  distributionWidth,
  formatDate,
  formatDateTime,
  resourceLabel
} from '../formatters.js'

defineProps({
  autoRefresh: { type: Boolean, default: false },
  chartGridLines: { type: Array, default: () => [] },
  dashboard: { type: Object, default: null },
  dashboardLoading: { type: Boolean, default: false },
  dashboardRange: { type: String, required: true },
  dashboardRanges: { type: Array, default: () => [] },
  distributionGroups: { type: Array, default: () => [] },
  metricCards: { type: Array, default: () => [] },
  trendSeries: { type: Array, default: () => [] },
  trendTicks: { type: Array, default: () => [] }
})

defineEmits(['auto-refresh-change', 'change-range', 'go-from-alert', 'switch-tab'])
</script>

<template>
  <section class="dashboard-view">
    <div class="dashboard-toolbar">
      <div>
        <p class="eyebrow">GLOBAL SIGNALS</p>
        <h2>全局数据</h2>
        <p v-if="dashboard">{{ formatDate(dashboard.start_date) }} — {{ formatDate(dashboard.end_date) }} · {{ dashboard.timezone }}</p>
      </div>
      <div class="toolbar-controls">
        <div class="range-switch" role="group" aria-label="数据范围">
          <button
            v-for="range in dashboardRanges"
            :key="range.id"
            type="button"
            :class="{ active: dashboardRange === range.id }"
            :aria-pressed="dashboardRange === range.id"
            @click="$emit('change-range', range.id)"
          >{{ range.label }}</button>
        </div>
        <label class="auto-refresh"><input :checked="autoRefresh" type="checkbox" @change="$emit('auto-refresh-change', $event.target.checked)"> <span>60 秒自动刷新</span></label>
      </div>
    </div>

    <div v-if="dashboardLoading && !dashboard" class="dashboard-skeleton">
      <div v-for="index in 6" :key="index" class="skeleton-block"></div>
    </div>

    <template v-else-if="dashboard">
      <div class="metric-grid">
        <article v-for="metric in metricCards" :key="metric.key" class="metric-card" :class="`metric-${metric.tone}`">
          <div class="metric-top"><span>{{ metric.label }}</span><b>{{ metric.mark }}</b></div>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.caption }}</small>
        </article>
      </div>

      <div class="dashboard-grid">
        <article class="dashboard-panel trend-panel">
          <div class="panel-heading"><div><p class="eyebrow">RHYTHM / {{ dashboardRange.toUpperCase() }}</p><h3>业务流入趋势</h3></div><span class="panel-note">按上海时区聚合</span></div>
          <div class="trend-legend"><span v-for="series in trendSeries" :key="series.key"><i :style="{ background: series.color }"></i>{{ series.label }}</span></div>
          <div class="trend-chart" aria-label="业务流入趋势图">
            <svg viewBox="0 0 760 250" role="img" aria-labelledby="trend-title">
              <title id="trend-title">用户、报告、预约和行动记录趋势</title>
              <line v-for="line in chartGridLines" :key="line" x1="28" :x2="736" :y1="line" :y2="line" class="chart-grid-line" />
              <polyline v-for="series in trendSeries" :key="series.key" :points="series.points" :stroke="series.color" class="trend-line" />
              <g v-for="tick in trendTicks" :key="tick.index">
                <line :x1="tick.x" :x2="tick.x" y1="214" y2="220" class="chart-tick" />
                <text :x="tick.x" y="241" text-anchor="middle" class="chart-label">{{ tick.label }}</text>
              </g>
            </svg>
          </div>
        </article>

        <article class="dashboard-panel alert-panel">
          <div class="panel-heading"><div><p class="eyebrow">ATTENTION REQUIRED</p><h3>待处理事项</h3></div><span class="alert-count">{{ dashboard.alerts.length }}</span></div>
          <div v-if="dashboard.alerts.length" class="alert-list">
            <button v-for="alert in dashboard.alerts" :key="alert.key" type="button" class="alert-item" @click="$emit('go-from-alert', alert)">
              <span :class="['alert-mark', `alert-${alert.level}`]"></span><span><strong>{{ alert.label }}</strong><small>{{ alert.count }} 项需要关注</small></span><IconMark name="arrow" class="alert-arrow" />
            </button>
          </div>
          <div v-else class="quiet-state"><IconMark name="spark" /><p>目前没有需要立即处理的事项。</p></div>
        </article>

        <article class="dashboard-panel distribution-panel">
          <div class="panel-heading"><div><p class="eyebrow">COMPOSITION</p><h3>结构分布</h3></div></div>
          <div class="distribution-columns">
            <div v-for="group in distributionGroups" :key="group.key" class="distribution-group">
              <div class="distribution-title"><span>{{ group.label }}</span><small>{{ distributionTotal(group.items) }}</small></div>
              <div v-for="item in group.items" :key="item.key" class="distribution-row">
                <div><span>{{ item.label }}</span><b>{{ item.value }}</b></div><span class="distribution-track"><i :style="{ width: `${distributionWidth(item, group.items)}%` }"></i></span>
              </div>
            </div>
          </div>
        </article>

        <article class="dashboard-panel activity-panel">
          <div class="panel-heading"><div><p class="eyebrow">TRACE / LATEST 8</p><h3>最近活动</h3></div><button type="button" class="panel-link" @click="$emit('switch-tab', 'logs')"><span>查看日志</span><IconMark name="arrow" /></button></div>
          <div v-if="dashboard.recent_activity.length" class="activity-list">
            <div v-for="activity in dashboard.recent_activity" :key="activity.id" class="activity-item"><span class="activity-dot"></span><div><strong>{{ actionLabel(activity.action) }}</strong><p>{{ activity.target_user_name || activity.actor_name || '系统' }} · {{ resourceLabel(activity.resource_type) }}</p></div><time>{{ formatDateTime(activity.created_at) }}</time></div>
          </div>
          <div v-else class="quiet-state"><IconMark name="reports" /><p>还没有可展示的活动记录。</p></div>
        </article>

        <article class="dashboard-panel course-panel">
          <div class="panel-heading"><div><p class="eyebrow">LEARNING / COURSE HEALTH</p><h3>课程学习概况</h3></div><span>按课程</span></div>
          <div v-if="dashboard.course_stats?.length" class="course-stats-list">
            <div v-for="course in dashboard.course_stats" :key="course.course_id" class="course-stat-row">
              <div><strong>{{ course.title }}</strong><small>{{ course.enrolled_count }} 人参与 · {{ course.active_count }} 人学习中</small></div>
              <div class="course-stat-numbers"><b>{{ course.completion_rate }}%</b><span>完成</span><small>均值 {{ course.average_progress }}%</small></div>
            </div>
          </div>
          <div v-else class="quiet-state"><IconMark name="book" /><p>暂无线课程参与数据。</p></div>
        </article>
      </div>
    </template>
  </section>
</template>
