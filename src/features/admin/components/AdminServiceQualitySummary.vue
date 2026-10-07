<script setup>
import { computed } from 'vue'

const props = defineProps({
  periodDays: { type: Number, default: 30 },
  summary: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const emit = defineEmits(['change-period'])
const periods = [7, 30, 90]
const peakWeeklyCount = computed(() => Math.max(1, ...(props.summary?.weekly_trend || []).map(item => item.feedback_count)))

function formatRating(value) {
  return value === null || value === undefined ? '—' : Number(value).toFixed(1)
}

function formatRate(value) {
  return value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`
}

function formatHours(value) {
  if (value === null || value === undefined) return '—'
  return value >= 24 ? `${(value / 24).toFixed(1)} 天` : `${value} 小时`
}

function weekBarHeight(item) {
  if (!item.feedback_count) return '0%'
  return `${Math.max(8, (item.feedback_count / peakWeeklyCount.value) * 100)}%`
}

function formatWeek(value) {
  return value ? `${String(value).slice(5, 7)}/${String(value).slice(8, 10)}` : '—'
}
</script>

<template>
  <section class="service-quality-summary" aria-labelledby="service-quality-summary-title" :aria-busy="loading">
    <div class="quality-summary-heading">
      <div>
        <p class="eyebrow">FEEDBACK ANALYSIS</p>
        <h3 id="service-quality-summary-title">服务质量分析</h3>
        <p v-if="summary">{{ summary.range_start }} 至 {{ summary.range_end }} · 结案时长仅统计已结案反馈，从提交到结案</p>
      </div>
      <div class="quality-summary-period" role="group" aria-label="服务质量统计周期">
        <button v-for="days in periods" :key="days" type="button" :aria-pressed="periodDays === days" :disabled="loading" @click="emit('change-period', days)">{{ days }} 天</button>
      </div>
    </div>

    <p v-if="error" class="quality-summary-error" role="alert">{{ error }}<span v-if="summary">当前仍显示上次成功加载的数据。</span></p>
    <p v-if="loading" class="quality-summary-loading" role="status" aria-live="polite">正在更新服务质量数据…</p>
    <p v-if="!summary && !loading && !error" class="quality-summary-empty">暂无汇总数据。</p>

    <template v-if="summary">
      <dl class="quality-summary-metrics">
        <div><dt>反馈总量</dt><dd>{{ summary.totals.feedback_count }}</dd></div>
        <div><dt>平均评分 <small>({{ summary.totals.rated_count }} 条)</small></dt><dd>{{ formatRating(summary.totals.average_rating) }}<small v-if="summary.totals.average_rating !== null"> / 5</small></dd></div>
        <div><dt>投诉</dt><dd>{{ summary.totals.complaint_count }}</dd></div>
        <div><dt>结案率</dt><dd>{{ formatRate(summary.totals.resolution_rate_percent) }}</dd></div>
        <div><dt>结案时长 P50 / P90</dt><dd>{{ formatHours(summary.totals.resolution_p50_hours) }}<small> / {{ formatHours(summary.totals.resolution_p90_hours) }}</small></dd></div>
      </dl>

      <section class="quality-weekly-section" aria-labelledby="quality-weekly-title">
        <div class="quality-subsection-heading"><h4 id="quality-weekly-title">每周反馈与投诉</h4><span>柱高表示反馈量，文字标出投诉数</span></div>
        <div class="quality-weekly-chart" role="img" :aria-label="`近 ${periodDays} 天每周反馈与投诉量`">
          <div v-for="week in summary.weekly_trend" :key="week.week_start" class="quality-week-column" :aria-label="`${formatWeek(week.week_start)}：反馈 ${week.feedback_count} 条，投诉 ${week.complaint_count} 条`">
            <span class="quality-week-count">{{ week.feedback_count }}</span>
            <div class="quality-week-track"><i :style="{ height: weekBarHeight(week) }"></i></div>
            <time>{{ formatWeek(week.week_start) }}</time>
            <small>投诉 {{ week.complaint_count }}</small>
          </div>
        </div>
      </section>

      <div class="quality-breakdown-grid">
        <section class="quality-breakdown" aria-labelledby="quality-service-title">
          <div class="quality-subsection-heading"><h4 id="quality-service-title">按服务类型</h4></div>
          <div class="quality-table-wrap" tabindex="0" aria-label="服务类型质量指标">
            <table>
              <thead><tr><th>服务</th><th>反馈</th><th>平均评分</th><th>投诉</th><th>结案率</th><th>结案时长 P50 / P90</th></tr></thead>
              <tbody>
                <tr v-for="group in summary.by_service" :key="group.key">
                  <th scope="row">{{ group.label }}</th><td>{{ group.feedback_count }}</td><td>{{ formatRating(group.average_rating) }} <small v-if="group.rated_count">({{ group.rated_count }})</small></td><td>{{ group.complaint_count }}</td><td>{{ formatRate(group.resolution_rate_percent) }}</td><td>{{ formatHours(group.resolution_p50_hours) }} / {{ formatHours(group.resolution_p90_hours) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="quality-breakdown" aria-labelledby="quality-specialty-title">
          <div class="quality-subsection-heading"><h4 id="quality-specialty-title">按咨询方向</h4></div>
          <div class="quality-table-wrap" tabindex="0" aria-label="咨询方向质量指标">
            <table>
              <thead><tr><th>方向</th><th>反馈</th><th>平均评分</th><th>投诉</th><th>结案率</th><th>结案时长 P50 / P90</th></tr></thead>
              <tbody>
                <tr v-for="group in summary.by_specialty" :key="group.key">
                  <th scope="row">{{ group.label }}</th><td>{{ group.feedback_count }}</td><td>{{ formatRating(group.average_rating) }} <small v-if="group.rated_count">({{ group.rated_count }})</small></td><td>{{ group.complaint_count }}</td><td>{{ formatRate(group.resolution_rate_percent) }}</td><td>{{ formatHours(group.resolution_p50_hours) }} / {{ formatHours(group.resolution_p90_hours) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section class="quality-breakdown" aria-labelledby="quality-consultant-title">
        <div class="quality-subsection-heading"><h4 id="quality-consultant-title">咨询师名下反馈</h4><span>协作申请分别计入各专业负责人</span></div>
        <div class="quality-table-wrap" tabindex="0" aria-label="咨询师反馈质量指标">
          <table>
            <thead><tr><th>咨询师</th><th>反馈</th><th>平均评分</th><th>投诉</th></tr></thead>
            <tbody>
              <tr v-for="group in summary.by_consultant" :key="group.consultant_id">
                <th scope="row">{{ group.consultant_name }}</th><td>{{ group.feedback_count }}</td><td>{{ formatRating(group.average_rating) }} <small v-if="group.rated_count">({{ group.rated_count }})</small></td><td>{{ group.complaint_count }}</td>
              </tr>
              <tr v-if="!summary.by_consultant.length"><td colspan="4" class="quality-no-data">所选周期没有可归属到咨询师的报告反馈。</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </section>
</template>
