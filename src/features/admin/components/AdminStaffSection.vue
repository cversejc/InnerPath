<script setup>
import { computed, reactive, watch } from 'vue'
import { Button as VanButton } from 'vant'
import { formatDateTime, roleText, serviceRequestStatusText } from '../formatters.js'
import { consultationTypeLabel } from '../../service-requests/formatters.js'

const props = defineProps({
  inviteForm: { type: Object, required: true },
  inviteSaving: { type: Boolean, default: false },
  inviteToken: { type: String, default: '' },
  consultantWorkloads: { type: Array, default: () => [] },
  workloadPeriodDays: { type: Number, default: 30 },
  workloadError: { type: String, default: '' },
  workloadLoading: { type: Boolean, default: false },
  specialtySavingId: { type: Number, default: null },
  staffLoading: { type: Boolean, default: false },
  staffUsers: { type: Array, default: () => [] }
})

const emit = defineEmits(['invite', 'open-activity', 'open-requests', 'update-specialties', 'change-workload-period'])
const specialties = [
  { id: 'metaphysics', label: '命理' },
  { id: 'psychology', label: '心理' }
]
const workloadPeriods = [7, 30, 90]
const specialtyDrafts = reactive({})
const workloadByConsultant = computed(() => new Map(
  props.consultantWorkloads.map(item => [item.consultant_id, item])
))

function specialtiesFor(member) {
  if (member.consultant_specialties?.length) return [...member.consultant_specialties]
  if (member.consultant_type === 'integrated') return specialties.map(item => item.id)
  if (member.consultant_type === 'mingli') return ['metaphysics']
  if (member.consultant_type === 'psychology') return ['psychology']
  return []
}

watch(() => props.staffUsers, members => {
  for (const member of members) {
    if (member.role === 'consultant') specialtyDrafts[member.id] = specialtiesFor(member)
  }
}, { immediate: true, deep: true })

function toggleSpecialty(memberId, specialty, checked) {
  const selected = new Set(specialtyDrafts[memberId] || [])
  if (checked) selected.add(specialty)
  else selected.delete(specialty)
  specialtyDrafts[memberId] = specialties.map(item => item.id).filter(item => selected.has(item))
}

function specialtiesChanged(member) {
  return JSON.stringify(specialtyDrafts[member.id] || []) !== JSON.stringify(specialtiesFor(member))
}

function saveSpecialties(member) {
  emit('update-specialties', { userId: member.id, specialties: specialtyDrafts[member.id] || [] })
}

function formatCycleHours(value) {
  if (value === null || value === undefined) return '—'
  return value >= 24 ? `${(value / 24).toFixed(1)} 天` : `${value} 小时`
}
</script>

<template>
  <section class="content-view">
    <div class="view-heading"><div><p class="eyebrow">TEAM / ACCESS</p><h2>后台成员</h2><p>维护咨询师与管理员席位，邀请链接只展示一次。</p></div></div>
    <div class="staff-grid">
      <article class="panel-surface invite-card">
        <p class="eyebrow">NEW INVITATION</p><h3>邀请后台成员</h3>
        <form class="stack-form" @submit.prevent="$emit('invite')">
          <label>手机号<input v-model.trim="inviteForm.phone" type="tel" inputmode="numeric" autocomplete="tel" required maxlength="11" placeholder="11 位手机号"></label>
          <label>角色<select v-model="inviteForm.role"><option value="consultant">咨询师</option><option value="admin">管理员</option></select></label>
          <label v-if="inviteForm.role === 'consultant'">专业类型<select v-model="inviteForm.consultant_type" required><option value="mingli">命理咨询师</option><option value="psychology">心理咨询师</option><option value="integrated">综合咨询师</option></select></label>
          <VanButton class="primary-button" type="primary" native-type="submit" :disabled="inviteSaving" :loading="inviteSaving" loading-text="生成中…" :aria-busy="inviteSaving">生成邀请链接</VanButton>
        </form>
        <div v-if="inviteToken" class="invite-result" role="status" aria-live="polite"><span>本次令牌</span><code>{{ inviteToken }}</code><router-link :to="{ path: '/auth/invite', query: { token: inviteToken } }">打开邀请页面 →</router-link></div>
      </article>

      <article class="panel-surface team-card">
        <div class="panel-heading team-panel-heading"><div><p class="eyebrow">CURRENT TEAM</p><h3>当前成员与工作量</h3></div><div class="team-heading-tools"><div class="workload-period" role="group" aria-label="咨询师工作量统计周期"><button v-for="days in workloadPeriods" :key="days" type="button" :aria-pressed="workloadPeriodDays === days" :disabled="workloadLoading" @click="emit('change-workload-period', days)">{{ days }} 天</button></div><span>{{ staffUsers.length }}</span></div></div>
        <div v-if="staffLoading" class="list-loading" aria-label="正在加载成员"><i v-for="index in 4" :key="index"></i></div>
        <div v-else class="team-list">
          <article v-for="member in staffUsers" :key="member.id" class="team-member">
            <div class="team-row"><span class="avatar-mark">{{ member.name?.slice(0, 1) || '人' }}</span><div><strong>{{ member.name }}</strong><small>{{ roleText(member.role) }} · {{ member.phone }}</small></div><span :class="['status-badge', member.is_active ? 'success' : 'muted']">{{ member.is_active ? '正常' : '停用' }}</span></div>
            <fieldset v-if="member.role === 'consultant'" class="consultant-specialties">
              <legend>可承接方向</legend>
              <label v-for="specialty in specialties" :key="specialty.id"><input type="checkbox" :checked="(specialtyDrafts[member.id] || []).includes(specialty.id)" :disabled="specialtySavingId === member.id" @change="toggleSpecialty(member.id, specialty.id, $event.target.checked)">{{ specialty.label }}</label>
              <span class="integrated-hint">同时选择两项即可承接综合申请</span>
              <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!specialtiesChanged(member) || specialtySavingId === member.id" :loading="specialtySavingId === member.id" loading-text="保存中…" @click="saveSpecialties(member)">保存能力</VanButton>
            </fieldset>
            <section v-if="member.role === 'consultant'" class="consultant-workload" :aria-label="`${member.name}的咨询工作量`">
              <p v-if="workloadError" class="workload-error" role="alert">{{ workloadError }}</p>
              <template v-else>
                <p v-if="workloadLoading" class="workload-refreshing" role="status" aria-live="polite">正在更新统计…</p>
                <div class="workload-metrics">
                  <div><span>当前未结</span><strong>{{ workloadByConsultant.get(member.id)?.active_requests ?? 0 }}</strong></div>
                  <div><span>当前名下申请</span><strong>{{ workloadByConsultant.get(member.id)?.total_requests ?? 0 }}</strong></div>
                  <div><span>近 {{ workloadPeriodDays }} 天本人接单</span><strong>{{ workloadByConsultant.get(member.id)?.accepted_in_period ?? 0 }}</strong></div>
                  <div><span>近 {{ workloadPeriodDays }} 天本人交付</span><strong>{{ workloadByConsultant.get(member.id)?.delivered_in_period ?? 0 }}</strong></div>
                </div>
                <section v-if="workloadByConsultant.get(member.id)?.active_by_status?.length" class="consultant-stage-breakdown" :aria-label="`${member.name}的在办阶段分布`">
                  <div class="active-work-heading"><strong>在办阶段</strong><span>按当前负责的申请统计</span></div>
                  <ul>
                    <li v-for="stage in workloadByConsultant.get(member.id).active_by_status" :key="stage.status"><span>{{ serviceRequestStatusText(stage.status) }}</span><strong>{{ stage.request_count }}</strong></li>
                  </ul>
                </section>
                <section class="consultant-delivery-cycle" :aria-label="`${member.name}的名下交付周期统计`">
                  <div class="active-work-heading"><strong>近 {{ workloadPeriodDays }} 天名下交付周期</strong><span>{{ workloadByConsultant.get(member.id)?.delivered_cycle_samples ?? 0 }} 个样本 · 从申请创建到交付</span></div>
                  <div class="delivery-cycle-values"><div><span>P50 中位</span><strong>{{ formatCycleHours(workloadByConsultant.get(member.id)?.delivery_cycle_p50_hours) }}</strong></div><div><span>P90</span><strong>{{ formatCycleHours(workloadByConsultant.get(member.id)?.delivery_cycle_p90_hours) }}</strong></div></div>
                </section>
                <section class="consultant-active-work" :aria-label="`${member.name}的在办申请`">
                  <div class="active-work-heading">
                    <strong>当前在办</strong>
                    <span :class="{ 'has-stale-work': workloadByConsultant.get(member.id)?.stale_active_requests }">
                      超 24 小时未更新 {{ workloadByConsultant.get(member.id)?.stale_active_requests ?? 0 }} 份
                    </span>
                  </div>
                  <ol v-if="workloadByConsultant.get(member.id)?.active_request_preview?.length" class="active-work-list">
                    <li v-for="request in workloadByConsultant.get(member.id).active_request_preview" :key="request.request_id" :class="{ stale: request.is_stale }">
                      <div class="work-event-main">
                        <strong>申请 #{{ request.request_id }} · {{ request.user_name || `用户 #${request.user_id}` }}</strong>
                        <small>{{ consultationTypeLabel(request.consultation_type) }} · {{ serviceRequestStatusText(request.current_status) }}</small>
                        <small>提交 {{ formatDateTime(request.created_at) }} · 最近更新 {{ formatDateTime(request.updated_at) }}</small>
                      </div>
                      <span v-if="request.is_stale" class="active-work-age overdue">闲置 {{ request.idle_hours }} 小时</span>
                      <span v-else class="active-work-age">申请已持续 {{ request.age_hours }} 小时</span>
                    </li>
                  </ol>
                  <p v-else class="workload-empty">暂无在办申请。</p>
                </section>
                <details v-if="workloadByConsultant.get(member.id)?.recent_events?.length" class="consultant-work-events">
                  <summary>最近接单与交付记录</summary>
                  <ol>
                    <li v-for="event in workloadByConsultant.get(member.id).recent_events" :key="`${event.event_type}-${event.request_id}-${event.event_at}`">
                      <div class="work-event-main"><strong>申请 #{{ event.request_id }} · {{ event.user_name }}</strong><small>{{ consultationTypeLabel(event.consultation_type) }} · {{ serviceRequestStatusText(event.current_status) }}</small></div>
                      <span :class="['work-event-type', `work-event-${event.event_type}`]">{{ event.event_type === 'accepted' ? '本人接单' : '本人交付' }}</span>
                      <time>{{ formatDateTime(event.event_at) }}</time>
                    </li>
                  </ol>
                </details>
                <p v-else class="workload-empty">暂无本人接单或交付事件。</p>
                <VanButton class="secondary-button compact-button workload-record-link" type="default" plain native-type="button" @click="$emit('open-requests', member.id)">查看全部申请记录</VanButton>
                <VanButton class="secondary-button compact-button workload-record-link" type="default" plain native-type="button" @click="$emit('open-activity', member.id)">查看完整操作日志</VanButton>
              </template>
            </section>
          </article>
          <p v-if="!staffUsers.length" class="empty-cell">暂无后台成员。</p>
        </div>
      </article>
    </div>
  </section>
</template>
