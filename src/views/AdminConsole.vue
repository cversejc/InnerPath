<template>
  <div class="admin-console-view">
    <OperationsShell
      shell-class="admin-shell"
      app-class="admin-app"
      brand-subtitle="运营中心"
      brand-to="/admin"
      :current-label="activeTabInfo.label"
      :logging-out="loggingOut"
      :nav-groups="operationsNavGroups"
      :operator-name="operatorName"
      operator-role="系统管理员"
      section-label="运营中心"
      status-label="ADMIN OPERATIONS"
      @select="switchTab"
      @logout="handleLogout"
    >
      <template #topbar-actions>
        <span class="sync-state" role="status" aria-live="polite"><i :class="{ live: dashboardLoading }"></i>{{ dashboardLoading ? '正在同步' : lastUpdated ? `更新于 ${lastUpdated}` : '等待同步' }}</span>
        <VanButton class="operations-refresh-button" type="default" plain native-type="button" :disabled="activeLoading" :loading="activeLoading" :aria-busy="activeLoading" aria-label="刷新当前数据" title="刷新当前数据" @click="refreshActive">
          <template #icon><IconMark name="refresh" /></template>
        </VanButton>
      </template>

      <main class="admin-main">
        <BrandPageHeader
          class="admin-page-header"
          contained
          compact
          :eyebrow="activeTabInfo.eyebrow"
          :title="activeTabInfo.label"
          :description="activeTabInfo.description"
          :seal="activeTabInfo.index"
        >
          <span class="admin-header-meta"><strong>内部工作台</strong><small>数据仅对管理员可见</small></span>
        </BrandPageHeader>

        <div v-if="message" class="console-message" role="status" aria-live="polite">
          <span>{{ message }}</span>
          <AdminIconButton icon="close" label="关闭提示" @click="message = ''" />
        </div>

      <AdminDashboardSection
        v-if="activeTab === 'overview'"
        :auto-refresh="autoRefresh"
        :chart-grid-lines="dashboardViewModel.chartGridLines"
        :dashboard="dashboard"
        :dashboard-load-error="dashboardLoadError"
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
        @retry-dashboard="loadDashboard"
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
        :assignment-error="assignmentError"
        :assignment-request="assignmentRequest"
        :assignment-saving-key="assignmentSavingKey"
        :consultant-workloads="consultantWorkloads"
        :filters="requestFilters"
        :loading="requestsLoading"
        :page="requestPage"
        :page-size="requestPageSize"
        :request-kind="requestKind"
        :retrying-request-key="retryingRequestKey"
        :service-requests="adminServiceRequests"
        @retry-service-request="retryAdminServiceRequest"
        @retry-calendar-request="retryAdminCalendarRequest"
        @change-kind="setRequestKind"
        @change-page="changeRequestPage"
        @assign-request="assignAdminRequest"
        @close-assignment="closeAdminAssignment"
        @open-report="openReport"
        @open-workflow="openReportWorkflow"
        @open-assignment="openAdminAssignment"
        @open-user="openUserDetail"
        @reset-filters="resetAdminRequestFilters"
        @search="searchAdminRequests"
      />

      <AdminServiceFeedbackSection
        v-else-if="activeTab === 'feedback'"
        :assignees="feedbackAssignees"
        :feedback="serviceFeedback"
        :filters="feedbackFilters"
        :view="feedbackView"
        :quality-summary="serviceQualitySummary"
        :summary-period-days="serviceQualityPeriodDays"
        :summary-loading="serviceQualityLoading"
        :summary-error="serviceQualityError"
        :loading="feedbackLoading"
        :quality-filters="qualityFilters"
        :quality-issues="qualityIssues"
        :quality-loading="qualityLoading"
        :quality-page="qualityPage"
        :quality-page-size="qualityPageSize"
        :page="feedbackPage"
        :page-size="feedbackPageSize"
        :saving-id="feedbackSavingId"
        @change-page="changeFeedbackPage"
        @save="saveFeedback"
        @search="searchFeedback"
        @select-view="setFeedbackView"
        @change-summary-period="changeServiceQualityPeriod"
        @search-quality="searchQualityIssues"
        @change-quality-page="changeQualityPage"
      />

      <AdminCalendarSection
        v-else-if="activeTab === 'calendar'"
        :calendar-form="calendarForm"
        :calendar-import-json="calendarImportJson"
        :calendar-loading="calendarLoading"
        :calendar-preview-decision-logs="calendarPreviewDecisionLogs"
        :calendar-preview-error="calendarPreviewError"
        :calendar-preview-id="calendarPreviewId"
        :calendar-preview-loading="calendarPreviewLoading"
        :calendar-saving="calendarSaving"
        :calendar-user-search="calendarUserSearch"
        :calendar-users="calendarUsers"
        :calendars="calendars"
        :selected-calendar-user="selectedCalendarUser"
        :show-calendar-import="showCalendarImport"
        @add-entry="addCalendarEntry"
        @archive-calendar="archiveCalendar"
        @cancel-edit="cancelCalendarEdit"
        @toggle-calendar-preview="toggleCalendarPreview"
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
        :consultant-workloads="consultantWorkloads"
        :workload-period-days="consultantWorkloadPeriodDays"
        :workload-error="consultantWorkloadError"
        :workload-loading="consultantWorkloadLoading"
        :specialty-saving-id="consultantSpecialtySavingId"
        :staff-loading="staffLoading"
        :staff-users="staffUsers"
        @invite="inviteStaff"
        @open-activity="openConsultantActivity"
        @open-requests="openConsultantServiceRequests"
        @change-workload-period="changeConsultantWorkloadPeriod"
        @update-specialties="updateConsultantSpecialties"
      />

      <AdminLLMSection v-else-if="activeTab === 'models'" />

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
        :timeline-error="timelineError"
        :timeline-loading="timelineLoading"
        @close-active="closeActiveDrawer"
        @close-log="closeLogDetail"
        @close-report="closeReportDetail"
        @close-user="closeUserDetail"
        @open-calendar-for-user="openCalendarForUser"
        @open-log="openLogDetail"
        @open-report="openReport"
        @retry-user-timeline="loadUserTimeline"
        @save-user-profile="saveUserProfile"
        @set-user-panel-tab="setUserPanelTab"
      />
      </main>
    </OperationsShell>

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
