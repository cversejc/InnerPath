<script setup>
import { ref } from 'vue'
import {
  actionLabel,
  calendarStatusText,
  decisionStatusText,
  formatDate,
  formatDateTime,
  prettyJson,
  reportStatusText,
  resourceLabel,
  roleText,
  statusText
} from '../formatters.js'

defineProps({
  bookingDetail: { type: Object, default: null },
  bookingEditor: { type: Object, required: true },
  bookingSaving: { type: Boolean, default: false },
  consultants: { type: Array, default: () => [] },
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
  userSummary: { type: Object, default: null }
})

const emit = defineEmits([
  'close-booking',
  'close-log',
  'close-report',
  'close-user',
  'close-active',
  'open-booking-detail',
  'open-calendar-for-user',
  'open-report',
  'save-booking',
  'save-course-progress',
  'save-user-profile',
  'set-user-panel-tab'
])

const userDrawer = ref(null)
const bookingDrawer = ref(null)
const reportDrawer = ref(null)
const logDrawer = ref(null)

function getDrawer(name) {
  return { userDrawer, bookingDrawer, reportDrawer, logDrawer }[name]?.value || null
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
      <div class="drawer-header"><div class="person-cell"><span class="avatar-mark large">{{ detailUser.name?.slice(0, 1) || '人' }}</span><span><p class="eyebrow">USER #{{ detailUser.id }}</p><h2 id="user-detail-title">{{ detailUser.name }}</h2><small>{{ detailUser.phone }}</small></span></div><button type="button" class="drawer-close" aria-label="关闭用户详情" @click="$emit('close-user')">×</button></div>
      <div class="drawer-tabs"><button v-for="tab in userPanelTabs" :key="tab.id" type="button" :class="{ active: userPanelTab === tab.id }" @click="$emit('set-user-panel-tab', tab.id)">{{ tab.label }}</button></div>
      <div v-if="userPanelLoading" class="drawer-loading" role="status" aria-live="polite">正在整理用户资料…</div>
      <div v-else class="drawer-body">
        <section v-if="userPanelTab === 'profile'" class="drawer-section">
          <div class="profile-summary"><div><span>报告</span><strong>{{ userSummary?.summary?.report_count ?? '—' }}</strong></div><div><span>预约</span><strong>{{ userSummary?.summary?.booking_count ?? '—' }}</strong></div><div><span>日历</span><strong>{{ userSummary?.summary?.calendar_count ?? '—' }}</strong></div><div><span>学习</span><strong>{{ userSummary?.summary?.average_course_progress ?? 0 }}%</strong></div></div>
          <form class="stack-form" @submit.prevent="$emit('save-user-profile')"><div class="form-grid two"><label>姓名<input v-model.trim="userEdit.name" autocomplete="name" required></label><label>性别<select v-model="userEdit.gender"><option value="">未填写</option><option value="male">男</option><option value="female">女</option></select></label><label>出生年<input v-model="userEdit.birth_year" type="number" min="1900" max="2026"></label><label>出生月<input v-model="userEdit.birth_month" type="number" min="1" max="12"></label><label>出生日<input v-model="userEdit.birth_day" type="number" min="1" max="31"></label><label>出生时<input v-model="userEdit.birth_hour" type="number" min="0" max="23"></label><label>出生分<input v-model="userEdit.birth_minute" type="number" min="0" max="59"></label><label>出生地<input v-model.trim="userEdit.birth_place" placeholder="可选"></label><label class="span-two">头像地址<input v-model.trim="userEdit.avatar_url" type="url" placeholder="可选，填写可访问的头像地址"></label></div><button class="primary-button" type="submit" :disabled="profileSaving" :aria-busy="profileSaving">{{ profileSaving ? '保存中…' : '保存资料' }}</button></form>
          <div class="detail-facts"><p><span>角色</span><strong>{{ roleText(detailUser.role) }}</strong></p><p><span>状态</span><strong>{{ detailUser.is_active ? '正常' : '已停用' }}</strong></p><p><span>注册时间</span><strong>{{ formatDateTime(detailUser.created_at) }}</strong></p><p><span>最近登录</span><strong>{{ formatDateTime(detailUser.last_login_at) }}</strong></p></div>
        </section>
        <section v-else-if="userPanelTab === 'reports'" class="drawer-section"><div class="section-caption"><h3>用户报告</h3><span>{{ userPanelData.reports?.total || 0 }} 份</span></div><div class="drawer-list"><button v-for="report in userPanelData.reports?.items || []" :key="report.id" type="button" class="drawer-list-item" @click="$emit('open-report', report)"><span><strong>{{ report.title }}</strong><small>{{ formatDate(report.created_at) }} · {{ report.energy_type || '综合型' }}</small></span><b>查看 →</b></button><p v-if="!userPanelData.reports?.items?.length" class="empty-cell">暂无报告。</p></div></section>
        <section v-else-if="userPanelTab === 'bookings'" class="drawer-section"><div class="section-caption"><h3>用户预约</h3><span>{{ userPanelData.bookings?.total || 0 }} 条</span></div><div class="drawer-list"><button v-for="booking in userPanelData.bookings?.items || []" :key="booking.id" type="button" class="drawer-list-item" @click="$emit('open-booking-detail', booking)"><span><strong>{{ booking.service_name }}</strong><small>{{ booking.confirmed_date || booking.preferred_time }} · {{ booking.consultant_name || '未分配' }}</small></span><span :class="['status-badge', `booking-${booking.status}`]">{{ statusText(booking.status) }}</span></button><p v-if="!userPanelData.bookings?.items?.length" class="empty-cell">暂无预约。</p></div></section>
        <section v-else-if="userPanelTab === 'courses'" class="drawer-section"><div class="section-caption"><h3>课程进度</h3><span>{{ userPanelData.courses?.length || 0 }} 门</span></div><div class="course-admin-list"><div v-for="course in userPanelData.courses || []" :key="course.course_id" class="course-admin-row"><div><strong>{{ course.title }}</strong><small>{{ course.completed_lessons }} / {{ course.total_lessons }} 课时</small></div><div class="course-progress-editor"><input v-model.number="course.progress" type="number" min="0" max="100"><span>%</span><button type="button" @click="$emit('save-course-progress', course)">保存</button></div></div><p v-if="!userPanelData.courses?.length" class="empty-cell">暂无课程。</p></div></section>
        <section v-else-if="userPanelTab === 'calendar'" class="drawer-section"><div class="section-caption"><h3>用户日历</h3><span>{{ userPanelData.calendars?.length || 0 }} 个版本</span></div><div class="drawer-list"><button v-for="calendar in userPanelData.calendars || []" :key="calendar.id" type="button" class="drawer-list-item" @click="$emit('open-calendar-for-user', detailUser)"><span><strong>{{ calendar.title }}</strong><small>v{{ calendar.version_number }} · {{ calendar.entries?.length || 0 }} 天</small></span><span :class="['status-badge', `calendar-${calendar.status}`]">{{ calendarStatusText(calendar.status) }}</span></button><p v-if="!userPanelData.calendars?.length" class="empty-cell">暂无日历。</p></div><button class="secondary-button full-button" type="button" @click="$emit('open-calendar-for-user', detailUser)">进入日历编辑器 →</button></section>
        <section v-else-if="userPanelTab === 'decisions'" class="drawer-section"><div class="section-caption"><h3>行动 / 决策记录</h3><span>{{ userPanelData.decisions?.total || 0 }} 条 · 只读</span></div><div class="decision-list"><div v-for="log in userPanelData.decisions?.items || []" :key="log.id"><div><strong>{{ log.content }}</strong><small>{{ formatDate(log.log_date) }} · {{ log.kind === 'decision' ? '决策' : '行动' }}</small></div><span :class="['status-badge', `decision-${log.status}`]">{{ decisionStatusText(log.status) }}</span></div><p v-if="!userPanelData.decisions?.items?.length" class="empty-cell">暂无行动记录。</p></div></section>
        <section v-else class="drawer-section"><div class="section-caption"><h3>最近审计活动</h3><span>{{ userPanelData.activity?.total || 0 }} 条</span></div><div class="activity-list compact"><div v-for="log in userPanelData.activity?.items || []" :key="log.id" class="activity-item"><span class="activity-dot"></span><div><strong>{{ actionLabel(log.action) }}</strong><p>{{ resourceLabel(log.resource_type) }}</p></div><time>{{ formatDateTime(log.created_at) }}</time></div><p v-if="!userPanelData.activity?.items?.length" class="empty-cell">暂无审计活动。</p></div></section>
      </div>
    </aside>
  </div>

  <div v-if="bookingDetail" class="drawer-layer" @click.self="$emit('close-booking')">
    <aside ref="bookingDrawer" class="drawer booking-drawer" role="dialog" aria-modal="true" aria-labelledby="booking-detail-title" tabindex="-1" @keydown="handleDrawerKeydown">
      <div class="drawer-header"><div><p class="eyebrow">BOOKING #{{ bookingDetail.id }}</p><h2 id="booking-detail-title">{{ bookingDetail.service_name }}</h2><small>{{ bookingDetail.user_name || `用户 #${bookingDetail.user_id}` }} · {{ bookingDetail.user_phone || bookingDetail.contact_phone }}</small></div><button type="button" class="drawer-close" aria-label="关闭预约详情" @click="$emit('close-booking')">×</button></div>
      <form class="drawer-body stack-form" @submit.prevent="$emit('save-booking')"><div class="detail-facts"><p><span>关注议题</span><strong>{{ bookingDetail.topics?.join('、') || '—' }}</strong></p><p><span>用户备注</span><strong>{{ bookingDetail.notes || '—' }}</strong></p><p><span>期望时间</span><strong>{{ bookingDetail.preferred_time }}</strong></p></div><label>预约状态<select v-model="bookingEditor.status"><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></label><div class="form-grid two"><label>确认日期<input v-model="bookingEditor.confirmed_date" type="date"></label><label>确认时间<input v-model="bookingEditor.confirmed_time" type="time"></label></div><label>分配咨询师<select v-model="bookingEditor.consultant_id"><option :value="null">未分配</option><option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select></label><label>会议链接<input v-model.trim="bookingEditor.meeting_url" type="url" placeholder="可选"></label><label>会议备注<textarea v-model.trim="bookingEditor.meeting_notes" rows="4" placeholder="记录会议安排或沟通要点"></textarea></label><label v-if="bookingEditor.status === 'cancelled'">取消原因<textarea v-model.trim="bookingEditor.cancellation_reason" rows="3" placeholder="可选"></textarea></label><button class="primary-button" type="submit" :disabled="bookingSaving" :aria-busy="bookingSaving">{{ bookingSaving ? '保存中…' : '保存预约' }}</button></form>
    </aside>
  </div>

  <div v-if="reportDetail" class="drawer-layer" @click.self="$emit('close-report')">
    <aside ref="reportDrawer" class="drawer report-drawer" role="dialog" aria-modal="true" aria-labelledby="report-detail-title" tabindex="-1" @keydown="handleDrawerKeydown">
      <div class="drawer-header"><div><p class="eyebrow">REPORT #{{ reportDetail.id }}</p><h2 id="report-detail-title">{{ reportDetail.title }}</h2><small>{{ reportDetail.user_name }} · {{ reportDetail.user_phone }}</small></div><button type="button" class="drawer-close" aria-label="关闭报告详情" @click="$emit('close-report')">×</button></div>
      <div class="drawer-body report-body"><div class="report-meta-grid"><div><span>状态</span><strong>{{ reportStatusText(reportDetail.status) }}</strong></div><div><span>模型</span><strong>{{ reportDetail.ai_model || '—' }}</strong></div><div><span>耗时</span><strong>{{ reportDetail.generation_time_ms ? `${reportDetail.generation_time_ms} ms` : '—' }}</strong></div><div><span>生成于</span><strong>{{ formatDateTime(reportDetail.created_at) }}</strong></div><div><span>生成来源</span><strong>{{ reportDetail.basic_info?.generated_by || '—' }}</strong></div></div><article class="report-block"><h3>摘要</h3><p>{{ reportDetail.summary || '暂无摘要。' }}</p></article><article class="report-block"><h3>能量画像</h3><pre>{{ prettyJson(reportDetail.energy_profile) }}</pre></article><article class="report-block"><h3>行动建议</h3><pre>{{ prettyJson(reportDetail.career_guidance) }}</pre></article><article class="report-block"><h3>关系模式</h3><pre>{{ prettyJson(reportDetail.relationship_pattern) }}</pre></article><article class="report-block"><h3>个人成长</h3><pre>{{ prettyJson(reportDetail.personal_growth) }}</pre></article></div>
    </aside>
  </div>

  <div v-if="logDetail" class="drawer-layer" @click.self="$emit('close-log')">
    <aside ref="logDrawer" class="drawer log-drawer" role="dialog" aria-modal="true" aria-labelledby="log-detail-title" tabindex="-1" @keydown="handleDrawerKeydown">
      <div class="drawer-header"><div><p class="eyebrow">AUDIT #{{ logDetail.id }}</p><h2 id="log-detail-title">{{ actionLabel(logDetail.action) }}</h2><small>{{ formatDateTime(logDetail.created_at) }}</small></div><button type="button" class="drawer-close" aria-label="关闭审计详情" @click="$emit('close-log')">×</button></div>
      <div class="drawer-body"><div class="detail-facts"><p><span>操作编码</span><strong class="mono-text">{{ logDetail.action }}</strong></p><p><span>资源</span><strong>{{ resourceLabel(logDetail.resource_type) }} {{ logDetail.resource_id ? `#${logDetail.resource_id}` : '' }}</strong></p><p><span>操作者</span><strong>{{ logDetail.actor_name || logDetail.actor_user_id || '系统' }}</strong></p><p><span>目标用户</span><strong>{{ logDetail.target_user_name || logDetail.target_user_id || '—' }}</strong></p><p><span>请求 ID</span><strong class="mono-text">{{ logDetail.request_id || '—' }}</strong></p><p><span>IP / UA</span><strong>{{ logDetail.ip_address || '—' }}<small>{{ logDetail.user_agent || '' }}</small></strong></p></div><div class="json-view"><span>结构化详情</span><pre>{{ prettyJson(logDetail.details_json || logDetail.details || {}) }}</pre></div></div>
    </aside>
  </div>
</template>
