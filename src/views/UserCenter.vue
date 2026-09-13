<template>
  <div class="user-center">
    <BrandNav />

    <!-- 用户信息头部 -->
    <section class="user-header">
      <div class="container user-header-inner">
        <div class="user-info">
          <div class="user-avatar">{{ userName.charAt(0) }}</div>
          <div class="user-details">
            <h2>{{ userName }}</h2>
            <p class="user-type">{{ userType }}</p>
          </div>
        </div>
        <router-link v-if="isAdmin" to="/admin" class="admin-entry-link">
          <span>进入管理中心</span>
          <IconMark name="arrow" />
        </router-link>
      </div>
    </section>

    <!-- 主内容区 -->
    <section class="user-content">
      <div class="container">
        <p v-if="loading" class="dashboard-message" role="status" aria-live="polite">正在打开你的个人空间…</p>
        <p v-if="message" class="dashboard-message" role="status" aria-live="polite">{{ message }}</p>
        <div class="content-layout">
          <!-- 侧边栏 -->
          <aside class="sidebar">
            <nav class="sidebar-nav" role="tablist" aria-label="个人空间分区">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                :id="`user-tab-${tab.id}`"
                type="button"
                class="nav-item"
                :class="{ active: activeTab === tab.id }"
                role="tab"
                :aria-selected="activeTab === tab.id"
                :aria-controls="`user-panel-${tab.id}`"
                :tabindex="activeTab === tab.id ? 0 : -1"
                @click="selectTab(tab.id)"
                @keydown.left.prevent="moveTab(-1)"
                @keydown.right.prevent="moveTab(1)"
              >
                <IconMark class="nav-icon" :name="tab.icon" />
                <span class="nav-label">{{ tab.label }}</span>
              </button>
            </nav>
          </aside>

          <!-- 内容区 -->
          <main class="main-content">
            <!-- 我的报告 -->
            <div v-if="activeTab === 'reports'" id="user-panel-reports" class="content-section" role="tabpanel" aria-labelledby="user-tab-reports" tabindex="0">
              <h3 class="section-title">报告</h3>
              <div v-if="reports.length === 0" class="empty-state">
                <IconMark class="empty-icon" name="document" />
                <p>暂无报告</p>
                <button type="button" class="btn-action" @click="goToAssessment">生成说明书</button>
              </div>
              <div v-else class="reports-list">
                <div v-for="report in reports" :key="report.id" class="report-card">
                  <div class="report-header">
                    <h4>{{ report.title }}</h4>
                    <span class="report-date">{{ report.date }}</span>
                  </div>
                  <div class="report-preview">
                    <div class="preview-item">
                      <strong>个人属性：</strong>{{ report.energyType }}
                    </div>
                    <div class="preview-item">
                      <strong>核心特质：</strong>{{ report.coreTraits }}
                    </div>
                  </div>
                  <div class="report-actions">
                    <button type="button" class="btn-view" @click="viewReport(report.id)">查看完整报告</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 我的决策日历 -->
            <div v-if="activeTab === 'calendar'" id="user-panel-calendar" class="content-section" role="tabpanel" aria-labelledby="user-tab-calendar" tabindex="0">
              <h3 class="section-title">决策日历</h3>
              <div class="calendar-access-card">
                <div class="calendar-access-mark" aria-hidden="true">辰</div>
                <div>
                  <span class="calendar-access-kicker">PERSONAL TIMEZONE</span>
                  <h4>把报告里的洞察带回每天</h4>
                  <p>查看阶段行动节奏，记录真实发生的事。</p>
                </div>
                <button type="button" class="btn-action" @click="goToCalendar">打开决策日历</button>
              </div>
            </div>

            <!-- 账户设置 -->
            <div v-if="activeTab === 'settings'" id="user-panel-settings" class="content-section" role="tabpanel" aria-labelledby="user-tab-settings" tabindex="0">
              <h3 class="section-title">账户设置</h3>
              <form class="settings-form">
                <div class="form-group">
                  <label>姓名</label>
                  <input v-model="settings.name" type="text" autocomplete="name">
                </div>
                <fieldset class="form-group choice-fieldset">
                  <legend>性别</legend>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input v-model="settings.gender" type="radio" value="male">
                      <span>男</span>
                    </label>
                    <label class="radio-label">
                      <input v-model="settings.gender" type="radio" value="female">
                      <span>女</span>
                    </label>
                  </div>
                </fieldset>
                <div class="form-group">
                  <label>联系方式</label>
                  <input v-model="settings.contact" type="tel" autocomplete="tel" readonly>
                </div>
                <div class="form-group">
                  <label>出生日期</label>
                  <input v-model="settings.birthDate" type="date">
                </div>
                <button type="button" class="btn-save" :disabled="savingSettings" :aria-busy="savingSettings" @click="saveSettings">{{ savingSettings ? '保存中…' : '保存设置' }}</button>
              </form>
              <form class="password-form" @submit.prevent="savePassword">
                <h4>修改密码</h4>
                <div class="form-group">
                  <label>当前密码</label>
                  <input v-model="passwordForm.current" type="password" minlength="8" maxlength="128" required autocomplete="current-password">
                </div>
                <div class="form-group">
                  <label>新密码</label>
                  <input v-model="passwordForm.next" type="password" minlength="8" maxlength="128" required autocomplete="new-password">
                </div>
                <button type="submit" class="btn-save" :disabled="savingPassword" :aria-busy="savingPassword">{{ savingPassword ? '更新中…' : '更新密码' }}</button>
              </form>
              <section class="account-actions" aria-labelledby="account-actions-title">
                <div>
                  <h4 id="account-actions-title">账号操作</h4>
                  <p>退出当前设备上的辰鉴账号。</p>
                </div>
                <button type="button" class="btn-logout" :disabled="loggingOut" :aria-busy="loggingOut" @click="handleLogout">
                  <IconMark name="logout" />
                  {{ loggingOut ? '退出中…' : '退出登录' }}
                </button>
              </section>
            </div>
          </main>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { changePassword, getCurrentUser, updateUserProfile } from '../utils/authService'
import { getUserReports } from '../utils/aiService'
import { hasRole, logout as logoutUser } from '../stores/auth'

export default {
  name: 'UserCenter',
  data() {
    return {
      userName: '用户',
      userType: '成长探索者',
      activeTab: 'reports',
      loading: true,
      message: '',
      tabs: [
        { id: 'reports', icon: 'reports', label: '报告' },
        { id: 'calendar', icon: 'calendar', label: '日历' },
        { id: 'settings', icon: 'settings', label: '设置' }
      ],
      reports: [],
      settings: {
        name: '',
        gender: '',
        contact: '',
        birthDate: '',
        email: ''
      },
      passwordForm: {
        current: '',
        next: ''
      },
      savingSettings: false,
      savingPassword: false,
      loggingOut: false
    }
  },
  computed: {
    isAdmin() {
      return hasRole('admin')
    }
  },
  async mounted() {
    await this.loadDashboard()
  },
  methods: {
    async loadDashboard() {
      this.loading = true
      try {
        const [user, reportResponse] = await Promise.all([
          getCurrentUser(),
          getUserReports()
        ])
        this.userName = user.name
        this.userType = user.role === 'admin' ? '管理员' : user.role === 'consultant' ? '咨询师' : '成长探索者'
        this.settings = {
          name: user.name || '',
          gender: user.gender || '',
          contact: user.phone || '',
          birthDate: user.birth_year && user.birth_month && user.birth_day
            ? `${user.birth_year}-${String(user.birth_month).padStart(2, '0')}-${String(user.birth_day).padStart(2, '0')}`
            : '',
          email: ''
        }
        this.reports = (reportResponse.items || []).map(report => ({
          id: report.id,
          title: report.title,
          date: this.formatDate(report.created_at),
          energyType: report.energy_type || '综合型',
          coreTraits: report.core_traits || '—'
        }))
      } catch (error) {
        this.message = error.response?.data?.detail || '暂时无法打开你的个人空间，请稍后再试'
      } finally {
        this.loading = false
      }
    },
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    },
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    },
    viewReport(reportId) {
      this.$router.push(`/pages/report/detail?id=${reportId}`)
    },
    selectTab(tabId) {
      this.activeTab = tabId
    },
    moveTab(offset) {
      const currentIndex = this.tabs.findIndex(tab => tab.id === this.activeTab)
      const nextIndex = (currentIndex + offset + this.tabs.length) % this.tabs.length
      const nextTab = this.tabs[nextIndex]
      this.activeTab = nextTab.id
      this.$nextTick(() => document.getElementById(`user-tab-${nextTab.id}`)?.focus())
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
    },
    async saveSettings() {
      this.savingSettings = true
      try {
        const payload = {
          name: this.settings.name,
          gender: this.settings.gender || null
        }
        if (this.settings.birthDate) {
          const [year, month, day] = this.settings.birthDate.split('-').map(Number)
          Object.assign(payload, { birth_year: year, birth_month: month, birth_day: day })
        }
        const user = await updateUserProfile(payload)
        this.userName = user.name
        this.message = '设置已保存'
      } catch (error) {
        this.message = error.response?.data?.detail || '设置保存失败'
      } finally {
        this.savingSettings = false
      }
    },
    async savePassword() {
      this.savingPassword = true
      try {
        await changePassword(this.passwordForm.current, this.passwordForm.next)
        this.passwordForm = { current: '', next: '' }
        this.message = '密码已更新，请重新登录其他设备'
      } catch (error) {
        this.message = error.response?.data?.detail || '密码更新失败'
      } finally {
        this.savingPassword = false
      }
    },
    async handleLogout() {
      this.loggingOut = true
      try {
        await logoutUser()
      } catch {
        // 本地会话由 logoutUser 在 finally 中清理，即使服务端请求失败也能退出当前设备。
      } finally {
        await this.$router.replace('/auth/login')
      }
    }
  }
}
</script>

<style scoped>
.dashboard-message {
  margin: 0 0 16px;
  color: var(--muted, #7d6653);
}

.user-center {
  width: 100%;
  background: var(--surface-strong, #fffaf0);
  min-height: 100dvh;
}

/* 用户头部 */
.user-header {
  padding: 100px 20px 40px;
  background: linear-gradient(135deg, rgba(255, 240, 223, .85) 0%, rgba(184, 92, 80, .22) 100%);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.admin-entry-link {
  display: inline-flex;
  min-height: var(--button-height, 46px);
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid rgba(158, 63, 53, .3);
  border-radius: var(--button-radius, 13px);
  padding: 0 16px;
  background: rgba(255, 250, 240, .64);
  color: var(--cinnabar-deep, #9e3f35);
  font-size: 14px;
  font-weight: 800;
  text-decoration: none;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
}

.admin-entry-link:hover {
  border-color: var(--cinnabar-deep, #9e3f35);
  background: rgba(158, 63, 53, .08);
}

.admin-entry-link:active {
  transform: scale(.985);
}

.admin-entry-link:focus-visible {
  outline: 3px solid rgba(181, 87, 76, .3);
  outline-offset: 2px;
}

.admin-entry-link .icon-mark {
  width: 16px;
  height: 16px;
}

.user-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--cinnabar, #b85c50);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 600;
}

.user-details h2 {
  font-size: 28px;
  font-weight: 700;
  color: var(--ink, #2f241b);
  margin-bottom: 8px;
}

.user-type {
  font-size: 16px;
  color: var(--muted, #7d6653);
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
}

/* 内容区 */
.user-content {
  padding: 40px 0 80px;
}

.content-layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 30px;
}

/* 侧边栏 */
.sidebar {
  background: #fff;
  border-radius: 12px;
  padding: 20px 0;
  height: fit-content;
  position: sticky;
  top: 100px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 12px;
  border-top: 0;
  border-right: 0;
  border-bottom: 0;
  background: transparent;
  padding: 15px 25px;
  color: var(--muted, #7d6653);
  cursor: pointer;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease);
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: var(--surface-strong, #fffaf0);
  color: var(--ink, #2f241b);
}

.nav-item.active {
  background: rgba(255, 240, 223, .78);
  color: var(--cinnabar-deep, #9e3f35);
  border-left-color: var(--cinnabar, #b85c50);
  font-weight: 600;
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
}

.nav-label {
  font-size: 15px;
}

/* 主内容 */
.main-content {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  min-height: 500px;
}

.section-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--ink, #2f241b);
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid var(--line, rgba(139, 90, 20, .16));
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 20px;
  color: var(--cinnabar-deep, #9e3f35);
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  color: var(--muted, #7d6653);
  margin-bottom: 25px;
}

.btn-action {
  padding: 12px 32px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: var(--cinnabar, #b85c50);
  border-radius: 50px;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
}

.btn-action:hover {
  background: var(--cinnabar-deep, #9e3f35);
  transform: translateY(-2px);
}

/* 报告列表 */
.reports-list {
  display: grid;
  gap: 20px;
}

.report-card {
  background: var(--surface-strong, #fffaf0);
  border-radius: 12px;
  padding: 25px;
  transition: box-shadow var(--motion-standard, 220ms) var(--ease-out, ease);
}

.report-card:hover {
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.report-header h4 {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink, #2f241b);
}

.report-date {
  font-size: 14px;
  color: var(--muted, #7d6653);
}

.report-preview {
  margin-bottom: 20px;
}

.preview-item {
  font-size: 14px;
  color: var(--muted, #7d6653);
  line-height: 2;
}

.preview-item strong {
  color: var(--ink, #2f241b);
}

.report-actions {
  display: flex;
  gap: 10px;
}

.btn-view,
.btn-download {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease);
}

.btn-view {
  color: #fff;
  background: var(--cinnabar, #b85c50);
}

.btn-view:hover {
  background: var(--cinnabar-deep, #9e3f35);
}

.btn-download {
  color: var(--muted, #7d6653);
  background: #fff;
  border: 2px solid rgba(139, 90, 20, .16);
}

.btn-download:hover {
  border-color: var(--cinnabar, #b85c50);
  color: var(--cinnabar-deep, #9e3f35);
}

/* 决策日历入口 */
.calendar-access-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 22px;
  border: 1px solid rgba(184, 92, 80, 0.18);
  border-radius: 18px;
  background: linear-gradient(135deg, #fffaf0 0%, #fff0df 100%);
  padding: 28px;
}

.calendar-access-mark {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border: 1px solid rgba(139, 90, 20, 0.2);
  border-radius: 50%;
  color: var(--cinnabar-deep);
  font-size: 28px;
  font-weight: 900;
}

.calendar-access-kicker {
  color: var(--gold-deep);
  font-family: "Manrope", "PingFang SC", sans-serif;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

.calendar-access-card h4 {
  margin-top: 7px;
  color: var(--ink);
  font-size: 21px;
}

.calendar-access-card p {
  max-width: 520px;
  margin-top: 8px;
  color: var(--ink-soft);
  line-height: 1.7;
}

/* 设置表单 */
.settings-form {
  max-width: 600px;
}

.password-form {
  max-width: 600px;
  margin-top: 36px;
  border-top: 1px solid rgba(139, 90, 20, .16);
  padding-top: 28px;
}

.password-form h4 {
  margin-bottom: 20px;
  color: var(--ink, #2f241b);
  font-size: 18px;
}

.account-actions {
  display: flex;
  max-width: 600px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 36px;
  border-top: 1px solid rgba(139, 90, 20, .16);
  padding-top: 28px;
}

.account-actions h4 {
  color: var(--ink, #2f241b);
  font-size: 18px;
}

.account-actions p {
  margin-top: 6px;
  color: var(--muted, #7d6653);
  font-size: 13px;
}

.btn-logout {
  display: inline-flex;
  min-height: var(--button-height, 46px);
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid rgba(158, 63, 53, .35);
  border-radius: var(--button-radius, 13px);
  padding: 0 18px;
  background: transparent;
  color: var(--cinnabar-deep, #9e3f35);
  font-family: var(--font-ui, sans-serif);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease);
}

.btn-logout:hover {
  border-color: var(--cinnabar-deep, #9e3f35);
  background: rgba(158, 63, 53, .08);
}

.btn-logout:focus-visible {
  outline: 3px solid rgba(181, 87, 76, .3);
  outline-offset: 2px;
}

.btn-logout:disabled {
  cursor: wait;
  opacity: .62;
}

.btn-logout .icon-mark {
  width: 16px;
  height: 16px;
}

.form-group {
  margin-bottom: 25px;
}

.choice-fieldset {
  min-width: 0;
  border: 0;
  padding: 0;
}

.choice-fieldset > legend {
  display: block;
  width: 100%;
  margin-bottom: 10px;
  color: var(--ink, #2f241b);
  font-size: 15px;
  font-weight: 600;
}

.form-group label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink, #2f241b);
  margin-bottom: 10px;
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group input[type="tel"],
.form-group input[type="date"],
.form-group input[type="password"] {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid rgba(139, 90, 20, .16);
  border-radius: 8px;
  font-size: 15px;
  transition: border-color var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease), background var(--motion-standard, 220ms) var(--ease-out, ease);
}

.form-group input:focus {
  border-color: var(--cinnabar, #b85c50);
  outline: none;
}

.radio-group {
  display: flex;
  gap: 20px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 0;
  cursor: pointer;
  font-weight: 400;
}

.radio-label input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.choice-fieldset .radio-label {
  display: flex;
  margin-bottom: 0;
}

.btn-save {
  padding: 14px 40px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: var(--cinnabar, #b85c50);
  border-radius: 50px;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
  margin-top: 10px;
}

.btn-save:hover {
  background: var(--cinnabar-deep, #9e3f35);
  transform: translateY(-2px);
}

/* 页脚 */
.footer {
  background: var(--ink, #2f241b);
  padding: 40px 0;
  text-align: center;
  color: rgba(255, 250, 240, .76);
}

/* 响应式 */
@media (max-width: 768px) {
  .nav-container {
    padding: 15px 20px;
  }

  .nav-menu {
    gap: 15px;
  }

  .nav-link {
    font-size: 14px;
  }

  .user-header {
    padding: 54px 20px 30px;
  }

  .user-header-inner {
    align-items: stretch;
    flex-direction: column;
    gap: 14px;
  }

  .user-avatar {
    width: 60px;
    height: 60px;
    font-size: 24px;
  }

  .admin-entry-link {
    width: 100%;
    justify-content: space-between;
  }

  .user-details h2 {
    font-size: 22px;
  }

  .content-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
  }

  .nav-item {
    flex-direction: column;
    gap: 5px;
    padding: 12px 20px;
    border-left: none;
    border-bottom: 3px solid transparent;
    white-space: nowrap;
  }

  .nav-item.active {
    border-left: none;
    border-bottom-color: var(--cinnabar, #b85c50);
  }

  .main-content {
    padding: 25px 20px;
  }

  .user-content {
    padding: 28px 0 calc(60px + var(--safe-bottom, 0px));
  }

  .report-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .report-actions {
    flex-direction: column;
  }

  .report-actions button,
  .btn-save {
    width: 100%;
  }

  .form-group input[type="text"],
  .form-group input[type="email"],
  .form-group input[type="tel"],
  .form-group input[type="date"],
  .form-group input[type="password"] {
    font-size: 16px;
  }

  .account-actions {
    align-items: stretch;
    flex-direction: column;
    gap: 14px;
  }

  .btn-logout {
    width: 100%;
  }

  .calendar-access-card {
    grid-template-columns: auto 1fr;
  }

  .calendar-access-card .btn-action {
    grid-column: 1 / -1;
    width: 100%;
  }

}

@media (max-width: 420px) {
  .user-info {
    gap: 13px;
  }

  .main-content {
    padding: 22px 15px;
  }

  .report-header {
    align-items: flex-start;
  }

  .report-header h4 {
    max-width: 100%;
    overflow-wrap: anywhere;
  }

  .report-card {
    padding: 19px 16px;
  }

  .calendar-access-card {
    grid-template-columns: 1fr;
    padding: 21px 18px;
  }

  .calendar-access-mark {
    width: 52px;
    height: 52px;
    font-size: 23px;
  }
}

/* 与主站纸张视觉统一，减少旧版后台面板的生硬白底。 */
.user-center {
  background: transparent;
}

.user-header {
  position: relative;
  overflow: hidden;
  padding: 62px 0 38px;
  background:
    linear-gradient(105deg, rgba(255, 250, 240, 0.82), rgba(255, 239, 222, 0.72)),
    radial-gradient(circle at 86% 24%, rgba(111, 159, 147, 0.18), transparent 28%),
    var(--paper-deep, #ead9bf);
}

.user-header::after {
  content: "辰鉴";
  position: absolute;
  right: 7%;
  bottom: -40px;
  color: rgba(184, 92, 80, 0.08);
  font-family: var(--font-display, serif);
  font-size: 150px;
  font-weight: 900;
  line-height: 1;
  pointer-events: none;
}

.user-info,
.user-header .container {
  position: relative;
  z-index: 1;
}

.user-info {
  gap: 16px;
}

.user-avatar {
  width: 66px;
  height: 66px;
  border: 1px solid rgba(184, 92, 80, 0.28);
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
  box-shadow: 0 12px 22px -15px rgba(158, 63, 53, 0.86);
  font-family: var(--font-display, serif);
}

.user-details h2 {
  font-family: var(--font-display, serif);
  letter-spacing: 0.02em;
}

.user-content {
  padding: 46px 0 78px;
}

.content-layout {
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 20px;
}

.sidebar,
.main-content {
  border: 1px solid rgba(139, 90, 20, 0.13);
  box-shadow: var(--shadow-card, 0 16px 48px -34px rgba(84, 48, 25, 0.48));
}

.sidebar {
  padding: 8px 0;
  background: rgba(255, 252, 245, 0.72);
}

.nav-item {
  min-height: 48px;
  padding: 12px 18px;
  border-left-width: 2px;
}

.main-content {
  background: rgba(255, 252, 245, 0.78);
  min-width: 0;
}

.content-section,
.report-card,
.calendar-access-card,
.settings-form,
.password-form {
  min-width: 0;
}

.section-title {
  font-family: var(--font-display, serif);
  letter-spacing: 0.02em;
}

.report-card {
  border: 1px solid rgba(139, 90, 20, 0.1);
  background: rgba(248, 241, 230, 0.56);
}

.calendar-access-card {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.btn-action,
.btn-save,
.btn-view,
.btn-download {
  min-height: 44px;
}

@media (max-width: 768px) {
  .user-header::after {
    right: 2%;
    bottom: -18px;
    font-size: 86px;
  }

  .content-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }

  .sidebar {
    overflow: hidden;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .sidebar-nav::-webkit-scrollbar {
    display: none;
  }

  .nav-item {
    width: auto;
    min-width: 92px;
    min-height: 48px;
    flex: 0 0 auto;
    justify-content: center;
    gap: 6px;
    border-left: 0;
    border-bottom: 2px solid transparent;
    padding: 8px 10px;
  }

  .nav-icon {
    width: 18px;
    height: 18px;
  }

  .nav-label {
    font-size: 13px;
  }

  .nav-item.active {
    border-left: 0;
    border-bottom-color: var(--cinnabar, #b85c50);
  }

  .main-content {
    min-height: 0;
    padding: 20px 14px;
  }

  .section-title {
    margin-bottom: 18px;
    font-size: clamp(23px, 6.5vw, 28px);
  }

  .empty-state {
    padding: 48px 14px;
  }

  .empty-icon {
    width: 40px;
    height: 40px;
    margin-bottom: 14px;
  }

  .empty-state p {
    margin-bottom: 18px;
  }

  .reports-list {
    gap: 14px;
  }

  .report-card {
    padding: 18px 16px;
  }

  .report-header {
    gap: 6px;
    margin-bottom: 14px;
  }

  .report-header h4 {
    font-size: 16px;
  }

  .report-date {
    font-size: 12px;
  }

  .report-preview {
    margin-bottom: 14px;
  }

  .preview-item {
    font-size: 13px;
    line-height: 1.75;
  }

  .calendar-access-card {
    gap: 14px;
    padding: 18px;
  }

  .calendar-access-mark {
    width: 52px;
    height: 52px;
    font-size: 22px;
  }

  .calendar-access-card h4 {
    font-size: 18px;
  }

  .calendar-access-card p {
    font-size: 14px;
    line-height: 1.7;
  }

  .form-group {
    margin-bottom: 18px;
  }

  .form-group label {
    margin-bottom: 7px;
    font-size: 14px;
  }

  .form-group input[type="text"],
  .form-group input[type="email"],
  .form-group input[type="tel"],
  .form-group input[type="date"],
  .form-group input[type="password"] {
    min-height: 48px;
    padding: 11px 13px;
  }

  .btn-action,
  .btn-save,
  .btn-view {
    min-height: 48px;
  }

  .report-actions .btn-view {
    width: 100%;
  }
}

@media (max-width: 420px) {
  .user-header {
    padding: 36px 0 22px;
  }

  .user-avatar {
    width: 54px;
    height: 54px;
    font-size: 24px;
  }

  .user-details h2 {
    font-size: 20px;
  }

  .content-layout {
    gap: 12px;
  }

  .main-content {
    padding: 18px 13px;
  }

  .nav-item {
    min-width: 86px;
    padding-right: 8px;
    padding-left: 8px;
  }

  .calendar-access-card {
    padding: 16px;
  }
}

/* 最终移动端紧凑版：保留触控尺寸，减少视觉体积与空白。 */
@media (max-width: 768px) {
  .user-header {
    padding: 34px 0 20px;
  }

  .user-header::after {
    right: 2%;
    bottom: -14px;
    font-size: 72px;
  }

  .user-avatar {
    width: 56px;
    height: 56px;
    font-size: 25px;
  }

  .user-details h2 {
    font-size: 21px;
  }

  .user-type {
    font-size: 14px;
  }

  .user-content {
    padding: 20px 0 calc(28px + var(--safe-bottom, 0px));
  }

  .content-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }

  .sidebar,
  .main-content {
    border-radius: 14px;
  }

  .sidebar-nav {
    gap: 0;
  }

  .nav-item {
    min-width: 82px;
    min-height: 44px;
    gap: 4px;
    padding: 7px 8px;
  }

  .nav-icon {
    width: 17px;
    height: 17px;
  }

  .nav-label {
    font-size: 12px;
  }

  .main-content {
    padding: 16px 12px;
  }

  .section-title {
    margin-bottom: 16px;
    font-size: 22px;
  }

  .empty-state {
    padding: 36px 12px;
  }

  .empty-icon {
    width: 36px;
    height: 36px;
    margin-bottom: 10px;
  }

  .empty-state p {
    margin-bottom: 16px;
    font-size: 14px;
  }

  .reports-list {
    gap: 12px;
  }

  .report-card {
    padding: 16px 14px;
    border-radius: 14px;
  }

  .report-header {
    margin-bottom: 10px;
  }

  .report-header h4 {
    font-size: 15px;
  }

  .report-date {
    font-size: 11px;
  }

  .report-preview {
    margin-bottom: 12px;
  }

  .preview-item {
    font-size: 13px;
    line-height: 1.65;
  }

  .calendar-access-card {
    gap: 12px;
    padding: 15px;
    border-radius: 14px;
  }

  .calendar-access-mark {
    width: 48px;
    height: 48px;
    font-size: 20px;
  }

  .calendar-access-card h4 {
    font-size: 17px;
  }

  .calendar-access-card p {
    font-size: 15px;
    line-height: 1.6;
  }

  .btn-action,
  .btn-save,
  .btn-view {
    display: inline-flex;
    min-height: 46px;
    align-items: center;
    justify-content: center;
    padding-right: 16px;
    padding-left: 16px;
    font-size: 14px;
  }

  .form-group {
    margin-bottom: 16px;
  }

  .form-group label {
    margin-bottom: 6px;
    font-size: 14px;
  }

  .form-group input[type="text"],
  .form-group input[type="email"],
  .form-group input[type="date"],
  .form-group input[type="password"] {
    min-height: 46px;
    padding: 10px 12px;
  }
}

@media (max-width: 420px) {
  .user-header {
    padding: 30px 0 18px;
  }

  .user-header::after {
    font-size: 60px;
  }

  .user-avatar {
    width: 52px;
    height: 52px;
    font-size: 23px;
  }

  .user-details h2 {
    font-size: 20px;
  }

  .main-content {
    padding: 14px 11px;
  }

  .nav-item {
    min-width: 78px;
    padding-right: 6px;
    padding-left: 6px;
  }
}

/* 按钮专项：个人中心的主操作统一为卡片内 CTA，表单按钮移动端全宽。 */
.btn-action,
.btn-save,
.btn-view {
  display: inline-flex;
  min-height: var(--button-height, 46px);
  align-items: center;
  justify-content: center;
  border: 1px solid var(--cinnabar-deep, #9e3f35);
  border-radius: var(--button-radius, 13px);
  padding: 0 16px;
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
  color: #fffaf0;
  font-family: var(--font-ui, sans-serif);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
}

.btn-action:hover,
.btn-save:hover,
.btn-view:hover {
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), #8f352f);
  box-shadow: 0 10px 22px -16px rgba(158, 63, 53, 0.86);
  transform: none;
}

.btn-action:active,
.btn-save:active,
.btn-view:active {
  transform: scale(0.985);
}

.report-actions {
  align-items: stretch;
  gap: var(--button-gap, 8px);
}

.calendar-access-card .btn-action {
  min-width: 160px;
}

@media (max-width: 768px) {
  .btn-action,
  .btn-save,
  .btn-view {
    min-height: 46px;
  }

  .empty-state .btn-action,
  .report-actions .btn-view,
  .calendar-access-card .btn-action,
  .settings-form .btn-save,
  .password-form .btn-save {
    width: 100%;
  }

  .calendar-access-card .btn-action {
    min-width: 0;
  }
}
</style>
