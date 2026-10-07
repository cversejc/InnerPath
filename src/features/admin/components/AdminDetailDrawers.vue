<script setup>
import { computed, ref, watch } from 'vue'
import { Button as VanButton } from 'vant'
import AdminIconButton from './AdminIconButton.vue'
import CalendarReadOnlyPreview from './CalendarReadOnlyPreview.vue'
import ReportContent from '../../reports/components/ReportContent.vue'
import { normalizeReportData, parseLegacyReportContent } from '../../reports/report-content.js'
import { shanghaiYear } from '../../../utils/dateTime.js'
import { consultationTypeLabel } from '../../service-requests/formatters.js'
import {
  actionLabel,
  calendarStatusText,
  decisionStatusText,
  formatDate,
  formatDateTime,
  prettyJson,
  calendarRequestStatusText,
  reportStatusText,
  resourceLabel,
  roleText,
  serviceRequestStatusText
} from '../formatters.js'
import {
  EXPECTED_OUTCOME_LABELS,
  PROFILE_VALUE_LABELS,
  USAGE_SCENARIO_LABELS,
  USER_TYPE_LABELS,
  firstNonEmptyArray,
  labelList,
  topicLabel,
  usageScenarioLabel
} from '../../../utils/displayLabels.js'

const props = defineProps({
  decisionStatusText: { type: Function, default: decisionStatusText },
  detailUser: { type: Object, default: null },
  logDetail: { type: Object, default: null },
  profileSaving: { type: Boolean, default: false },
  reportDetail: { type: Object, default: null },
  userEdit: { type: Object, required: true },
  userPanelData: { type: Object, required: true },
  userPanelLoading: { type: Boolean, default: false },
  userPanelTab: { type: String, default: 'profile' },
  userPanelTabs: { type: Array, default: () => [] },
  userSummary: { type: Object, default: null },
  timelineError: { type: String, default: '' },
  timelineLoading: { type: Boolean, default: false }
})

const emit = defineEmits([
  'close-log',
  'close-report',
  'close-user',
  'close-active',
  'open-calendar-for-user',
  'open-log',
  'open-report',
  'retry-user-timeline',
  'save-user-profile',
  'set-user-panel-tab'
])

const userDrawer = ref(null)
const reportDrawer = ref(null)
const logDrawer = ref(null)
const reportView = ref('user')
const calendarPreviewId = ref(null)
const currentYear = shanghaiYear()

const reportPreview = computed(() => {
  if (!props.reportDetail) return null
  const report = normalizeReportData(props.reportDetail)
  let foundationData = report.contentPayload?.foundation_data || null
  let contentWithoutFoundation = ''
  if (report.aiGeneratedContent) {
    const parsed = parseLegacyReportContent(report.aiGeneratedContent)
    foundationData = foundationData || parsed.foundationData
    contentWithoutFoundation = parsed.contentWithoutFoundation
  }
  return { report, foundationData, contentWithoutFoundation }
})

const selectedCalendarPreview = computed(() => (props.userPanelData.calendars || [])
  .find(calendar => calendar.id === calendarPreviewId.value) || null)

watch(() => props.reportDetail?.id, () => { reportView.value = 'user' })
watch(() => props.detailUser?.id, () => { calendarPreviewId.value = null })

function openCalendarPreview(calendar) {
  calendarPreviewId.value = calendarPreviewId.value === calendar.id ? null : calendar.id
}

function displayValue(value) {
  const labels = { ...PROFILE_VALUE_LABELS, ...USER_TYPE_LABELS, ...USAGE_SCENARIO_LABELS }
  if (Array.isArray(value)) return value.length ? value.map(item => labels[item] || item).join('、') : '未填写'
  return value === null || value === undefined || value === '' ? '未填写' : labels[value] || String(value)
}

function genderLabel(value) {
  return { male: '男', female: '女' }[value] || '未填写'
}

function requestTopicValues(payload) {
  return firstNonEmptyArray(
    payload?.selected_topics,
    payload?.context?.focus_topics,
    payload?.context?.selected_topics
  )
}

function requestExpectedOutcomeValues(payload) {
  return firstNonEmptyArray(payload?.context?.expected_outcomes, payload?.expected_outcomes)
}

function birthDateLabel(user) {
  if (!user.birth_year || !user.birth_month || !user.birth_day) return '未填写'
  const calendar = user.calendar_type === 'lunar' ? '农历' : '公历'
  const leap = user.birth_is_leap_month ? '闰' : ''
  return `${calendar} ${user.birth_year} 年 ${leap}${user.birth_month} 月 ${user.birth_day} 日`
}

function birthTimeLabel(user) {
  if (user.birth_hour === null || user.birth_hour === undefined) return '未填写'
  const minute = user.birth_minute === null || user.birth_minute === undefined ? '??' : String(user.birth_minute).padStart(2, '0')
  return `${String(user.birth_hour).padStart(2, '0')}:${minute}`
}

function precisionLabel(value) {
  return { exact: '准确', approximate: '大致', unknown: '未知' }[value] || '未知'
}

function getDrawer(name) {
  return { userDrawer, reportDrawer, logDrawer }[name]?.value || null
}

function handleDrawerKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close-active')
    return
  }
  if (event.key !== 'Tab') return

  const drawer = event.currentTarget
  const focusables = [...drawer.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')]
    .filter(element => element.offsetParent !== null)
  if (!focusables.length) {
    event.preventDefault()
    drawer.focus()
    return
  }
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

defineExpose({ getDrawer })
</script>

<template>
  <div v-if="detailUser" class="drawer-layer" @click.self="$emit('close-user')">
    <aside ref="userDrawer" class="drawer user-drawer" role="dialog" aria-modal="true" aria-labelledby="user-detail-title" tabindex="-1" @keydown="handleDrawerKeydown">
      <div class="drawer-header"><div class="person-cell"><span class="avatar-mark large">{{ detailUser.name?.slice(0, 1) || '人' }}</span><span><p class="eyebrow">USER #{{ detailUser.id }}</p><h2 id="user-detail-title">{{ detailUser.name }}</h2><small>{{ detailUser.phone }}</small></span></div><AdminIconButton class="drawer-close" icon="close" label="关闭用户详情" @click="$emit('close-user')" /></div>
      <div class="drawer-tabs"><button v-for="tab in userPanelTabs" :key="tab.id" type="button" :class="{ active: userPanelTab === tab.id }" @click="$emit('set-user-panel-tab', tab.id)">{{ tab.label }}</button></div>
      <div v-if="userPanelLoading" class="drawer-loading" role="status" aria-live="polite">正在整理用户资料…</div>
      <div v-else class="drawer-body">
        <section v-if="userPanelTab === 'overview'" class="drawer-section">
          <div class="profile-summary"><div><span>申请</span><strong>{{ (userSummary?.summary?.report_request_count || 0) + (userSummary?.summary?.calendar_request_count || 0) }}</strong></div><div><span>报告</span><strong>{{ userSummary?.summary?.report_count ?? '—' }}</strong></div><div><span>日历版本</span><strong>{{ userSummary?.summary?.calendar_count ?? '—' }}</strong></div><div><span>行动记录</span><strong>{{ userSummary?.summary?.decision_log_count ?? '—' }}</strong></div></div>
          <div class="section-caption"><h3>用户历程</h3><span>最近 {{ userPanelData.timeline?.items?.length || 0 }} 条</span></div>
          <p v-if="timelineLoading" class="timeline-state" role="status" aria-live="polite">正在整理用户历程…</p>
          <div v-else-if="timelineError" class="timeline-state timeline-error" role="alert"><span>{{ timelineError }}</span><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="$emit('retry-user-timeline')">重试</VanButton></div>
          <ol class="user-timeline">
            <li v-for="item in userPanelData.timeline?.items || []" v-show="!timelineLoading && !timelineError" :key="item.key" class="user-timeline-item">
              <span class="user-timeline-marker" aria-hidden="true"></span>
              <div class="user-timeline-copy"><strong>{{ item.label }}</strong><p>{{ item.description || resourceLabel(item.resource_type) }}</p></div>
              <time>{{ formatDateTime(item.occurred_at) }}</time>
            </li>
            <li v-if="!timelineLoading && !timelineError && !userPanelData.timeline?.items?.length" class="empty-cell">暂无历程记录。</li>
          </ol>
          <div class="user-overview-links" aria-label="用户详细记录">
            <button type="button" @click="$emit('set-user-panel-tab', 'applications')">申请记录</button>
            <button type="button" @click="$emit('set-user-panel-tab', 'reports')">报告</button>
            <button type="button" @click="$emit('set-user-panel-tab', 'calendar')">日历</button>
            <button type="button" @click="$emit('set-user-panel-tab', 'decisions')">行动记录</button>
            <button type="button" @click="$emit('set-user-panel-tab', 'activity')">审计活动</button>
          </div>
        </section>
        <section v-if="userPanelTab === 'profile'" class="drawer-section">
          <div class="profile-data-grid">
            <section class="profile-data-group"><h3>账号信息</h3><div class="profile-data-items"><p><span>用户 ID</span><strong>{{ detailUser.id }}</strong></p><p><span>角色 / 类型</span><strong>{{ roleText(detailUser.role) }} · {{ displayValue(detailUser.user_type) }}</strong></p><p><span>账号状态</span><strong>{{ detailUser.is_active ? '正常' : '已停用' }}</strong></p><p><span>档案完成度</span><strong>{{ detailUser.profile_completion ?? '—' }}%</strong></p><p><span>手机验证</span><strong>{{ formatDateTime(detailUser.phone_verified_at) }}</strong></p><p><span>注册时间</span><strong>{{ formatDateTime(detailUser.created_at) }}</strong></p><p><span>资料更新时间</span><strong>{{ formatDateTime(detailUser.updated_at) }}</strong></p><p><span>最近登录</span><strong>{{ formatDateTime(detailUser.last_login_at) }}</strong></p><p><span>资料版本 / 确认</span><strong>v{{ detailUser.profile_version }} · {{ formatDateTime(detailUser.profile_last_confirmed_at) }}</strong></p></div></section>
            <section class="profile-data-group"><h3>出生档案</h3><div class="profile-data-items"><p><span>性别</span><strong>{{ genderLabel(detailUser.gender) }}</strong></p><p><span>出生日期</span><strong>{{ birthDateLabel(detailUser) }}</strong></p><p><span>出生时间</span><strong>{{ birthTimeLabel(detailUser) }} · {{ precisionLabel(detailUser.birth_time_precision) }}</strong></p><p><span>出生地</span><strong>{{ displayValue(detailUser.birth_place) }}</strong></p><p><span>头像地址</span><strong class="profile-break-value">{{ displayValue(detailUser.avatar_url) }}</strong></p></div></section>
            <section class="profile-data-group"><h3>当前画像</h3><div class="profile-data-items"><p><span>常住地</span><strong>{{ displayValue(detailUser.current_residence) }}</strong></p><p><span>婚姻状况</span><strong>{{ displayValue(detailUser.marital_status) }}</strong></p><p><span>职业状态</span><strong>{{ displayValue(detailUser.occupation_status) }}</strong></p><p><span>最高学历</span><strong>{{ displayValue(detailUser.highest_education) }}</strong></p><p><span>MBTI</span><strong>{{ displayValue(detailUser.mbti) }}</strong></p><p><span>性格关键词</span><strong>{{ displayValue(detailUser.personality_keywords) }}</strong></p><p><span>优势</span><strong>{{ displayValue(detailUser.strengths) }}</strong></p><p><span>限制因素</span><strong>{{ displayValue(detailUser.limitations) }}</strong></p></div></section>
            <section class="profile-data-group"><h3>内容偏好</h3><div class="profile-data-items"><p><span>命理经验</span><strong>{{ displayValue(detailUser.mingli_experience) }}</strong></p><p v-if="detailUser.mingli_experience_other"><span>其他命理体验</span><strong>{{ displayValue(detailUser.mingli_experience_other) }}</strong></p><p><span>命理态度</span><strong>{{ displayValue(detailUser.mingli_attitude) }}</strong></p><p><span>内容深度</span><strong>{{ displayValue(detailUser.preferred_content_depth) }}</strong></p><p><span>常用场景</span><strong>{{ displayValue(detailUser.default_usage_scenarios) }}</strong></p><p v-if="detailUser.default_usage_scenarios_other"><span>其他使用场景</span><strong>{{ displayValue(detailUser.default_usage_scenarios_other) }}</strong></p></div></section>
          </div>
          <form class="stack-form" @submit.prevent="$emit('save-user-profile')"><div class="section-caption"><h3>常用档案维护</h3><span>保存操作会记录在审计活动中</span></div><div class="form-grid two"><label>姓名<input v-model.trim="userEdit.name" autocomplete="name" required></label><label>性别<select v-model="userEdit.gender"><option value="">未填写</option><option value="male">男</option><option value="female">女</option></select></label><label>出生年<input v-model="userEdit.birth_year" type="number" min="1900" :max="currentYear"></label><label>出生月<input v-model="userEdit.birth_month" type="number" min="1" max="12"></label><label>出生日<input v-model="userEdit.birth_day" type="number" min="1" max="31"></label><label>出生时<input v-model="userEdit.birth_hour" type="number" min="0" max="23"></label><label>出生分<input v-model="userEdit.birth_minute" type="number" min="0" max="59"></label><label>出生地<input v-model.trim="userEdit.birth_place" placeholder="可选"></label><label class="span-two">头像地址<input v-model.trim="userEdit.avatar_url" type="url" placeholder="可选，填写可访问的头像地址"></label></div><VanButton class="primary-button" type="primary" native-type="submit" :disabled="profileSaving" :loading="profileSaving" loading-text="保存中…" :aria-busy="profileSaving">保存资料</VanButton></form>
        </section>
        <section v-else-if="userPanelTab === 'applications'" class="drawer-section">
            <section class="request-history-group"><div class="section-caption"><h3>报告申请 · 咨询师交付</h3><span>{{ userPanelData.applications?.serviceRequests?.total || 0 }} 份</span></div><article v-for="item in userPanelData.applications?.serviceRequests?.items || []" :key="`report-${item.id}`" class="request-history-card"><div class="request-history-head"><div><strong>申请 #{{ item.id }}</strong><small>{{ consultationTypeLabel(item.consultation_type) }} · {{ formatDateTime(item.created_at) }} · {{ item.assigned_consultant_name || '待分配咨询师' }}</small></div><span :class="['status-badge', `request-${item.status}`]">{{ serviceRequestStatusText(item.status) }}</span></div><p class="request-history-goal">{{ item.request_payload?.context?.current_challenge || '未填写当前问题' }}</p><small>关注主题：{{ topicLabel(requestTopicValues(item.request_payload), '—') }} · 期望结果：{{ labelList(requestExpectedOutcomeValues(item.request_payload), EXPECTED_OUTCOME_LABELS, '—') }}</small><div class="request-history-timeline"><p><span>接单</span><strong>{{ formatDateTime(item.accepted_at) }}</strong></p><p><span>初稿开始</span><strong>{{ formatDateTime(item.ai_started_at) }}</strong></p><p><span>初稿完成</span><strong>{{ formatDateTime(item.ai_completed_at) }}</strong></p><p><span>审校</span><strong>{{ formatDateTime(item.reviewing_at) }}</strong></p><p><span>待补充</span><strong>{{ formatDateTime(item.needs_info_at) }}</strong></p><p><span>处理失败</span><strong>{{ formatDateTime(item.failed_at) }}</strong></p><p><span>交付</span><strong>{{ formatDateTime(item.delivered_at) }}</strong></p><p><span>关闭 / 撤回</span><strong>{{ formatDateTime(item.rejected_at || item.withdrawn_at) }}</strong></p></div><p v-if="item.needs_info_reason || item.rejection_reason || item.last_error" class="request-note">{{ item.needs_info_reason || item.rejection_reason || item.last_error }}</p><details class="request-payload-details"><summary>查看完整申请内容</summary><pre>{{ prettyJson(item.request_payload) }}</pre></details><VanButton v-if="item.result_type === 'report' && item.result_id" class="secondary-button compact-button" type="default" plain native-type="button" @click="$emit('open-report', { id: item.result_id })">查看交付报告 #{{ item.result_id }}</VanButton></article><p v-if="!userPanelData.applications?.serviceRequests?.items?.length" class="empty-cell">暂无报告申请。</p></section>
          <section class="request-history-group"><div class="section-caption"><h3>日历申请 · AI 生成</h3><span>{{ userPanelData.applications?.calendarRequests?.total || 0 }} 份</span></div><article v-for="item in userPanelData.applications?.calendarRequests?.items || []" :key="`calendar-${item.id}`" class="request-history-card"><div class="request-history-head"><div><strong>申请 #{{ item.id }}</strong><small>{{ formatDateTime(item.created_at) }} · {{ formatDate(item.start_date) }} — {{ formatDate(item.end_date) }}</small></div><span :class="['status-badge', `calendar-request-${item.status}`]">{{ calendarRequestStatusText(item.status) }}</span></div><p class="request-history-goal">{{ item.goal || '未填写当前决策目标' }}</p><small>关注领域：{{ topicLabel(item.focus_topics, '—') }} · 用途：{{ usageScenarioLabel(item.usage_scenario, '—') }} · 来源报告：{{ item.source_report_id || '—' }}</small><div class="request-history-timeline"><p><span>进度</span><strong>{{ item.progress }}%</strong></p><p><span>重试次数</span><strong>{{ item.retry_count }}</strong></p><p><span>审核时间</span><strong>{{ formatDateTime(item.reviewed_at) }}</strong></p><p><span>日历</span><strong>{{ item.calendar_id ? `#${item.calendar_id}` : '—' }}</strong></p></div><p v-if="item.generation_error || item.review_note" class="request-note">{{ item.generation_error || item.review_note }}</p><details class="request-payload-details"><summary>查看完整申请内容</summary><pre>{{ prettyJson(item) }}</pre></details></article><p v-if="!userPanelData.applications?.calendarRequests?.items?.length" class="empty-cell">暂无日历申请。</p></section>
        </section>
        <section v-else-if="userPanelTab === 'reports'" class="drawer-section"><div class="section-caption"><h3>用户报告</h3><span>{{ userPanelData.reports?.total || 0 }} 份</span></div><div class="drawer-list"><button v-for="report in userPanelData.reports?.items || []" :key="report.id" type="button" class="drawer-list-item" @click="$emit('open-report', report)"><span><strong>{{ report.title }}</strong><small>{{ formatDateTime(report.created_at) }} · {{ report.energy_type || '综合型' }}</small></span><b>查看 →</b></button><p v-if="!userPanelData.reports?.items?.length" class="empty-cell">暂无报告。</p></div></section>
        <section v-else-if="userPanelTab === 'calendar'" class="drawer-section"><div class="section-caption"><h3>用户日历</h3><span>{{ userPanelData.calendars?.length || 0 }} 个版本</span></div><div class="drawer-list"><article v-for="calendar in userPanelData.calendars || []" :key="calendar.id" class="drawer-list-item calendar-record-card"><div><strong>{{ calendar.title }}</strong><small>#{{ calendar.id }} · v{{ calendar.version_number }} · {{ calendar.entries?.length || 0 }} 天 · {{ formatDateTime(calendar.updated_at) }}</small><details class="request-payload-details"><summary>查看完整日历内容</summary><pre>{{ prettyJson(calendar) }}</pre></details></div><div class="calendar-record-actions"><span :class="['status-badge', `calendar-${calendar.status}`]">{{ calendarStatusText(calendar.status) }}</span><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="openCalendarPreview(calendar)">{{ calendarPreviewId === calendar.id ? '关闭视图' : '用户视图' }}</VanButton></div></article><p v-if="!userPanelData.calendars?.length" class="empty-cell">暂无日历。</p></div><div v-if="selectedCalendarPreview" class="calendar-preview-panel"><div class="section-caption"><h3>{{ selectedCalendarPreview.title }}</h3><VanButton class="filter-reset" type="default" plain native-type="button" @click="calendarPreviewId = null">关闭预览</VanButton></div><CalendarReadOnlyPreview :calendar="selectedCalendarPreview" :decision-logs="userPanelData.decisions?.items || []" /></div><VanButton class="secondary-button full-button" type="default" plain native-type="button" @click="$emit('open-calendar-for-user', detailUser)"><template #icon><IconMark name="calendar" /></template>进入日历编辑器</VanButton></section>
        <section v-else-if="userPanelTab === 'decisions'" class="drawer-section"><div class="section-caption"><h3>行动 / 决策记录</h3><span>{{ userPanelData.decisions?.total || 0 }} 条 · 只读</span></div><div class="decision-list"><div v-for="log in userPanelData.decisions?.items || []" :key="log.id"><div><strong>{{ log.content }}</strong><small>{{ formatDate(log.log_date) }} · {{ log.kind === 'decision' ? '决策' : '行动' }} · 更新于 {{ formatDateTime(log.updated_at) }}</small><small v-if="log.note">备注：{{ log.note }}</small></div><span :class="['status-badge', `decision-${log.status}`]">{{ decisionStatusText(log.status) }}</span></div><p v-if="!userPanelData.decisions?.items?.length" class="empty-cell">暂无行动记录。</p></div></section>
        <section v-else class="drawer-section"><div class="section-caption"><h3>最近审计活动</h3><span>{{ userPanelData.activity?.total || 0 }} 条</span></div><div class="activity-list compact"><button v-for="log in userPanelData.activity?.items || []" :key="log.id" type="button" class="activity-item audit-activity-item" @click="emit('open-log', log)"><span class="activity-dot"></span><span><strong>{{ actionLabel(log.action) }}</strong><p>{{ resourceLabel(log.resource_type) }}</p></span><time>{{ formatDateTime(log.created_at) }}</time></button><p v-if="!userPanelData.activity?.items?.length" class="empty-cell">暂无审计活动。</p></div></section>
      </div>
    </aside>
  </div>

  <div v-if="reportDetail" class="drawer-layer" @click.self="$emit('close-report')">
    <aside ref="reportDrawer" class="drawer report-drawer" role="dialog" aria-modal="true" aria-labelledby="report-detail-title" tabindex="-1" @keydown="handleDrawerKeydown">
      <div class="drawer-header"><div><p class="eyebrow">REPORT #{{ reportDetail.id }}</p><h2 id="report-detail-title">{{ reportDetail.title }}</h2><small>{{ reportDetail.user_name }} · {{ reportDetail.user_phone }}</small></div><AdminIconButton class="drawer-close" icon="close" label="关闭报告详情" @click="$emit('close-report')" /></div>
      <div class="drawer-body report-body">
        <div class="report-view-switch" role="tablist" aria-label="报告详情视图">
          <button type="button" role="tab" :aria-selected="reportView === 'user'" :class="{ active: reportView === 'user' }" @click="reportView = 'user'">用户视图</button>
          <button type="button" role="tab" :aria-selected="reportView === 'admin'" :class="{ active: reportView === 'admin' }" @click="reportView = 'admin'">管理信息</button>
        </div>
        <section v-if="reportView === 'user' && reportPreview" class="report-user-view">
          <div class="report-user-meta"><span>生成时间：{{ formatDateTime(reportDetail.created_at) }}</span><span>{{ reportPreview.report.basicInfo?.name || reportDetail.user_name || '用户' }}</span></div>
          <ReportContent :report="reportPreview.report" :foundation-data="reportPreview.foundationData" :content-without-foundation="reportPreview.contentWithoutFoundation" />
        </section>
        <section v-else class="report-admin-view">
          <div class="report-meta-grid"><div><span>状态</span><strong>{{ reportStatusText(reportDetail.status) }}</strong></div><div><span>模型</span><strong>{{ reportDetail.ai_model || '—' }}</strong></div><div><span>耗时</span><strong>{{ reportDetail.generation_time_ms ? `${reportDetail.generation_time_ms} ms` : '—' }}</strong></div><div><span>生成于</span><strong>{{ formatDateTime(reportDetail.created_at) }}</strong></div><div><span>生成来源</span><strong>{{ reportDetail.basic_info?.generated_by || '—' }}</strong></div><div><span>出生信息</span><strong>{{ reportDetail.basic_info?.birth_date || formatDate(reportDetail.birth_date) }} {{ reportDetail.birth_time || '' }}</strong></div><div><span>出生地 / 历法</span><strong>{{ reportDetail.birth_place || '—' }} · {{ displayValue(reportDetail.birth_calendar_type) }}</strong></div><div><span>档案版本</span><strong>{{ reportDetail.profile_version ? `v${reportDetail.profile_version}` : '—' }}</strong></div><div><span>申请 / 审校</span><strong>{{ reportDetail.request_id ? `#${reportDetail.request_id}` : '—' }} · {{ formatDateTime(reportDetail.reviewed_at) }}</strong></div><div><span>关注主题</span><strong>{{ topicLabel(reportDetail.selected_topics, '—') }}</strong></div></div><article class="report-block"><h3>摘要</h3><p>{{ reportDetail.summary || '暂无摘要。' }}</p></article><article class="report-block"><h3>能量画像</h3><pre>{{ prettyJson(reportDetail.energy_profile) }}</pre></article><article class="report-block"><h3>行动建议</h3><pre>{{ prettyJson(reportDetail.career_guidance) }}</pre></article><article class="report-block"><h3>关系模式</h3><pre>{{ prettyJson(reportDetail.relationship_pattern) }}</pre></article><article class="report-block"><h3>个人成长</h3><pre>{{ prettyJson(reportDetail.personal_growth) }}</pre></article><article class="report-block"><h3>咨询师审校内容</h3><pre>{{ prettyJson(reportDetail.content_payload) }}</pre></article><article class="report-block"><details class="request-payload-details"><summary>查看原始生成内容</summary><pre>{{ reportDetail.ai_generated_content || '无单独保存的原始 AI 文本。' }}</pre></details></article><article class="report-block"><details class="request-payload-details"><summary>查看完整输入快照与咨询情境</summary><pre>{{ prettyJson({ input_snapshot: reportDetail.input_snapshot, context: reportDetail.context, additional_info: reportDetail.additional_info }) }}</pre></details></article>
        </section>
      </div>
    </aside>
  </div>

  <div v-if="logDetail" class="drawer-layer" @click.self="$emit('close-log')">
    <aside ref="logDrawer" class="drawer log-drawer" role="dialog" aria-modal="true" aria-labelledby="log-detail-title" tabindex="-1" @keydown="handleDrawerKeydown">
      <div class="drawer-header"><div><p class="eyebrow">AUDIT #{{ logDetail.id }}</p><h2 id="log-detail-title">{{ actionLabel(logDetail.action) }}</h2><small>{{ formatDateTime(logDetail.created_at) }}</small></div><AdminIconButton class="drawer-close" icon="close" label="关闭审计详情" @click="$emit('close-log')" /></div>
      <div class="drawer-body"><div class="detail-facts"><p><span>操作编码</span><strong class="mono-text">{{ logDetail.action }}</strong></p><p><span>资源</span><strong>{{ resourceLabel(logDetail.resource_type) }} {{ logDetail.resource_id ? `#${logDetail.resource_id}` : '' }}</strong></p><p><span>操作者</span><strong>{{ logDetail.actor_name || logDetail.actor_user_id || '系统' }}</strong></p><p><span>目标用户</span><strong>{{ logDetail.target_user_name || logDetail.target_user_id || '—' }}</strong></p><p><span>请求 ID</span><strong class="mono-text">{{ logDetail.request_id || '—' }}</strong></p><p><span>IP / UA</span><strong>{{ logDetail.ip_address || '—' }}<small>{{ logDetail.user_agent || '' }}</small></strong></p></div><div class="json-view"><span>结构化详情</span><pre>{{ prettyJson(logDetail.details_json || logDetail.details || {}) }}</pre></div></div>
    </aside>
  </div>
</template>
