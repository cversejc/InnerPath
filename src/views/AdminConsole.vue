<template>
  <div class="admin-shell">
    <BrandNav />
    <main class="admin-main">
      <BrandPageHeader contained compact eyebrow="OPERATIONS ROOM" title="辰鉴运营中枢" description="把每一个用户、申请与交付，整理成可以被照看的全局。" seal="有序">
        <template #actions>
          <span class="sync-state"><i :class="{ live: dashboardLoading }"></i>{{ dashboardLoading ? '正在同步' : lastUpdated ? `更新于 ${lastUpdated}` : '等待同步' }}</span>
          <router-link class="secondary-button compact-button" to="/staff">申请工作台</router-link>
          <router-link class="secondary-button compact-button" to="/skills">技能与示例工作台</router-link>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="activeLoading" :loading="activeLoading" loading-text="刷新中…" :aria-busy="activeLoading" @click="refreshActive">
            <template #icon><IconMark name="refresh" /></template>
            刷新
          </VanButton>
          <VanButton class="admin-account-button" type="default" plain native-type="button" :disabled="loggingOut" :loading="loggingOut" loading-text="退出中…" :aria-busy="loggingOut" @click="handleLogout">
            <template #icon><IconMark name="logout" /></template>
            退出登录
          </VanButton>
        </template>
      </BrandPageHeader>

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
        <AdminIconButton icon="close" label="关闭提示" @click="message = ''" />
      </div>

      <AdminDashboardSection
        v-if="activeTab === 'overview'"
        :auto-refresh="autoRefresh"
        :chart-grid-lines="dashboardViewModel.chartGridLines"
        :dashboard="dashboard"
        :dashboard-loading="dashboardLoading"
        :dashboard-range="dashboardRange"
        :dashboard-ranges="dashboardRanges"
        :distribution-groups="dashboardViewModel.distributionGroups"
        :metric-cards="dashboardViewModel.metricCards"
        :trend-series="dashboardViewModel.trendSeries"
        :trend-ticks="dashboardViewModel.trendTicks"
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

      <AdminRequestsSection
        v-else-if="activeTab === 'requests'"
        :calendar-filters="calendarRequestFilters"
        :calendar-requests="adminCalendarRequests"
        :consultants="staffUsers.filter(member => member.role === 'consultant' && member.is_active)"
        :filters="requestFilters"
        :loading="requestsLoading"
        :page="requestPage"
        :page-size="requestPageSize"
        :request-kind="requestKind"
        :service-requests="adminServiceRequests"
        @change-kind="setRequestKind"
        @change-page="changeRequestPage"
        @open-report="openReport"
        @open-user="openUserDetail"
        @reset-filters="resetAdminRequestFilters"
        @search="searchAdminRequests"
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
        :specialty-saving-id="consultantSpecialtySavingId"
        :staff-loading="staffLoading"
        :staff-users="staffUsers"
        @invite="inviteStaff"
        @update-specialties="updateConsultantSpecialties"
      />

      <AdminReportsSection
        v-else-if="activeTab === 'reports'"
        :page-size="reportPageSize"
        :report-filters="reportFilters"
        :report-page="reportPage"
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
        @open-log="openLogDetail"
        @open-report="openReport"
        @save-user-profile="saveUserProfile"
        @set-user-panel-tab="setUserPanelTab"
      />
    </main>

    <VanDialog
      v-model:show="passwordDialog.visible"
      class="mobile-form-dialog"
      title="重置用户密码"
      :close-on-click-overlay="false"
      :keyboard-enabled="!passwordDialog.submitting"
      :show-confirm-button="false"
    >
      <p class="mobile-form-dialog__copy">
        为 <strong>{{ passwordDialog.user?.name }}</strong> 设置新密码，提交后该用户的原会话会立即失效。
      </p>
      <VanField
        v-model="passwordDialog.password"
        class="mobile-form-dialog__field"
        label="新密码"
        :type="passwordDialog.showPassword ? 'text' : 'password'"
        :right-icon="passwordDialog.showPassword ? 'closed-eye' : 'eye-o'"
        :maxlength="64"
        autocomplete="new-password"
        placeholder="至少 8 位"
        :disabled="passwordDialog.submitting"
        :error-message="passwordDialog.error"
        @update:model-value="passwordDialog.error = ''"
        @click-right-icon="passwordDialog.showPassword = !passwordDialog.showPassword"
      />
      <template #footer>
        <div class="mobile-form-dialog__footer">
          <VanButton block plain native-type="button" :disabled="passwordDialog.submitting" @click="passwordDialog.visible = false">取消</VanButton>
          <VanButton
            block
            type="primary"
            native-type="button"
            :disabled="passwordDialog.submitting || passwordDialog.password.length < 8"
            :loading="passwordDialog.submitting"
            loading-text="重置中…"
            @click="submitPasswordReset"
          >
            确认重置
          </VanButton>
        </div>
      </template>
    </VanDialog>
  </div>
</template>

<script src="./AdminConsole.js"></script>

<style src="./AdminConsole.css"></style>
