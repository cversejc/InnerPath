<template>
  <div class="admin-shell">
    <BrandNav />
    <main class="admin-main">
      <header class="admin-hero">
        <div>
          <p class="section-kicker">CHENJIAN / OPERATIONS ROOM</p>
          <h1>辰鉴运营中枢</h1>
          <p class="hero-caption">把每一个用户、时机与行动，整理成可以被照看的全局。</p>
        </div>
        <div class="hero-actions">
          <span class="sync-state"><i :class="{ live: dashboardLoading }"></i>{{ dashboardLoading ? '正在同步' : lastUpdated ? `更新于 ${lastUpdated}` : '等待同步' }}</span>
          <router-link class="secondary-button compact-button" to="/staff">申请工作台</router-link>
          <button class="secondary-button compact-button" type="button" :disabled="activeLoading" @click="refreshActive"><IconMark name="refresh" /> <span>刷新</span></button>
          <button class="admin-account-button" type="button" :disabled="loggingOut" :aria-busy="loggingOut" @click="handleLogout">
            <IconMark name="logout" />
            <span>{{ loggingOut ? '退出中…' : '退出登录' }}</span>
          </button>
        </div>
      </header>

      <nav class="admin-tabs" aria-label="管理后台导航">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          :class="['admin-tab', { active: activeTab === tab.id }]"
          :aria-pressed="activeTab === tab.id"
          @click="switchTab(tab.id)">
          <span class="tab-index">{{ tab.index }}</span>
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <div v-if="message" class="console-message" role="status" aria-live="polite">
        <span>{{ message }}</span>
        <button type="button" aria-label="关闭提示" @click="message = ''">×</button>
      </div>

      <AdminDashboardSection
        v-if="activeTab === 'overview'"
        :auto-refresh="autoRefresh"
        :chart-grid-lines="chartGridLines"
        :dashboard="dashboard"
        :dashboard-loading="dashboardLoading"
        :dashboard-range="dashboardRange"
        :dashboard-ranges="dashboardRanges"
        :distribution-groups="distributionGroups"
        :metric-cards="metricCards"
        :trend-series="trendSeries"
        :trend-ticks="trendTicks"
        @auto-refresh-change="setAutoRefresh"
        @change-range="changeDashboardRange"
        @go-from-alert="goFromAlert"
        @switch-tab="switchTab"
      />

      <AdminUsersSection
        v-else-if="activeTab === 'users'"
        :filters="userFilters"
        :loading="usersLoading"
        :page="userPage"
        :page-size="userPageSize"
        :users="users"
        @change-page="changeUserPage"
        @change-role="changeRole"
        @export="exportResource"
        @open-calendar="openCalendarForUser"
        @open-user="openUserDetail"
        @reset-filters="resetUserFilters"
        @reset-password="resetUserPassword"
        @search="searchUsers"
        @toggle-user="toggleUser"
      />

      <AdminCalendarRequestsSection
        v-else-if="activeTab === 'calendar-requests'"
        :calendar-requests="calendarRequests"
        :loading="calendarRequestsLoading"
        :status-filter="calendarRequestStatusFilter"
        @refresh="loadCalendarRequests"
        @review="reviewCalendarRequest"
        @update-status-filter="setCalendarRequestStatusFilter"
      />

      <AdminCalendarSection
        v-else-if="activeTab === 'calendar'"
        :calendar-form="calendarForm"
        :calendar-import-json="calendarImportJson"
        :calendar-loading="calendarLoading"
        :calendar-saving="calendarSaving"
        :calendar-user-search="calendarUserSearch"
        :calendar-users="calendarUsers"
        :calendars="calendars"
        :selected-calendar-user="selectedCalendarUser"
        :show-calendar-import="showCalendarImport"
        @add-entry="addCalendarEntry"
        @archive-calendar="archiveCalendar"
        @cancel-edit="cancelCalendarEdit"
        @export-calendar="exportCalendarJson"
        @import-json="importCalendarJson"
        @load-users="loadCalendarUsers"
        @new-calendar="startNewCalendar"
        @prepare-edit="prepareCalendarEdit"
        @publish-calendar="publishCalendar"
        @remove-entry="removeCalendarEntry"
        @save-calendar="saveCalendar"
        @select-user="selectCalendarUser"
        @toggle-import="toggleImportPanel"
        @update:calendar-import-json="updateCalendarImportJson"
        @update:calendar-user-search="updateCalendarUserSearch"
      />

      <AdminStaffSection
        v-else-if="activeTab === 'staff'"
        :invite-form="inviteForm"
        :invite-saving="inviteSaving"
        :invite-token="inviteToken"
        :staff-loading="staffLoading"
        :staff-users="staffUsers"
        @invite="inviteStaff"
      />

      <AdminReportsSection
        v-else-if="activeTab === 'reports'"
        :page-size="reportPageSize"
        :report-filters="reportFilters"
        :report-page="reportPage"
        :report-retry-limit="reportRetryLimit"
        :report-section="reportSection"
        :reports="reports"
        :reports-loading="reportsLoading"
        :report-tasks="reportTasks"
        :task-filters="taskFilters"
        :task-page="taskPage"
        :task-page-size="taskPageSize"
        :tasks-loading="tasksLoading"
        @change-report-page="changeReportPage"
        @change-task-page="changeTaskPage"
        @export="exportResource"
        @open-report="openReport"
        @retry-task="retryTask"
        @search-reports="searchReports"
        @search-tasks="searchReportTasks"
        @select-section="setReportSection"
      />

      <AdminActivitySection
        v-else-if="activeTab === 'logs'"
        :audit-loading="auditLoading"
        :audit-logs="auditLogs"
        :behavior-filters="behaviorFilters"
        :decision-loading="decisionLoading"
        :decision-logs="decisionLogs"
        :decision-page="decisionPage"
        :decision-page-size="decisionPageSize"
        :log-filters="logFilters"
        :log-page="logPage"
        :log-page-size="logPageSize"
        :log-section="logSection"
        :report-tasks="reportTasks"
        :staff-users="staffUsers"
        :task-filters="taskFilters"
        :task-page="taskPage"
        :task-page-size="taskPageSize"
        :tasks-loading="tasksLoading"
        @change-decision-page="changeDecisionPage"
        @change-log-page="changeLogPage"
        @change-task-page="changeTaskPage"
        @export="exportResource"
        @load-audit-logs="loadAuditLogs"
        @open-log="openLogDetail"
        @reset-log-filters="resetLogFilters"
        @search-decision-logs="searchDecisionLogs"
        @search-tasks="searchReportTasks"
        @select-section="setLogSection"
      />

      <AdminDetailDrawers
        ref="adminDetailDrawers"
        :detail-user="detailUser"
        :log-detail="logDetail"
        :profile-saving="profileSaving"
        :report-detail="reportDetail"
        :user-edit="userEdit"
        :user-panel-data="userPanelData"
        :user-panel-loading="userPanelLoading"
        :user-panel-tab="userPanelTab"
        :user-panel-tabs="userPanelTabs"
        :user-summary="userSummary"
        @close-active="closeActiveDrawer"
        @close-log="closeLogDetail"
        @close-report="closeReportDetail"
        @close-user="closeUserDetail"
        @open-calendar-for-user="openCalendarForUser"
        @open-report="openReport"
        @save-user-profile="saveUserProfile"
        @set-user-panel-tab="setUserPanelTab"
      />
    </main>
  </div>
</template>

<script src="./AdminConsole.js"></script>

<style src="./AdminConsole.css"></style>
