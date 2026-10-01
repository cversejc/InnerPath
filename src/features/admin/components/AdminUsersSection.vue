<script setup>
import { formatDateTime, pageCount } from '../formatters.js'

defineProps({
  filters: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 12 },
  users: { type: Object, required: true }
})

const emit = defineEmits([
  'change-page',
  'change-role',
  'export',
  'open-calendar',
  'open-user',
  'reset-filters',
  'reset-password',
  'search',
  'toggle-user'
])

function exportUsers() {
  emit('export', 'users')
}
</script>

<template>
  <section class="content-view">
    <div class="view-heading"><div><p class="eyebrow">PEOPLE / DIRECTORY</p><h2>用户运营</h2><p>从账户状态到成长轨迹，统一查看和维护。</p></div><button class="secondary-button" type="button" @click="exportUsers"><IconMark name="download" /> <span>导出用户 CSV</span></button></div>
    <div class="filter-bar">
      <input v-model.trim="filters.search" aria-label="搜索姓名或手机号" placeholder="搜索姓名或手机号" @keyup.enter="$emit('search')">
      <select v-model="filters.role" aria-label="按角色筛选"><option value="">全部角色</option><option value="user">用户</option><option value="consultant">咨询师</option><option value="admin">管理员</option></select>
      <select v-model="filters.is_active" aria-label="按状态筛选"><option value="">全部状态</option><option :value="true">正常</option><option :value="false">已停用</option></select>
      <label class="date-filter"><span>注册自</span><input v-model="filters.created_from" type="date"></label>
      <label class="date-filter"><span>至</span><input v-model="filters.created_to" type="date"></label>
      <button class="primary-button compact-button" type="button" @click="$emit('search')">查询</button>
      <button class="filter-reset" type="button" @click="$emit('reset-filters')">清空</button>
    </div>

    <div v-if="loading" class="list-loading" aria-label="正在加载用户"><i v-for="index in 4" :key="index"></i></div>
    <div v-else class="table-panel">
      <div class="table-meta"><span>共 {{ users.total }} 个账号</span><span>管理员可见完整运营资料</span></div>
      <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
        <table class="admin-table">
          <thead><tr><th>用户</th><th>角色</th><th>运营概览</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="user in users.items" :key="user.id">
              <td><div class="person-cell"><span class="avatar-mark">{{ user.name?.slice(0, 1) || '人' }}</span><span><strong>{{ user.name }}</strong><small>#{{ user.id }} · {{ user.phone }}</small></span></div></td>
              <td><select :value="user.role" @change="$emit('change-role', user, $event.target.value)"><option value="user">用户</option><option value="consultant">咨询师</option><option value="admin">管理员</option></select></td>
              <td><div class="mini-stats"><span>报 {{ user.report_count }}</span><span>历 {{ user.calendar_count }}</span></div></td>
              <td><span :class="['status-badge', user.is_active ? 'success' : 'muted']">{{ user.is_active ? '正常' : '已停用' }}</span></td>
              <td class="muted-text">{{ formatDateTime(user.last_login_at) }}</td>
              <td><div class="row-actions"><button type="button" @click="$emit('open-user', user)">详情</button><button type="button" @click="$emit('open-calendar', user)">日历</button><button type="button" @click="$emit('reset-password', user)">{{ user.is_active ? '重置密码' : '启用' }}</button><button v-if="user.is_active" type="button" class="danger-action" @click="$emit('toggle-user', user)">停用</button><button v-else type="button" @click="$emit('toggle-user', user)">启用</button></div></td>
            </tr>
            <tr v-if="!users.items.length"><td colspan="6" class="empty-cell">没有找到符合条件的用户。</td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination"><span>第 {{ page }} / {{ pageCount(users.total, pageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="page <= 1" @click="$emit('change-page', -1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="page >= pageCount(users.total, pageSize)" @click="$emit('change-page', 1)">下一页</button></div></div>
    </div>
  </section>
</template>
