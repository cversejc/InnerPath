<template>
  <div class="staff-shell">
    <BrandNav />
    <main class="staff-main">
      <div class="staff-heading">
        <div>
          <p class="section-kicker">STAFF WORKSPACE</p>
          <h1>咨询工作台</h1>
          <p>查看分配给你的预约，并在需要时补充会议记录。</p>
        </div>
        <button class="secondary-button" type="button" @click="loadBookings">刷新预约</button>
      </div>

      <p v-if="message" class="console-message" role="status" aria-live="polite">{{ message }}</p>
      <section class="staff-workspace-grid">
        <div class="console-card paper-card">
          <div class="section-row"><div><h2>我的预约</h2><p>仅展示当前账号被分配的预约。</p></div></div>
          <div class="booking-list" aria-label="分配给我的预约">
            <button v-for="booking in bookings.items" :key="booking.id" class="booking-item" :class="{ selected: selectedBooking?.id === booking.id }" type="button" :aria-pressed="selectedBooking?.id === booking.id" @click="selectBooking(booking)">
              <span>#{{ booking.id }} · {{ booking.service_name }}</span>
              <small>用户 #{{ booking.user_id }} · {{ statusText(booking.status) }}</small>
            </button>
            <div v-if="!bookings.items.length" class="empty-cell">暂无分配的预约</div>
          </div>
        </div>

        <div class="console-card paper-card">
          <div v-if="selectedBooking">
            <h2>预约详情 #{{ selectedBooking.id }}</h2>
            <dl class="detail-list">
              <div><dt>服务</dt><dd>{{ selectedBooking.service_name }}</dd></div>
              <div><dt>期望时间</dt><dd>{{ selectedBooking.preferred_time }}</dd></div>
              <div><dt>联系方式</dt><dd>{{ selectedBooking.contact_phone }}</dd></div>
              <div><dt>关注议题</dt><dd>{{ (selectedBooking.topics || []).join('、') || '—' }}</dd></div>
            </dl>
            <form class="staff-form" @submit.prevent="saveBooking">
              <label>预约状态<select v-model="editor.status"><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></label>
              <label>会议链接<input v-model.trim="editor.meeting_url" type="url" placeholder="可选"></label>
              <label>会议记录<textarea v-model="editor.meeting_notes" rows="6" placeholder="记录本次沟通要点"></textarea></label>
              <button class="primary-button" type="submit" :disabled="saving" :aria-busy="saving">{{ saving ? '保存中…' : '保存记录' }}</button>
            </form>
            <div class="related-data">
              <div><h3>用户报告</h3><p v-if="!reports.length">暂无报告或无访问权限</p><ul v-else><li v-for="report in reports" :key="report.id">{{ report.title }} · {{ formatDate(report.created_at) }}</li></ul></div>
              <div><h3>已发布日历</h3><p v-if="!calendars.length">暂无日历</p><ul v-else><li v-for="calendar in calendars" :key="calendar.id">{{ calendar.title }} · {{ calendar.entries.length }} 天</li></ul></div>
            </div>
          </div>
          <div v-else class="empty-state"><IconMark class="empty-icon" name="compass" /><p>选择左侧预约查看详情</p></div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { getStaffBookings, getStaffUserCalendars, getStaffUserReports, updateStaffBooking } from '../utils/businessService'

export default {
  name: 'StaffConsole',
  data() {
    return {
      bookings: { total: 0, items: [] },
      selectedBooking: null,
      editor: { status: 'pending', meeting_url: '', meeting_notes: '' },
      saving: false,
      reports: [],
      calendars: [],
      message: ''
    }
  },
  mounted() {
    this.loadBookings()
  },
  methods: {
    async loadBookings() {
      try {
        this.bookings = await getStaffBookings()
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async selectBooking(booking) {
      this.selectedBooking = booking
      this.editor = {
        status: booking.status,
        meeting_url: booking.meeting_url || '',
        meeting_notes: booking.meeting_notes || ''
      }
      try {
        const [reports, calendars] = await Promise.all([
          getStaffUserReports(booking.user_id),
          getStaffUserCalendars(booking.user_id)
        ])
        this.reports = reports.items || []
        this.calendars = calendars.items || []
      } catch (error) {
        this.reports = []
        this.calendars = []
        this.message = this.errorText(error)
      }
    },
    async saveBooking() {
      if (!this.selectedBooking || this.saving) return
      this.saving = true
      try {
        const updated = await updateStaffBooking(this.selectedBooking.id, this.editor)
        Object.assign(this.selectedBooking, updated)
        this.message = '会议记录已保存'
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.saving = false
      }
    },
    statusText(status) {
      return { pending: '待确认', confirmed: '已确认', completed: '已完成', cancelled: '已取消' }[status] || status
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
    },
    errorText(error) {
      return error.response?.data?.detail || '请求失败，请稍后重试'
    }
  }
}
</script>

<style scoped>
.staff-shell { min-height: 100dvh; background: var(--paper, #f8f1e6); }
.staff-main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 72px 0; }
.staff-heading, .section-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.staff-heading h1 { margin: 8px 0; font-size: clamp(32px, 6vw, 56px); }
.staff-heading p:not(.section-kicker), .console-card p { color: var(--muted, #7d6653); line-height: 1.7; }
.staff-workspace-grid { display: grid; grid-template-columns: minmax(250px, .7fr) minmax(0, 1.3fr); gap: 18px; margin-top: 32px; }
.console-card { padding: 26px; }
.console-card h2 { margin: 0 0 6px; color: #3b2d24; }
.booking-list { display: grid; gap: 8px; margin-top: 18px; }
.booking-item { display: grid; gap: 5px; border: 1px solid rgba(80, 54, 32, .12); border-radius: 10px; background: #fffaf0; padding: 13px; text-align: left; cursor: pointer; }
.booking-item.selected { border-color: #b85c50; background: #fff0df; }
.booking-item small { color: var(--muted, #7d6653); }
.empty-cell, .empty-state { padding: 32px 12px; color: var(--muted, #7d6653); text-align: center; }
.empty-icon { width: 42px; height: 42px; margin: 0 auto 14px; color: #b85c50; }
.detail-list { display: grid; gap: 10px; margin: 22px 0; }
.detail-list div { display: grid; grid-template-columns: 90px 1fr; gap: 12px; }
.detail-list dt { color: var(--muted, #7d6653); }
.detail-list dd { margin: 0; color: #3b2d24; }
.staff-form { display: grid; gap: 13px; }
.staff-form label { display: grid; gap: 6px; color: #51463d; font-weight: 700; }
.staff-form input, .staff-form select, .staff-form textarea { border: 1px solid rgba(80, 54, 32, .16); border-radius: 9px; background: #fffaf0; padding: 11px 12px; font: inherit; }
.staff-form textarea { resize: vertical; }
.related-data { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 28px; border-top: 1px solid rgba(80, 54, 32, .1); padding-top: 20px; }
.related-data h3 { margin: 0 0 8px; font-size: 16px; }
.related-data p, .related-data li { font-size: 13px; }
.related-data ul { margin: 0; padding-left: 18px; color: var(--muted, #7d6653); }
.console-message { margin: 18px 0; color: #8f352f; }
@media (max-width: 800px) {
  .staff-main {
    width: calc(100% - 32px);
    padding: 24px 0 calc(92px + var(--safe-bottom, 0px));
  }

  .staff-heading,
  .section-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .staff-heading {
    gap: 12px;
  }

  .staff-heading h1 {
    font-size: clamp(28px, 9vw, 38px);
    line-height: 1.12;
  }

  .staff-heading .secondary-button {
    width: 100%;
  }

  .staff-workspace-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 18px;
  }

  .console-card {
    padding: 16px 13px;
    border-radius: 14px;
  }

  .console-card h2 {
    font-size: 21px;
  }

  .booking-list {
    margin-top: 14px;
  }

  .booking-item {
    min-height: 52px;
    padding: 12px;
  }

  .staff-form input,
  .staff-form select,
  .staff-form textarea {
    min-height: 48px;
    font-size: 16px;
  }

  .staff-form textarea {
    min-height: 132px;
  }

  .staff-form .primary-button {
    width: 100%;
  }

  .detail-list {
    gap: 8px;
    margin: 16px 0;
  }

  .related-data {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 20px;
    padding-top: 16px;
  }

  .related-data p,
  .related-data li {
    font-size: 14px;
  }
}

/* 按钮专项：员工工作台的刷新、保存与列表选择保持同一触控节奏。 */
.staff-heading .secondary-button,
.staff-form .primary-button {
  min-height: var(--button-height, 46px);
  border-radius: var(--button-radius, 13px);
}

.booking-item {
  min-height: 52px;
}

@media (max-width: 1023px) {
  .staff-main {
    padding-bottom: calc(92px + var(--safe-bottom, 0px));
  }
}

</style>
