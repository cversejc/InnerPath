<template>
  <div class="user-center">
    <BrandNav />

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

    <section class="user-content">
      <div class="container">
        <p v-if="loading" class="dashboard-message" role="status" aria-live="polite">正在打开你的个人空间…</p>
        <p v-if="message" class="dashboard-message" role="status" aria-live="polite">{{ message }}</p>
        <ProfileGrowthCard
          v-if="!loading"
          class="user-growth-card"
          :profile="settings"
          :completion="profileCompletion"
          :last-confirmed-at="profileLastConfirmedAt"
          @edit="openProfileSettings"
        />

        <div class="content-layout">
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

          <main class="main-content">
            <ReportsPanel
              v-if="activeTab === 'reports'"
              :reports="reports"
              @request-report="goToAssessment"
              @view-report="viewReport"
            />
            <DecisionCalendarPanel v-else-if="activeTab === 'calendar'" @open-calendar="goToCalendar" />
            <RequestsPanel v-else-if="activeTab === 'requests'" :requests="requests" />
            <AccountSettingsPanel
              v-else-if="activeTab === 'settings'"
              v-model:settings="settings"
              v-model:optional-profile-expanded="optionalProfileExpanded"
              v-model:password-form="passwordForm"
              :settings-errors="settingsErrors"
              :settings-error="settingsError"
              :saving-settings="savingSettings"
              :saving-password="savingPassword"
              :logging-out="loggingOut"
              @save-settings="saveSettings"
              @save-password="savePassword"
              @logout="handleLogout"
            />
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
import { getMyServiceRequests } from '../features/service-requests/api'
import {
  buildProfilePayload,
  createEmptyProfile,
  mapUserToProfile,
  validateProfile
} from '../features/user-center/profile'
import { formatUserCenterDate } from '../features/user-center/presentation'
import AccountSettingsPanel from '../features/user-center/components/AccountSettingsPanel.vue'
import DecisionCalendarPanel from '../features/user-center/components/DecisionCalendarPanel.vue'
import ReportsPanel from '../features/user-center/components/ReportsPanel.vue'
import RequestsPanel from '../features/user-center/components/RequestsPanel.vue'
import { hasRole, logout as logoutUser, setAuthenticatedUser } from '../stores/auth'
import ProfileGrowthCard from '../components/ProfileGrowthCard.vue'

export default {
  name: 'UserCenter',
  components: {
    AccountSettingsPanel,
    DecisionCalendarPanel,
    ProfileGrowthCard,
    ReportsPanel,
    RequestsPanel
  },
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
        { id: 'requests', icon: 'document', label: '我的申请' },
        { id: 'settings', icon: 'settings', label: '设置' }
      ],
      reports: [],
      requests: [],
      settings: createEmptyProfile(),
      profileCompletion: 0,
      profileLastConfirmedAt: null,
      optionalProfileExpanded: false,
      settingsErrors: {},
      settingsError: '',
      passwordForm: { current: '', next: '' },
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
    if (['reports', 'calendar', 'settings'].includes(this.$route.query.tab)) this.activeTab = this.$route.query.tab
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
        let requestResponse = { items: [] }
        try {
          requestResponse = await getMyServiceRequests()
        } catch (error) {
          // 申请分区不能阻断历史报告和账户设置的打开。
          this.message = this.message || '申请记录暂时无法同步，请稍后重试'
        }
        this.userName = user.name
        this.userType = user.role === 'admin' ? '管理员' : user.role === 'consultant' ? '咨询师' : '成长探索者'
        this.settings = mapUserToProfile(user)
        this.profileCompletion = Number(user.profile_completion || 0)
        this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
        this.optionalProfileExpanded = this.profileCompletion < 100
        this.reports = (reportResponse.items || []).map(report => ({
          id: report.id,
          title: report.title,
          date: formatUserCenterDate(report.created_at),
          energyType: report.energy_type || '综合型',
          coreTraits: report.core_traits || '—'
        }))
        this.requests = requestResponse.items || []
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
    openProfileSettings() {
      this.activeTab = 'settings'
      this.optionalProfileExpanded = true
      this.$nextTick(() => document.getElementById('user-profile-name')?.focus())
    },
    moveTab(offset) {
      const currentIndex = this.tabs.findIndex(tab => tab.id === this.activeTab)
      const nextIndex = (currentIndex + offset + this.tabs.length) % this.tabs.length
      const nextTab = this.tabs[nextIndex]
      this.activeTab = nextTab.id
      this.$nextTick(() => document.getElementById(`user-tab-${nextTab.id}`)?.focus())
    },
    async saveSettings() {
      this.settingsError = ''
      this.settingsErrors = validateProfile(this.settings)
      if (Object.keys(this.settingsErrors).length) {
        this.settingsError = '请先检查档案中的必填项。'
        return
      }
      this.savingSettings = true
      try {
        const user = await updateUserProfile(buildProfilePayload(this.settings))
        setAuthenticatedUser(user)
        this.userName = user.name
        this.profileCompletion = Number(user.profile_completion || 0)
        this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
        this.settingsError = ''
        this.message = `个人档案已保存（版本 v${user.profile_version || 1}）`
      } catch (error) {
        this.settingsError = error.response?.data?.detail || '设置保存失败'
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

<style scoped src="../features/user-center/styles/shell.css"></style>
<style scoped src="../features/user-center/styles/shell-responsive.css"></style>
<style scoped src="../features/user-center/styles/shared.css"></style>
