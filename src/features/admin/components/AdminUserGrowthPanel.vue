<script setup>
import { computed } from 'vue'

const props = defineProps({
  dashboardRange: { type: String, default: '30d' },
  summary: { type: Object, default: null }
})

const periodLabel = computed(() => ({ '7d': '7 天', '30d': '30 天', '90d': '90 天' }[props.dashboardRange] || '本期'))

const conversionRows = computed(() => {
  const summary = props.summary || {}
  return [
    { key: 'profile', label: '完成基础资料', count: summary.profile_completed_users, rate: summary.profile_completion_rate_percent },
    { key: 'request', label: '提交服务申请', count: summary.applicant_users, rate: summary.applicant_rate_percent },
    { key: 'delivered', label: '获得服务交付', count: summary.delivered_users, rate: summary.registered_users ? Number((summary.delivered_users * 100 / summary.registered_users).toFixed(1)) : null }
  ]
})

function formatRate(value) {
  return value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`
}

function barWidth(value) {
  const rate = Number(value)
  return `${Number.isFinite(rate) ? Math.max(0, Math.min(100, rate)) : 0}%`
}
</script>

<template>
  <article v-if="summary" class="dashboard-panel user-growth-panel" aria-labelledby="user-growth-title">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">CONVERSION / RETURN</p>
        <h3 id="user-growth-title">用户转化与留存</h3>
      </div>
      <span class="panel-note">{{ summary.range_start }} 至 {{ summary.range_end }}</span>
    </div>

    <p class="user-growth-definition">新注册用户按本期创建时间统计；资料按当前状态统计，申请和交付统计至本期末。总体人数去重，用户可能同时使用报告与日历。</p>

    <dl class="user-growth-metrics">
      <div><dt>新注册用户</dt><dd>{{ summary.registered_users }}</dd></div>
      <div><dt>完整基础资料</dt><dd>{{ summary.profile_completed_users }} <small>{{ formatRate(summary.profile_completion_rate_percent) }}</small></dd></div>
      <div><dt>提交过服务申请</dt><dd>{{ summary.applicant_users }} <small>{{ formatRate(summary.applicant_rate_percent) }}</small></dd></div>
      <div><dt>获得过服务交付</dt><dd>{{ summary.delivered_users }} <small>{{ formatRate(conversionRows[2].rate) }}</small></dd></div>
    </dl>

    <div class="user-growth-content">
      <section class="user-growth-conversion" aria-labelledby="user-growth-conversion-title">
        <div class="user-growth-heading"><h4 id="user-growth-conversion-title">注册用户进展</h4><span>各项占新注册用户</span></div>
        <div class="user-growth-bars">
          <div v-for="row in conversionRows" :key="row.key" class="user-growth-bar-row">
            <div><span>{{ row.label }}</span><b>{{ row.count }} <small>{{ formatRate(row.rate) }}</small></b></div>
            <span class="user-growth-track"><i :style="{ width: barWidth(row.rate) }"></i></span>
          </div>
        </div>
      </section>

      <section class="user-growth-return" aria-labelledby="user-growth-return-title">
        <div class="user-growth-heading"><h4 id="user-growth-return-title">登录回访</h4><span>近 {{ periodLabel }}</span></div>
        <div class="user-growth-return-metric">
          <strong>{{ summary.returning_users }}</strong>
          <span>老用户在本期登录<br>占存量有效账号 {{ formatRate(summary.existing_user_login_rate_percent) }}</span>
        </div>
        <div class="user-growth-return-scale" role="img" :aria-label="`本期存量用户登录回访率 ${formatRate(summary.existing_user_login_rate_percent)}`">
          <i :style="{ width: barWidth(summary.existing_user_login_rate_percent) }"></i>
        </div>
        <p class="user-growth-return-note">统计周期内登录且当前有效的存量账号 ÷ 周期开始前已注册且当前有效账号（{{ summary.returning_users }} / {{ summary.existing_user_base }}）。这是区间回访率，不代表注册后第 7/30 天留存。</p>
        <p class="user-growth-active-count">本期登录的当前有效用户：<strong>{{ summary.active_login_users }}</strong></p>
      </section>
    </div>

    <section class="user-growth-channels" aria-labelledby="user-growth-channels-title">
      <div class="user-growth-heading"><h4 id="user-growth-channels-title">报告与日历申请转化</h4><span>本期新注册用户中的去重人数</span></div>
      <div class="admin-table-wrap user-growth-table-wrap" tabindex="0" aria-label="报告与日历申请转化表，可横向滚动查看">
        <table class="admin-table user-growth-table">
          <thead><tr><th>服务</th><th>提交申请</th><th>已交付</th><th>申请到交付</th></tr></thead>
          <tbody>
            <tr v-for="channel in summary.by_service" :key="channel.key">
              <th scope="row">{{ channel.label }}</th>
              <td>{{ channel.applicant_users }}</td>
              <td>{{ channel.delivered_users }}</td>
              <td>{{ formatRate(channel.delivery_rate_percent) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </article>
</template>
