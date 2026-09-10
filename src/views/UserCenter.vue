<template>
  <div class="user-center">
    <BrandNav />

    <!-- 用户信息头部 -->
    <section class="user-header">
      <div class="container">
        <div class="user-info">
          <div class="user-avatar">{{ userName.charAt(0) }}</div>
          <div class="user-details">
            <h2>{{ userName }}</h2>
            <p class="user-type">{{ userType }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 主内容区 -->
    <section class="user-content">
      <div class="container">
        <p v-if="loading" class="dashboard-message">正在打开你的个人空间…</p>
        <p v-if="message" class="dashboard-message">{{ message }}</p>
        <div class="content-layout">
          <!-- 侧边栏 -->
          <aside class="sidebar">
            <nav class="sidebar-nav">
              <a
                v-for="tab in tabs"
                :key="tab.id"
                class="nav-item"
                :class="{ active: activeTab === tab.id }"
                @click="activeTab = tab.id"
              >
                <span class="nav-icon">{{ tab.icon }}</span>
                <span class="nav-label">{{ tab.label }}</span>
              </a>
            </nav>
          </aside>

          <!-- 内容区 -->
          <main class="main-content">
            <!-- 我的报告 -->
            <div v-if="activeTab === 'reports'" class="content-section">
              <h3 class="section-title">我的报告</h3>
              <div v-if="reports.length === 0" class="empty-state">
                <div class="empty-icon">📄</div>
                <p>暂无报告</p>
                <button class="btn-action" @click="goToAssessment">生成说明书</button>
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
                    <button class="btn-view" @click="viewReport(report.id)">查看完整报告</button>
                    <button class="btn-download">下载PDF</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 我的决策日历 -->
            <div v-if="activeTab === 'calendar'" class="content-section">
              <h3 class="section-title">我的决策日历</h3>
              <div class="calendar-access-card">
                <div class="calendar-access-mark" aria-hidden="true">辰</div>
                <div>
                  <span class="calendar-access-kicker">PERSONAL TIMEZONE</span>
                  <h4>把报告里的洞察带回每天</h4>
                  <p>查看当前阶段的行动节奏，记录真实发生过的事，让选择逐渐有迹可循。</p>
                </div>
                <button class="btn-action" @click="goToCalendar">打开决策日历</button>
              </div>
            </div>

            <!-- 账户设置 -->
            <div v-if="activeTab === 'settings'" class="content-section">
              <h3 class="section-title">账户设置</h3>
              <form class="settings-form">
                <div class="form-group">
                  <label>姓名</label>
                  <input v-model="settings.name" type="text">
                </div>
                <div class="form-group">
                  <label>性别</label>
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
                </div>
                <div class="form-group">
                  <label>联系方式</label>
                  <input v-model="settings.contact" type="text" readonly>
                </div>
                <div class="form-group">
                  <label>出生日期</label>
                  <input v-model="settings.birthDate" type="date">
                </div>
                <button type="button" class="btn-save" @click="saveSettings">保存设置</button>
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
                <button type="submit" class="btn-save">更新密码</button>
              </form>
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
        { id: 'reports', icon: '📊', label: '我的报告' },
        { id: 'calendar', icon: '🗓️', label: '决策日历' },
        { id: 'settings', icon: '⚙️', label: '账户设置' }
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
      }
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
    formatDate(value) {
      return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
    },
    async saveSettings() {
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
      }
    },
    async savePassword() {
      try {
        await changePassword(this.passwordForm.current, this.passwordForm.next)
        this.passwordForm = { current: '', next: '' }
        this.message = '密码已更新，请重新登录其他设备'
      } catch (error) {
        this.message = error.response?.data?.detail || '密码更新失败'
      }
    }
  }
}
</script>

<style scoped>
.dashboard-message {
  margin: 0 0 16px;
  color: var(--muted, #756a60);
}

.user-center {
  width: 100%;
  background: #f8f9fa;
  min-height: 100vh;
}

/* 导航栏 */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 1000;
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 24px;
  font-weight: 600;
  color: #d4524f;
}

.nav-menu {
  display: flex;
  gap: 30px;
}

.nav-link {
  font-size: 16px;
  color: #666;
  transition: color 0.3s;
}

.nav-link:hover,
.nav-link.active {
  color: #d4524f;
}

/* 用户头部 */
.user-header {
  padding: 100px 20px 40px;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #d4524f;
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
  color: #2d3436;
  margin-bottom: 8px;
}

.user-type {
  font-size: 16px;
  color: #636e72;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
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
  align-items: center;
  gap: 12px;
  padding: 15px 25px;
  color: #666;
  cursor: pointer;
  transition: all 0.3s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #f8f9fa;
  color: #2d3436;
}

.nav-item.active {
  background: #fff5f5;
  color: #d4524f;
  border-left-color: #d4524f;
  font-weight: 600;
}

.nav-icon {
  font-size: 20px;
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
  color: #2d3436;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  color: #999;
  margin-bottom: 25px;
}

.btn-action {
  padding: 12px 32px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-action:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

/* 报告列表 */
.reports-list {
  display: grid;
  gap: 20px;
}

.report-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 25px;
  transition: all 0.3s;
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
  color: #2d3436;
}

.report-date {
  font-size: 14px;
  color: #999;
}

.report-preview {
  margin-bottom: 20px;
}

.preview-item {
  font-size: 14px;
  color: #666;
  line-height: 2;
}

.preview-item strong {
  color: #2d3436;
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
  transition: all 0.3s;
}

.btn-view {
  color: #fff;
  background: #d4524f;
}

.btn-view:hover {
  background: #c0392b;
}

.btn-download {
  color: #666;
  background: #fff;
  border: 2px solid #e0e0e0;
}

.btn-download:hover {
  border-color: #d4524f;
  color: #d4524f;
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
  border-top: 1px solid #e8e8e8;
  padding-top: 28px;
}

.password-form h4 {
  margin-bottom: 20px;
  color: #2d3436;
  font-size: 18px;
}

.form-group {
  margin-bottom: 25px;
}

.form-group label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 10px;
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group input[type="date"],
.form-group input[type="password"] {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.3s;
}

.form-group input:focus {
  border-color: #d4524f;
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
  cursor: pointer;
  font-weight: 400;
}

.radio-label input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.btn-save {
  padding: 14px 40px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
  margin-top: 10px;
}

.btn-save:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

/* 页脚 */
.footer {
  background: #2d3436;
  padding: 40px 0;
  text-align: center;
  color: #b2bec3;
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
    padding: 80px 20px 30px;
  }

  .user-avatar {
    width: 60px;
    height: 60px;
    font-size: 24px;
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
    border-bottom-color: #d4524f;
  }

  .main-content {
    padding: 25px 20px;
  }

  .calendar-access-card {
    grid-template-columns: auto 1fr;
  }

  .calendar-access-card .btn-action {
    grid-column: 1 / -1;
    width: 100%;
  }

}
</style>
