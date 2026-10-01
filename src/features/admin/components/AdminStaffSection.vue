<script setup>
import { roleText } from '../formatters.js'

defineProps({
  inviteForm: { type: Object, required: true },
  inviteSaving: { type: Boolean, default: false },
  inviteToken: { type: String, default: '' },
  staffLoading: { type: Boolean, default: false },
  staffUsers: { type: Array, default: () => [] }
})

defineEmits(['invite'])
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
          <button class="primary-button" type="submit" :disabled="inviteSaving" :aria-busy="inviteSaving">{{ inviteSaving ? '生成中…' : '生成邀请链接' }}</button>
        </form>
        <div v-if="inviteToken" class="invite-result" role="status" aria-live="polite"><span>本次令牌</span><code>{{ inviteToken }}</code><router-link :to="{ path: '/auth/invite', query: { token: inviteToken } }">打开邀请页面 →</router-link></div>
      </article>

      <article class="panel-surface team-card">
        <div class="panel-heading"><div><p class="eyebrow">CURRENT TEAM</p><h3>当前成员</h3></div><span>{{ staffUsers.length }}</span></div>
        <div v-if="staffLoading" class="list-loading" aria-label="正在加载成员"><i v-for="index in 4" :key="index"></i></div>
        <div v-else class="team-list"><div v-for="member in staffUsers" :key="member.id" class="team-row"><span class="avatar-mark">{{ member.name?.slice(0, 1) || '人' }}</span><div><strong>{{ member.name }}</strong><small>{{ roleText(member.role) }} · {{ member.phone }}</small></div><span :class="['status-badge', member.is_active ? 'success' : 'muted']">{{ member.is_active ? '正常' : '停用' }}</span></div><p v-if="!staffUsers.length" class="empty-cell">暂无后台成员。</p></div>
      </article>
    </div>
  </section>
</template>
