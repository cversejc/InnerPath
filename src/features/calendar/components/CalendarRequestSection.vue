<script setup>
import { onMounted, ref } from 'vue'
import { Button as VanButton } from 'vant'
import ProfileSummary from '../../../components/ProfileSummary.vue'
import ServiceFeedbackControl from '../../service-feedback/components/ServiceFeedbackControl.vue'
import { getMyServiceFeedback } from '../../service-feedback/api.js'
import { calendarGenerationText } from '../generation-progress.js'
import { CALENDAR_REQUEST_STATUS_LABELS } from '../../../utils/displayLabels.js'

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
  'go-to-reports',
  'submit',
  'retry',
  'toggle-topic',
  'toggle-outcome'
])

function formatRequestDate(start, end) {
  if (!start || !end) return '未设置周期'
  return `${start} — ${end}`
}

function requestStatusLabel(status) {
  return {
    generating: 'AI 生成中',
    queued: '排队中',
    processing: 'AI 生成中',
    fulfilled: '已生成并交付',
    delivered: '已开放使用',
    failed: '生成失败',
    pending: '历史申请',
    accepted: '旧流程已停用',
    submitted: '旧流程已停用',
    reviewing: '历史申请',
    rejected: '已退回',
    cancelled: '已取消'
  }[status] || CALENDAR_REQUEST_STATUS_LABELS[status] || status
}

const feedbackByCalendarRequestId = ref({})
const feedbackReady = ref(false)
const feedbackLoadError = ref(false)

onMounted(async () => {
  try {
    const response = await getMyServiceFeedback()
    feedbackByCalendarRequestId.value = Object.fromEntries(
      (response.items || [])
        .filter(item => item.calendar_request_id)
        .map(item => [item.calendar_request_id, item])
    )
    feedbackReady.value = true
  } catch {
    feedbackReady.value = false
    feedbackLoadError.value = true
  }
})

function saveCalendarFeedback(requestId, feedback) {
  feedbackByCalendarRequestId.value = {
    ...feedbackByCalendarRequestId.value,
    [requestId]: feedback
  }
}
</script>

<template>
  <section class="section-band calendar-request-section">
    <div class="container">
      <div class="calendar-section-heading request-heading">
        <div>
          <p class="section-kicker">CALENDAR REQUEST</p>
          <h2 class="section-title">基于人生说明书生成决策日历</h2>
        </div>
        <p class="section-desc">日历以已交付报告为依据，结合你选择的周期与目标生成；完成后自动交付，无需人工审核。</p>
      </div>

      <div v-if="!reports.length" class="calendar-request-cta paper-card report-first-card">
        <div>
          <span class="mini-label">DELIVERED REPORT + 30 DAYS</span>
          <h3>把报告里的方向放进接下来的日常</h3>
          <p>请从已交付的人生说明书进入，日历会沿用那份报告的内容和你本次填写的目标。</p>
        </div>
        <VanButton v-if="draft.source_report_id" type="primary" native-type="button" class="btn-action" @click="$emit('open')">{{ feedback ? '重新生成日历' : '继续设置日历' }}</VanButton>
        <VanButton v-else type="primary" native-type="button" class="btn-action" @click="$emit('go-to-reports')">查看已交付报告</VanButton>
        <p v-if="feedback" class="request-feedback" role="status">{{ feedback }}</p>
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
            <span class="mini-label">REPORT-BASED GENERATION</span>
            <h3>设置接下来 30 天的使用目标</h3>
          </div>
          <VanButton type="default" plain native-type="button" class="request-close" @click="$emit('close')">收起</VanButton>
        </div>

        <p v-if="draft.source_report_id" class="calendar-source-report">
          来源报告 #{{ draft.source_report_id }} · 生成后自动交付
        </p>

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
              <label for="calendar-request-end">结束日期 <span class="required">*</span></label>
              <input id="calendar-request-end" v-model="draft.end_date" type="date" required readonly aria-readonly="true">
              <small>周期必须连续 30 天</small>
            </div>
          </div>

          <div class="request-form-field">
            <label for="calendar-request-purpose">日历用途 <span class="required">*</span></label>
            <select id="calendar-request-purpose" v-model="draft.usage_scenario" required>
              <option value="">请选择这张日历主要服务什么</option>
              <option v-for="option in usageOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </div>

          <div class="request-form-field">
            <label for="calendar-request-availability">每天可投入时间 <span class="required">*</span></label>
            <div class="availability-input-row">
              <input id="calendar-request-availability" v-model.number="draft.available_minutes_per_day" type="number" min="5" max="480" step="5" required>
              <span>分钟</span>
            </div>
            <small>日历会按这段时间安排报告中的行动练习；默认 30 分钟。</small>
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
            <VanButton type="primary" native-type="submit" class="btn-action" :disabled="submitting" :loading="submitting" :aria-busy="submitting">{{ submitting ? '正在提交…' : '生成30天日历' }}</VanButton>
          </div>
        </form>
      </div>

      <div v-if="reports.length && calendarRequests.length" class="calendar-request-history">
        <div class="history-heading"><span class="mini-label">GENERATION HISTORY</span><strong>日历生成记录</strong></div>
        <div class="request-history-list">
          <article v-for="item in calendarRequests" :key="item.id" class="request-history-item">
            <div><strong>{{ formatRequestDate(item.start_date, item.end_date) }}</strong><span>{{ item.goal }}</span></div>
            <span class="request-status" :class="`status-${item.status}`" role="status">{{ calendarGenerationText(item) }}<small v-if="item.calendar_id"> · 日历 #{{ item.calendar_id }}</small></span>
            <VanButton v-if="item.status === 'failed'" plain native-type="button" :disabled="submitting" @click="$emit('retry', item.id)">重试生成</VanButton>
            <ServiceFeedbackControl
              v-if="feedbackReady && ['fulfilled', 'delivered'].includes(item.status) && item.calendar_id"
              class="calendar-feedback-control"
              service-type="calendar"
              :source-id="item.id"
              :existing="feedbackByCalendarRequestId[item.id] || null"
              @submitted="saveCalendarFeedback(item.id, $event)"
            />
            <p v-else-if="feedbackLoadError && ['fulfilled', 'delivered'].includes(item.status) && item.calendar_id" class="calendar-feedback-load-error" role="status">反馈状态暂时无法读取，请稍后刷新。</p>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>
