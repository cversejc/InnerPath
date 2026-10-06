<script setup>
import { reactive, watch } from 'vue'
import { Button as VanButton } from 'vant'
import { roleText } from '../formatters.js'

const props = defineProps({
  inviteForm: { type: Object, required: true },
  inviteSaving: { type: Boolean, default: false },
  inviteToken: { type: String, default: '' },
  specialtySavingId: { type: Number, default: null },
  staffLoading: { type: Boolean, default: false },
  staffUsers: { type: Array, default: () => [] }
})

const emit = defineEmits(['invite', 'update-specialties'])
const specialties = [
  { id: 'metaphysics', label: '命理' },
  { id: 'psychology', label: '心理' }
]
const specialtyDrafts = reactive({})

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
        <div class="panel-heading"><div><p class="eyebrow">CURRENT TEAM</p><h3>当前成员</h3></div><span>{{ staffUsers.length }}</span></div>
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
          </article>
          <p v-if="!staffUsers.length" class="empty-cell">暂无后台成员。</p>
        </div>
      </article>
    </div>
  </section>
</template>
