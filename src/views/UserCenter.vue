<template>
  <div class="user-center">
    <BrandNav />

    <BrandPageHeader eyebrow="YOUR PERSONAL SPACE" title="我的个人空间" description="你的档案、报告与行动记录，都在这里。每一次回看，都可以成为下一步的起点。" seal="行路">
      <div class="user-info">
        <div class="user-avatar">{{ userName.charAt(0) }}</div>
        <div class="user-details">
          <strong class="user-name">{{ userName }}</strong>
          <p class="user-type">{{ userType }}</p>
        </div>
      </div>
      <template v-if="isAdmin" #actions>
        <router-link to="/admin" class="admin-entry-link">
          <span>进入管理中心</span>
          <IconMark name="arrow" />
        </router-link>
      </template>
    </BrandPageHeader>

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

<script src="../features/user-center/page.js"></script>

<style scoped src="../features/user-center/styles/shell.css"></style>
<style scoped src="../features/user-center/styles/shell-responsive.css"></style>
<style scoped src="../features/user-center/styles/shared.css"></style>
