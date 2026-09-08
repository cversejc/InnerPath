<template>
  <div class="staff-shell">
    <BrandNav />
    <main class="staff-main">
      <div class="staff-heading">
        <div>
          <p class="section-kicker">ADMIN CONSOLE</p>
          <h1>辰鉴管理后台</h1>
          <p>管理账户、预约与用户的个性化决策日历。</p>
        </div>
        <button class="secondary-button" type="button" @click="refreshAll">刷新数据</button>
      </div>

      <div class="staff-tabs">
        <button v-for="tab in tabs" :key="tab.id" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
          {{ tab.label }}
        </button>
      </div>

      <p v-if="message" class="console-message">{{ message }}</p>

      <section v-if="activeTab === 'users'" class="console-card paper-card">
        <div class="section-row">
          <div>
            <h2>用户管理</h2>
            <p>共 {{ users.total }} 个账号</p>
          </div>
          <div class="inline-form">
            <input v-model.trim="search" placeholder="姓名或手机号">
            <button class="primary-button" type="button" @click="searchUsers">搜索</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>用户</th><th>手机号</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="user in users.items" :key="user.id">
                <td>{{ user.name }}<small>#{{ user.id }}</small></td>
                <td>{{ user.phone }}</td>
                <td>
                  <select :value="user.role" @change="changeRole(user, $event.target.value)">
                    <option value="user">用户</option>
                    <option value="consultant">咨询师</option>
                    <option value="admin">管理员</option>
                  </select>
                </td>
                <td><span :class="['status-pill', user.is_active ? 'active' : 'inactive']">{{ user.is_active ? '正常' : '已停用' }}</span></td>
                <td class="action-cell">
                  <button class="text-action" type="button" @click="selectUserDetail(user)">详情</button>
                  <button class="text-action" type="button" @click="selectCalendarUser(user)">维护日历</button>
                  <button class="text-action" type="button" @click="resetUserPassword(user)">重置密码</button>
                  <button class="text-action" type="button" @click="toggleUser(user)">{{ user.is_active ? '停用' : '启用' }}</button>
                </td>
              </tr>
              <tr v-if="!users.items.length"><td colspan="5" class="empty-cell">暂无用户</td></tr>
            </tbody>
          </table>
        </div>
        <div class="table-footer">
          <span>第 {{ userPage }} 页 · 共 {{ users.total }} 个账号</span>
          <div class="inline-form">
            <button class="secondary-button" type="button" :disabled="userPage <= 1" @click="changeUserPage(-1)">上一页</button>
            <button class="secondary-button" type="button" :disabled="userPage * userPageSize >= users.total" @click="changeUserPage(1)">下一页</button>
          </div>
        </div>
        <div v-if="userDetail" class="user-detail-card">
          <div class="section-row"><h3>{{ userDetail.name }} 的账户详情</h3><button class="text-action" type="button" @click="userDetail = null">关闭</button></div>
          <dl class="detail-grid">
            <div><dt>账号 ID</dt><dd>#{{ userDetail.id }}</dd></div>
            <div><dt>手机号</dt><dd>{{ userDetail.phone }}</dd></div>
            <div><dt>角色</dt><dd>{{ userDetail.role }}</dd></div>
            <div><dt>状态</dt><dd>{{ userDetail.is_active ? '正常' : '已停用' }}</dd></div>
            <div><dt>注册时间</dt><dd>{{ formatDateTime(userDetail.created_at) }}</dd></div>
            <div><dt>最近登录</dt><dd>{{ formatDateTime(userDetail.last_login_at) }}</dd></div>
          </dl>
        </div>
      </section>

      <section v-if="activeTab === 'bookings'" class="console-card paper-card">
        <div class="section-row">
          <div><h2>预约管理</h2><p>确认时间、分配咨询师并维护会议资料。</p></div>
          <button class="secondary-button" type="button" @click="loadBookings">刷新预约</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>预约</th><th>用户</th><th>服务</th><th>状态</th><th>咨询师</th><th>会议资料</th><th>保存</th></tr></thead>
            <tbody>
              <tr v-for="booking in bookings.items" :key="booking.id">
                <td>#{{ booking.id }}<small>{{ booking.preferred_time }}</small></td>
                <td>#{{ booking.user_id }}</td>
                <td>{{ booking.service_name }}</td>
                <td>
                  <select v-model="booking.status">
                    <option value="pending">待确认</option>
                    <option value="confirmed">已确认</option>
                    <option value="completed">已完成</option>
                    <option value="cancelled">已取消</option>
                  </select>
                </td>
                <td>
                  <select v-model="booking.consultant_id">
                    <option :value="null">未分配</option>
                    <option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option>
                  </select>
                </td>
                <td class="meeting-fields">
                  <input v-model.trim="booking.meeting_url" placeholder="会议链接">
                  <input v-model.trim="booking.meeting_notes" placeholder="会议备注">
                </td>
                <td><button class="text-action" type="button" @click="saveBooking(booking)">保存</button></td>
              </tr>
              <tr v-if="!bookings.items.length"><td colspan="7" class="empty-cell">暂无预约</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'calendar'" class="console-grid">
        <div class="console-card paper-card">
          <h2>选择用户</h2>
          <p class="card-hint">从用户列表选择需要维护日历的账号。</p>
          <div class="user-picker">
            <button v-for="user in users.items" :key="user.id" :class="{ selected: selectedUser?.id === user.id }" type="button" @click="selectCalendarUser(user)">
              <strong>{{ user.name }}</strong><span>#{{ user.id }} · {{ user.phone }}</span>
            </button>
          </div>
        </div>
        <div class="console-card paper-card">
          <div class="section-row"><div><h2>个性化日历</h2><p>{{ selectedUser ? `${selectedUser.name} 的日历` : '请先选择用户' }}</p></div></div>
          <form v-if="selectedUser" class="calendar-form" @submit.prevent="saveCalendar">
            <input v-model.trim="calendarForm.title" required placeholder="日历标题">
            <textarea v-model="calendarForm.entriesJson" rows="9" placeholder='条目 JSON，例如：[{
  "entry_date": "2026-09-07",
  "keyword": "观察",
  "summary": "适合准备",
  "suitable": ["记录想法"],
  "unsuitable": ["做最终决策"]
}]'></textarea>
            <div class="action-row">
              <button class="primary-button" type="submit">{{ editingCalendarId ? '保存日历' : '创建草稿' }}</button>
              <button v-if="editingCalendarId" class="secondary-button" type="button" @click="cancelCalendarEdit">取消编辑</button>
            </div>
          </form>
          <div v-if="selectedUser && !calendars.length" class="empty-cell">暂无日历，请创建草稿。</div>
          <article v-for="calendar in calendars" :key="calendar.id" class="calendar-admin-card">
            <div><strong>{{ calendar.title }}</strong><span :class="['status-pill', calendar.status]">{{ calendar.status }}</span></div>
            <p>{{ calendar.entries.length }} 个日期条目 · 更新于 {{ formatDate(calendar.updated_at) }}</p>
            <ul v-if="calendar.entries.length" class="calendar-preview">
              <li v-for="entry in calendar.entries.slice(0, 3)" :key="entry.id">{{ entry.entry_date }} · {{ entry.keyword || entry.status_label || '未命名条目' }}</li>
            </ul>
            <div class="action-row">
              <button class="text-action" type="button" @click="editCalendar(calendar)">编辑</button>
              <button v-if="calendar.status === 'draft'" class="text-action" type="button" @click="publishCalendar(calendar)">发布</button>
              <button v-if="calendar.status === 'published'" class="text-action" type="button" @click="archiveCalendar(calendar)">归档</button>
            </div>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'staff'" class="console-card paper-card staff-invite-card">
        <h2>邀请后台成员</h2>
        <p>邀请链接只展示一次，请通过安全渠道发送给对方。</p>
        <form class="inline-form" @submit.prevent="inviteStaff">
          <input v-model.trim="inviteForm.phone" required maxlength="11" placeholder="手机号">
          <select v-model="inviteForm.role"><option value="consultant">咨询师</option><option value="admin">管理员</option></select>
          <button class="primary-button" type="submit">生成邀请</button>
        </form>
        <div v-if="inviteToken" class="invite-result">
          <strong>邀请令牌</strong>
          <code>{{ inviteToken }}</code>
          <router-link :to="{ path: '/auth/invite', query: { token: inviteToken } }">打开邀请页面</router-link>
        </div>
      </section>

      <section v-if="activeTab === 'audit'" class="console-card paper-card">
        <div class="section-row">
          <div><h2>审计记录</h2><p>角色、账号状态、预约分配和日历发布等后台操作。</p></div>
          <button class="secondary-button" type="button" @click="loadAuditLogs">刷新记录</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>时间</th><th>操作</th><th>资源</th><th>操作者</th><th>详情</th></tr></thead>
            <tbody>
              <tr v-for="log in auditLogs.items" :key="log.id">
                <td>{{ formatDateTime(log.created_at) }}</td>
                <td>{{ log.action }}</td>
                <td>{{ log.resource_type }}{{ log.resource_id ? ` #${log.resource_id}` : '' }}</td>
                <td>{{ log.actor_user_id || '系统' }}</td>
                <td class="audit-details">{{ log.details || '—' }}</td>
              </tr>
              <tr v-if="!auditLogs.items.length"><td colspan="5" class="empty-cell">暂无审计记录</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import {
  archiveAdminCalendar,
  createAdminCalendar,
  createStaffInvite,
  getAdminBookings,
  getAdminAuditLogs,
  getAdminUser,
  getAdminCalendars,
  getAdminUsers,
  publishAdminCalendar,
  resetAdminUserPassword,
  updateAdminBooking,
  updateAdminCalendar,
  updateAdminUserRole,
  updateAdminUserStatus
} from '../utils/businessService'

export default {
  name: 'AdminConsole',
  data() {
    return {
      activeTab: 'users',
      tabs: [
        { id: 'users', label: '用户管理' },
        { id: 'bookings', label: '预约管理' },
        { id: 'calendar', label: '用户日历' },
        { id: 'staff', label: '后台成员' },
        { id: 'audit', label: '审计记录' }
      ],
      users: { total: 0, items: [] },
      consultantUsers: [],
      bookings: { total: 0, items: [] },
      auditLogs: { total: 0, items: [] },
      search: '',
      userPage: 1,
      userPageSize: 20,
      userDetail: null,
      selectedUser: null,
      calendars: [],
      calendarForm: { title: '', entriesJson: '[]' },
      editingCalendarId: null,
      inviteForm: { phone: '', role: 'consultant' },
      inviteToken: '',
      message: ''
    }
  },
  computed: {
    consultants() {
      return this.consultantUsers
    }
  },
  mounted() {
    this.refreshAll()
  },
  methods: {
    async refreshAll() {
      await Promise.all([this.loadUsers(), this.loadConsultants(), this.loadBookings(), this.loadAuditLogs()])
      if (this.selectedUser) await this.loadCalendars()
    },
    async loadUsers() {
      try {
        this.users = await getAdminUsers({
          search: this.search || undefined,
          page: this.userPage,
          size: this.userPageSize
        })
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async searchUsers() {
      this.userPage = 1
      await this.loadUsers()
    },
    async changeUserPage(offset) {
      const nextPage = this.userPage + offset
      if (nextPage < 1 || nextPage > Math.ceil(this.users.total / this.userPageSize)) return
      this.userPage = nextPage
      await this.loadUsers()
    },
    async selectUserDetail(user) {
      try {
        this.userDetail = await getAdminUser(user.id)
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async loadBookings() {
      try {
        this.bookings = await getAdminBookings()
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async loadConsultants() {
      try {
        const response = await getAdminUsers({ role: 'consultant', is_active: true, size: 100 })
        this.consultantUsers = response.items || []
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async loadAuditLogs() {
      try {
        this.auditLogs = await getAdminAuditLogs({ size: 100 })
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async toggleUser(user) {
      try {
        await updateAdminUserStatus(user.id, !user.is_active)
        user.is_active = !user.is_active
        await this.loadConsultants()
        this.message = '用户状态已更新'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async resetUserPassword(user) {
      const newPassword = window.prompt(`为 ${user.name} 设置新密码（至少8位）`)
      if (newPassword === null) return
      if (newPassword.length < 8) {
        this.message = '新密码至少需要8位'
        return
      }
      try {
        await resetAdminUserPassword(user.id, newPassword)
        this.message = '用户密码已重置，原会话已失效'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async changeRole(user, role) {
      try {
        await updateAdminUserRole(user.id, role)
        user.role = role
        await this.loadConsultants()
        this.message = '用户角色已更新'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async saveBooking(booking) {
      try {
        const updated = await updateAdminBooking(booking.id, {
          status: booking.status,
          consultant_id: booking.consultant_id || null,
          meeting_url: booking.meeting_url || null,
          meeting_notes: booking.meeting_notes || null
        })
        Object.assign(booking, updated)
        this.message = '预约已更新'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async selectCalendarUser(user) {
      this.selectedUser = user
      this.activeTab = 'calendar'
      this.cancelCalendarEdit()
      await this.loadCalendars()
    },
    async loadCalendars() {
      if (!this.selectedUser) return
      try {
        const response = await getAdminCalendars(this.selectedUser.id)
        this.calendars = response.items || []
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async saveCalendar() {
      try {
        const entries = JSON.parse(this.calendarForm.entriesJson || '[]')
        const payload = { title: this.calendarForm.title, entries }
        if (this.editingCalendarId) {
          await updateAdminCalendar(this.editingCalendarId, payload)
          this.message = '日历草稿已更新'
        } else {
          await createAdminCalendar(this.selectedUser.id, payload)
          this.message = '日历草稿已创建'
        }
        this.cancelCalendarEdit()
        await this.loadCalendars()
      } catch (error) {
        this.message = error instanceof SyntaxError ? '条目 JSON 格式不正确' : this.errorText(error)
      }
    },
    editCalendar(calendar) {
      this.editingCalendarId = calendar.id
      this.calendarForm = {
        title: calendar.title,
        entriesJson: JSON.stringify(calendar.entries || [], null, 2)
      }
    },
    cancelCalendarEdit() {
      this.editingCalendarId = null
      this.calendarForm = { title: '', entriesJson: '[]' }
    },
    async publishCalendar(calendar) {
      try {
        const updated = await publishAdminCalendar(calendar.id)
        Object.assign(calendar, updated)
        this.message = '日历已发布'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async archiveCalendar(calendar) {
      try {
        const updated = await archiveAdminCalendar(calendar.id)
        Object.assign(calendar, updated)
        this.message = '日历已归档'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async inviteStaff() {
      try {
        const response = await createStaffInvite(this.inviteForm.phone, this.inviteForm.role)
        this.inviteToken = response.token
        this.message = '邀请已生成'
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
    },
    formatDateTime(value) {
      return value ? new Date(value).toLocaleString('zh-CN') : '—'
    },
    errorText(error) {
      return error.response?.data?.detail || '请求失败，请稍后重试'
    }
  }
}
</script>

<style scoped>
.staff-shell { min-height: 100vh; background: #f7f0e6; }
.staff-main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 72px 0; }
.staff-heading, .section-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.staff-heading h1 { margin: 8px 0; font-size: clamp(32px, 6vw, 56px); }
.staff-heading p:not(.section-kicker), .console-card p, .card-hint { color: #756a60; line-height: 1.7; }
.staff-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin: 34px 0 22px; }
.staff-tabs button { border: 1px solid rgba(80, 54, 32, .15); border-radius: 999px; background: rgba(255, 250, 240, .75); padding: 10px 16px; cursor: pointer; }
.staff-tabs button.active { border-color: #b85c50; background: #fff0df; color: #8f352f; font-weight: 800; }
.console-message { margin: 12px 0; color: #8f352f; }
.console-card { padding: 26px; }
.console-card h2 { margin: 0 0 6px; color: #3b2d24; }
.inline-form { display: flex; flex-wrap: wrap; gap: 8px; }
.inline-form input, .inline-form select, .calendar-form input, .calendar-form textarea { border: 1px solid rgba(80, 54, 32, .16); border-radius: 9px; background: #fffaf0; padding: 11px 12px; font: inherit; }
.table-wrap { overflow-x: auto; margin-top: 22px; }
.table-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 16px; color: #756a60; font-size: 13px; }
table { width: 100%; border-collapse: collapse; min-width: 760px; }
th, td { padding: 13px 12px; border-bottom: 1px solid rgba(80, 54, 32, .1); text-align: left; vertical-align: middle; }
th { color: #8f352f; font-size: 12px; letter-spacing: .08em; }
td small { display: block; margin-top: 4px; color: #897a6c; }
td select { max-width: 150px; border: 1px solid rgba(80, 54, 32, .16); border-radius: 7px; background: #fffaf0; padding: 7px; }
.action-cell { white-space: nowrap; }
.text-action { border: 0; background: transparent; color: #8f352f; cursor: pointer; font-weight: 800; }
.meeting-fields { display: grid; gap: 6px; min-width: 190px; }
.meeting-fields input { width: 180px; border: 1px solid rgba(80, 54, 32, .16); border-radius: 7px; background: #fffaf0; padding: 7px; font: inherit; }
.status-pill { display: inline-block; border-radius: 999px; padding: 4px 9px; background: #eee4d5; color: #756a60; font-size: 12px; }
.status-pill.active, .status-pill.published { background: #e1f0dc; color: #39724e; }
.status-pill.inactive, .status-pill.archived { background: #f2dddd; color: #8f352f; }
.status-pill.draft { background: #fff0c9; color: #89621a; }
.empty-cell { padding: 32px; color: #897a6c; text-align: center; }
.console-grid { display: grid; grid-template-columns: minmax(250px, .7fr) minmax(0, 1.3fr); gap: 18px; }
.user-picker { display: grid; gap: 8px; margin-top: 18px; max-height: 520px; overflow: auto; }
.user-picker button { display: grid; gap: 3px; border: 1px solid rgba(80, 54, 32, .12); border-radius: 10px; background: #fffaf0; padding: 12px; text-align: left; cursor: pointer; }
.user-picker button.selected { border-color: #b85c50; background: #fff0df; }
.user-picker span { color: #897a6c; font-size: 12px; }
.calendar-form { display: grid; gap: 10px; margin: 18px 0 20px; }
.calendar-form textarea { resize: vertical; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.calendar-admin-card { margin-top: 12px; border-top: 1px solid rgba(80, 54, 32, .1); padding-top: 14px; }
.calendar-admin-card > div:first-child { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.calendar-admin-card p { margin: 6px 0; font-size: 13px; }
.calendar-preview { margin: 0 0 12px; padding-left: 18px; color: #756a60; font-size: 13px; line-height: 1.7; }
.audit-details { max-width: 360px; white-space: pre-wrap; word-break: break-word; }
.user-detail-card { margin-top: 22px; border-top: 1px solid rgba(80, 54, 32, .1); padding-top: 18px; }
.user-detail-card h3 { margin: 0; color: #3b2d24; }
.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 20px; margin: 16px 0 0; }
.detail-grid div { display: grid; grid-template-columns: 76px 1fr; gap: 10px; }
.detail-grid dt { color: #897a6c; }
.detail-grid dd { margin: 0; color: #3b2d24; word-break: break-word; }
.action-row { display: flex; gap: 14px; }
.staff-invite-card { max-width: 760px; }
.invite-result { display: grid; gap: 8px; margin-top: 22px; padding: 16px; border: 1px dashed rgba(184, 92, 80, .45); border-radius: 10px; background: #fff4e9; }
.invite-result code { overflow-wrap: anywhere; color: #8f352f; }
.invite-result a { color: #8f352f; font-weight: 800; }
@media (max-width: 800px) { .staff-main { padding: 42px 0; } .staff-heading, .section-row { align-items: flex-start; flex-direction: column; } .console-grid { grid-template-columns: 1fr; } .console-card { padding: 20px 16px; } .table-footer { align-items: flex-start; flex-direction: column; } .detail-grid { grid-template-columns: 1fr; } }
</style>
