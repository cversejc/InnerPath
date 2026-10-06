<script setup>
import { Button as VanButton } from 'vant'
import ProfileSummary from '../../../components/ProfileSummary.vue'

defineProps({
  calendarRequests: { type: Array, default: () => [] },
  reports: { type: Array, default: () => [] },
  showForm: { type: Boolean, default: false },
  draft: { type: Object, required: true },
  profile: { type: Object, default: null },
  submitting: { type: Boolean, default: false },
  error: { type: String, default: '' },
  feedback: { type: String, default: '' },
  topicOptions: { type: Array, default: () => [] },
  usageOptions: { type: Array, default: () => [] },
  outcomeOptions: { type: Array, default: () => [] }
})

defineEmits([
  'open',
  'close',
  'go-to-profile',
  'submit',
  'toggle-topic',
  'toggle-outcome'
])

function formatRequestDate(start, end) {
  if (!start || !end) return '未设置周期'
  return `${start} — ${end}`
}

function requestStatusLabel(status) {
  return { processing: '生成中', pending: '旧流程已停用', delivered: '已开放', failed: '生成失败', reviewing: '旧流程已停用', fulfilled: '已开放', rejected: '已失败', cancelled: '已取消' }[status] || status
}
</script>

<template>
  <section class="section-band calendar-request-section">
    <div class="container">
      <div class="calendar-section-heading request-heading">
        <div>
          <p class="section-kicker">CALENDAR REQUEST</p>
          <h2 class="section-title">为下一阶段申请一张日历</h2>
        </div>
        <p class="section-desc">日历会复用你的个人档案，但会根据这一次的周期、用途和决策目标重新制定。</p>
      </div>

      <div v-if="!reports.length" class="calendar-request-cta paper-card report-first-card">
        <div>
          <span class="mini-label">REPORT FIRST</span>
          <h3>先申请并获得已交付报告</h3>
          <p>日历会以你的报告为基础生成。申请报告后，等待咨询师交付，再回来启动日历。</p>
        </div>
        <router-link class="btn-action primary-button" to="/pages/assessment/assessment">申请报告</router-link>
      </div>

      <div v-else-if="!showForm" class="calendar-request-cta paper-card">
        <div>
          <span class="mini-label">DELIVERED REPORT + CURRENT GOAL</span>
          <h3>从已交付报告生成决策日历</h3>
          <p>选择一份报告并说明这 30 天的目标。生成成功后，日历会自动开放使用。</p>
        </div>
        <VanButton type="primary" native-type="button" class="btn-action" @click="$emit('open')">生成新日历</VanButton>
      </div>

      <div v-else class="calendar-request-card paper-card">
        <div class="request-card-head">
          <div>
            <span class="mini-label">CALENDAR GENERATION</span>
            <h3>选择报告并补充本次目标</h3>
          </div>
          <VanButton type="default" plain native-type="button" class="request-close" @click="$emit('close')">收起</VanButton>
        </div>

        <ProfileSummary
          v-if="profile"
          :profile="profile"
          :profile-version="profile.profile_version"
          :last-confirmed-at="profile.profile_last_confirmed_at"
          @edit="$emit('go-to-profile')"
        />
        <div v-if="profile && Number(profile.profile_completion || 0) < 100" class="request-profile-warning" role="alert">
          个人档案的性别和出生日期还未完成，请先补充档案后再提交日历申请。
          <VanButton type="default" plain native-type="button" class="request-profile-link" @click="$emit('go-to-profile')">去完善个人档案</VanButton>
        </div>

        <form class="calendar-request-form" novalidate @submit.prevent="$emit('submit')">
          <div class="request-form-field">
            <label for="calendar-source-report">已交付报告 <span class="required">*</span></label>
            <select id="calendar-source-report" v-model="draft.source_report_id" required>
              <option value="">请选择一份已交付报告</option>
              <option v-for="report in reports" :key="report.id" :value="report.id">{{ report.title }} · {{ report.created_at ? new Date(report.created_at).toLocaleDateString('zh-CN') : '已交付' }}</option>
            </select>
            <small>日历将结合这份报告与下面填写的目标生成。</small>
          </div>

          <div class="request-date-grid">
            <div class="request-form-field">
              <label for="calendar-request-start">开始日期 <span class="required">*</span></label>
              <input id="calendar-request-start" v-model="draft.start_date" type="date" required>
            </div>
            <div class="request-form-field">
              <label for="calendar-request-end">结束日期</label>
              <input id="calendar-request-end" v-model="draft.end_date" type="date" readonly aria-readonly="true">
            </div>
          </div>

          <div class="request-form-field">
            <label for="calendar-request-purpose">日历用途 <span class="required">*</span></label>
            <select id="calendar-request-purpose" v-model="draft.usage_scenario" required>
              <option value="">请选择这张日历主要服务什么</option>
              <option v-for="option in usageOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </div>

          <fieldset class="request-form-field">
            <legend>关注领域 <span class="required">*</span> <small>最多 3 项</small></legend>
            <div class="request-option-grid">
              <VanButton
                v-for="topic in topicOptions"
                :key="topic.value"
                type="default"
                plain
                native-type="button"
                class="request-option"
                :class="{ selected: draft.focus_topics.includes(topic.value) }"
                :aria-pressed="draft.focus_topics.includes(topic.value)"
                @click="$emit('toggle-topic', topic.value)"
              >{{ topic.label }}</VanButton>
            </div>
          </fieldset>

          <div class="request-form-field">
            <label for="calendar-request-goal">当前决策目标 <span class="required">*</span></label>
            <textarea id="calendar-request-goal" v-model="draft.goal" rows="4" maxlength="1000" placeholder="这段周期里，你最希望推进、观察或理清什么？"></textarea>
          </div>

          <fieldset class="request-form-field">
            <legend>期望输出 <span class="required">*</span> <small>至少 1 项，最多 7 项</small></legend>
            <div class="request-check-grid">
              <label v-for="outcome in outcomeOptions" :key="outcome.value" class="request-check-option">
                <input
                  type="checkbox"
                  :checked="draft.expected_outcomes.includes(outcome.value)"
                  @change="$emit('toggle-outcome', outcome.value)"
                >
                <span>{{ outcome.label }}</span>
              </label>
            </div>
          </fieldset>

          <details class="calendar-request-details">
            <summary>补充决策背景（选填）</summary>
            <div class="request-optional-grid">
              <div class="request-form-field field-wide">
                <label for="calendar-request-decision">重要决策描述</label>
                <input id="calendar-request-decision" v-model="draft.decision_description" type="text" maxlength="1000" placeholder="如：是否在本季度接受新的工作机会">
              </div>
              <div class="request-form-field field-wide">
                <label for="calendar-request-additional">补充说明</label>
                <textarea id="calendar-request-additional" v-model="draft.additional_info" rows="3" maxlength="2000" placeholder="只填写与这次日历目标有关的背景"></textarea>
              </div>
            </div>
          </details>

          <p v-if="error" class="request-error" role="alert">{{ error }}</p>
          <p v-if="feedback" class="request-feedback" role="status">{{ feedback }}</p>
          <div class="request-actions">
            <VanButton type="default" plain native-type="button" class="btn-secondary" @click="$emit('close')">取消</VanButton>
            <VanButton type="primary" native-type="submit" class="btn-action" :disabled="submitting" :aria-busy="submitting">{{ submitting ? '正在启动…' : '开始生成日历' }}</VanButton>
          </div>
        </form>
      </div>

      <div v-if="reports.length && calendarRequests.length" class="calendar-request-history">
        <div class="history-heading"><span class="mini-label">GENERATION HISTORY</span><strong>日历生成记录</strong></div>
        <div class="request-history-list">
          <article v-for="item in calendarRequests" :key="item.id" class="request-history-item">
            <div><strong>{{ formatRequestDate(item.start_date, item.end_date) }}</strong><span>{{ item.goal }}</span></div>
            <span class="request-status" :class="`status-${item.status}`">{{ requestStatusLabel(item.status) }}{{ item.progress && item.status === 'processing' ? ` · ${item.progress}%` : '' }}</span>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>
