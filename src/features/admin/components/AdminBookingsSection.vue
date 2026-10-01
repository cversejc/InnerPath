<script setup>
import { formatDateTime, pageCount, statusText } from '../formatters.js'

defineProps({
  bookings: { type: Object, required: true },
  consultants: { type: Array, default: () => [] },
  filters: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 12 }
})

defineEmits(['change-page', 'export', 'open-booking', 'reset-filters', 'search'])
</script>

<template>
  <section class="content-view">
    <div class="view-heading"><div><p class="eyebrow">SERVICE / APPOINTMENTS</p><h2>预约运营</h2><p>从待确认到完成服务，掌握每一次交付节点。</p></div><button class="secondary-button" type="button" @click="$emit('export')"><IconMark name="download" /> <span>导出预约 CSV</span></button></div>
    <div class="filter-bar">
      <input v-model.trim="filters.search" aria-label="搜索用户、手机号或服务" placeholder="搜索用户、手机号或服务" @keyup.enter="$emit('search')">
      <select v-model="filters.status" aria-label="按预约状态筛选"><option value="">全部状态</option><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select>
      <select v-model="filters.consultant_id" aria-label="按咨询师筛选"><option value="">全部咨询师</option><option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select>
      <label class="date-filter"><span>创建自</span><input v-model="filters.date_from" type="date"></label>
      <label class="date-filter"><span>至</span><input v-model="filters.date_to" type="date"></label>
      <button class="primary-button compact-button" type="button" @click="$emit('search')">查询</button>
      <button class="filter-reset" type="button" @click="$emit('reset-filters')">清空</button>
    </div>

    <div v-if="loading" class="list-loading" aria-label="正在加载预约"><i v-for="index in 4" :key="index"></i></div>
    <div v-else class="table-panel">
      <div class="table-meta"><span>共 {{ bookings.total }} 条预约</span><span>点击行查看会议与沟通资料</span></div>
      <div class="admin-table-wrap" tabindex="0" aria-label="数据表格，可横向滚动查看">
        <table class="admin-table booking-table">
          <thead><tr><th>用户</th><th>服务</th><th>期望时间</th><th>状态</th><th>咨询师</th><th>创建时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="booking in bookings.items" :key="booking.id" @click="$emit('open-booking', booking)">
              <td><strong>{{ booking.user_name || `用户 #${booking.user_id}` }}</strong><small>{{ booking.user_phone || booking.contact_phone }}</small></td>
              <td>{{ booking.service_name }}<small>{{ booking.service_price ? `¥${booking.service_price}` : '—' }}</small></td>
              <td>{{ booking.confirmed_date || booking.preferred_time }}<small v-if="booking.confirmed_time">{{ booking.confirmed_time }}</small></td>
              <td><span :class="['status-badge', `booking-${booking.status}`]">{{ statusText(booking.status) }}</span></td>
              <td>{{ booking.consultant_name || '未分配' }}</td>
              <td class="muted-text">{{ formatDateTime(booking.created_at) }}</td>
              <td><button type="button" class="row-open" @click.stop="$emit('open-booking', booking)">查看 →</button></td>
            </tr>
            <tr v-if="!bookings.items.length"><td colspan="7" class="empty-cell">暂无预约记录。</td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination"><span>第 {{ page }} / {{ pageCount(bookings.total, pageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="page <= 1" @click="$emit('change-page', -1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="page >= pageCount(bookings.total, pageSize)" @click="$emit('change-page', 1)">下一页</button></div></div>
    </div>
  </section>
</template>
