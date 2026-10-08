<template>
  <div class="staff-console-view" :class="{ 'staff-shell-node-focus': selectedReportStepKey && reportCase }">
    <OperationsShell
      shell-class="staff-shell"
      app-class="staff-app"
      brand-subtitle="运营中心"
      brand-to="/staff"
      :current-label="workspaceCurrentLabel"
      :logging-out="loggingOut"
      :nav-groups="operationsNavGroups"
      :operator-name="operatorName"
      :operator-role="admin ? '系统管理员' : specialtyLabel"
      section-label="咨询师工作台"
      :status-label="admin ? 'ADMIN OPERATIONS' : 'CONSULTANT OPERATIONS'"
      @logout="handleLogout"
    >
      <template #topbar-actions>
        <span v-if="!selectedRequest" class="live-state" role="status" aria-live="polite"><i :class="{ active: loading || pollingTask || reportCaseLoading || reportAnalysisPending }"></i>{{ reportAnalysisPending ? '分析建议处理中' : pollingTask ? '内容生成中' : reportCaseLoading ? '正在打开报告' : loading ? '正在同步' : '已同步' }}</span>
        <VanButton v-if="!selectedRequest" class="operations-refresh-button" type="default" plain native-type="button" :disabled="loading" :loading="loading" aria-label="刷新报告申请" title="刷新报告申请" @click="loadRequests">
          <template #icon><IconMark name="refresh" /></template>
        </VanButton>
      </template>

    <main class="staff-main" :class="{ 'staff-main-workspace': selectedRequest }">
      <BrandPageHeader v-if="!selectedRequest" class="staff-heading" contained compact eyebrow="REVIEW ROOM" title="选择一份报告" description="打开报告后，将在独立工作区查看进度并完成当前任务。" seal="照见">
        <template #actions>
          <VanButton class="secondary-button" type="default" plain native-type="button" :disabled="loading" @click="loadRequests">刷新列表</VanButton>
        </template>
      </BrandPageHeader>

      <header v-else-if="selectedReportStepKey && reportCase" class="workbench-focus-header">
        <VanButton plain native-type="button" aria-label="返回报告处理总览" @click="openReportOverview">报告总览</VanButton>
        <strong :title="workspace?.user?.name || selectedRequest.user_name">{{ workspace?.user?.name || selectedRequest.user_name || '未填写姓名' }}</strong>
        <span>申请 {{ selectedRequest.id }}</span>
      </header>
      <header v-else class="workbench-global-header">
        <VanButton class="workbench-back-button" type="default" plain native-type="button" @click="closeReportWorkspace">返回报告列表</VanButton>
        <div class="workbench-client-heading">
          <p class="section-kicker">人生说明书处理</p>
          <h1>{{ workspace?.user?.name || selectedRequest.user_name || '未填写姓名' }}</h1>
          <p>{{ workspace?.user?.phone || '未填写联系方式' }} · 申请编号 {{ selectedRequest.id }} · {{ consultationTypeLabel(workspace?.request?.consultation_type) }}</p>
        </div>
        <div class="workbench-header-actions">
          <VanButton class="secondary-button compact-button workbench-overview-button" type="default" plain native-type="button" aria-label="返回报告处理总览" @click="openReportOverview">回到处理总览</VanButton>
          <span :class="['status-badge', workbenchStatusClass]">{{ workbenchStatusLabel }}</span>
        </div>
      </header>

      <p v-if="message" class="console-message" role="status" aria-live="polite">{{ message }}</p>

      <section v-if="!selectedRequest" class="staff-toolbar paper-card" aria-label="报告筛选">
        <div class="scope-tabs" role="tablist" aria-label="申请范围">
          <button v-for="item in scopeOptions" :key="item.id" type="button" role="tab" :aria-selected="scope === item.id" :class="{ active: scope === item.id }" @click="changeScope(item.id)">{{ item.label }}</button>
        </div>
        <div class="staff-filters">
          <label><span>类型</span><select v-model="serviceType" @change="loadRequests"><option value="">全部报告申请</option><option value="report">报告</option></select></label>
          <label><span>状态</span><select v-model="statusFilter" @change="loadRequests"><option value="">全部状态</option><option v-for="status in statusOptions" :key="status" :value="status">{{ statusLabel(status) }}</option></select></label>
        </div>
      </section>

      <section class="staff-workspace-grid" :class="{ 'report-selection-grid': !selectedRequest, 'report-fullscreen-grid': selectedRequest }">
        <aside v-if="!selectedRequest" class="console-card paper-card request-list-panel">
          <div class="section-row"><div><p class="eyebrow">待办报告 · {{ requests.total }}</p><h2>报告申请</h2><p>{{ scopeDescription }}</p></div></div>
          <div class="selection-summary" aria-label="报告申请概览">
            <div><strong>{{ requests.items.filter(item => ['submitted', 'accepted', 'failed'].includes(item.status)).length }}</strong><span>需要关注</span></div>
            <div><strong>{{ requests.items.filter(item => ['ai_processing', 'ai_ready', 'reviewing'].includes(item.status)).length }}</strong><span>处理中</span></div>
            <div><strong>{{ requests.items.filter(item => item.status === 'delivered').length }}</strong><span>已交付</span></div>
          </div>
          <div class="request-list" aria-label="服务申请列表">
            <button v-for="item in requests.items" :key="item.id" type="button" class="request-item" :class="{ selected: selectedRequest?.id === item.id }" :aria-pressed="selectedRequest?.id === item.id" @click="selectRequest(item)">
              <span class="request-item-icon"><IconMark name="reports" /></span>
              <span class="request-item-copy"><strong>{{ item.user_name || `用户 #${item.user_id}` }}</strong><small>申请编号 {{ item.id }} · {{ formatDateTime(item.created_at) }}</small><small v-if="item.current_step_key" class="request-item-step">{{ reportStepLabel(item.current_step_key) }} · {{ reportStepStatusLabel(item.current_step_status) }}</small><em>{{ consultationTypeLabel(item.consultation_type) }} · {{ topicLabel(item.request_preview?.selected_topics) }}</em></span>
              <span class="request-item-status">{{ statusLabel(item.status) }}</span>
            </button>
            <div v-if="!requests.items.length" class="empty-cell">当前筛选下没有申请。</div>
          </div>
        </aside>

        <section v-if="selectedRequest" class="console-card paper-card workspace-panel" aria-live="polite">
          <div v-if="loading && !workspace" class="workspace-loading" role="status">正在打开报告工作区…</div>
          <div v-else-if="ownsSelectedRequest && !workspace" class="workspace-load-error" role="alert">暂时无法读取报告资料。请返回列表刷新后重试。</div>
          <div v-else-if="selectedRequest && !workspace" class="request-preview">
            <div class="preview-note"><strong>{{ selectedRequest.user_name || '未填写姓名' }}</strong><p>这份报告正在等待对应专业咨询师。接单后会开放申请资料，并由你负责本专业的节点。</p></div>
            <dl class="detail-list"><div><dt>关注主题</dt><dd>{{ requestGoal(selectedRequest) }}</dd></div><div><dt>补充说明</dt><dd>{{ selectedRequest.request_preview?.additional_info || '暂无补充说明' }}</dd></div></dl>
            <VanButton v-if="canAcceptSelectedRequest" class="primary-button" type="primary" native-type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '正在接单…' : '接单并查看资料' }}</VanButton>
            <p v-else class="preview-lock">当前申请已分配给其他咨询师。返回列表后可切换查看范围。</p>
          </div>

          <div v-else-if="workspace" class="workspace-content">
            <DeliveredReportSummary v-if="!selectedReportStepKey" :request="workspace.request" @view-analysis="selectReportNode('S1')" />
            <div v-if="admin && !selectedReportStepKey && reportCase?.application_snapshot?.collaboration_contract" class="assignment-row">
              <label>咨询方向<select v-model="consultationType" :disabled="assignmentSaving" @change="saveConsultationType"><option value="metaphysics">命理</option><option value="psychology">心理</option><option value="integrated">综合（命理 + 心理）</option></select></label>
              <label v-for="specialty in ['mingli', 'psychology']" :key="specialty">{{ specialty === 'mingli' ? '命理负责人' : '心理负责人' }}<select :value="workspace.request['assigned_' + specialty + '_consultant_id'] || ''" :disabled="assignmentSaving" @change="assignProfessional(specialty, $event.target.value)"><option value="">待接单</option><option v-for="consultant in consultants.filter(item => consultantCanHandle(item, specialty))" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select></label>
            </div>
            <div v-else-if="admin && !selectedReportStepKey" class="assignment-row">
              <label v-if="workspace.request.service_type === 'report'">咨询方向<select v-model="consultationType" :disabled="assignmentSaving" @change="changeConsultationType"><option value="metaphysics">命理</option><option value="psychology">心理</option><option value="integrated">综合（命理 + 心理）</option></select></label>
              <label>处理咨询师<select v-model="assignmentId" :disabled="assignmentSaving"><option :value="null">未分配</option><option v-for="consultant in assignableConsultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select></label>
              <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!assignmentChanged || assignmentSaving" :loading="assignmentSaving" loading-text="保存中…" @click="assignConsultant">保存分配</VanButton>
              <small>可按咨询方向分配咨询师；修改不会覆盖已有报告版本。</small>
            </div>

            <section v-if="workspace.request.service_type === 'report'" class="report-case-workspace" aria-label="人生说明书处理工作区">
              <div v-if="reportCaseLoading" class="empty-cell" role="status">正在读取报告内容…</div>
              <template v-else-if="reportCase">
                <section v-if="canImportReportCase()" class="report-import-entry" aria-label="快速导入报告">
                  <div>
                    <p class="eyebrow">FAST LANE</p>
                    <h3>已有写好的报告？</h3>
                    <p>粘贴或上传完整正文，系统会自动整理为“你是谁 / 卡在哪 / 往哪去”三段，并标记前五个节点完成，直接进入第 6 步最终确认。AI 检查是可选的参考、不设任何门槛；咨询师核对报告后随时可以确认并交付。</p>
                  </div>
                  <VanButton class="primary-button compact-button" type="primary" native-type="button" @click="openReportImport">快速导入报告</VanButton>
                </section>
                <details class="report-source-panel" open>
                  <summary>
                    <strong>用户完整信息</strong>
                    <span>档案 {{ reportProfileItems.length }} 项 · 申请补充 {{ reportContextItems.length }} 项</span>
                  </summary>
                  <p class="report-source-note">来自用户申请时填写的完整资料；处理任一节点时都可在这里核对，节点内的上游输入仍保留原始记录。</p>
                  <div class="report-source-grid">
                    <section class="facts-panel" aria-label="用户档案">
                      <div class="panel-heading"><div><p class="eyebrow">USER PROFILE</p><h4>用户档案</h4></div></div>
                      <dl v-if="reportProfileItems.length" class="detail-list source-list">
                        <div v-for="item in reportProfileItems" :key="item.title"><dt>{{ item.title }}</dt><dd>{{ item.body }}</dd></div>
                      </dl>
                      <p v-else class="empty-cell">申请中没有留下用户档案信息。</p>
                    </section>
                    <section class="facts-panel" aria-label="本次申请补充信息">
                      <div class="panel-heading"><div><p class="eyebrow">APPLICATION CONTEXT</p><h4>本次申请补充</h4></div></div>
                      <dl v-if="reportContextItems.length" class="detail-list source-list">
                        <div v-for="item in reportContextItems" :key="item.key"><dt>{{ item.title }}</dt><dd>{{ item.body }}</dd></div>
                      </dl>
                      <p v-else class="empty-cell">本次申请没有补充说明。</p>
                    </section>
                  </div>
                </details>
                <ReportNodeWorkbench
                  :report-case="reportCase"
                  :actor="staffActor"
                  :selected-step-key="selectedReportStepKey"
                  :section="workspaceSection"
                  :tool-pending="nodeToolPending"
                  :generation-status="reportGeneration.status"
                  :content="reportCaseContent"
                  :current-step="currentReportStep"
                  :narrative-plan="reportNarrative.current_plan"
                  :quality="reportQuality"
                  :completion-gate="reportCaseCompletionGate"
                  :loading="reportStepSaving"
                  :waiting-for-user="workspace.request.status === 'needs_info'"
                  :review-busy="reportReviewBusy"
                  :can-reopen="!['DELIVERED', 'CANCELLED'].includes(reportCase.status)"
                  @start-step="startReportStep"
                  @complete-step="completeReportStep"
                  @toggle-return="reportStepReturn.visible = !reportStepReturn.visible"
                  @to-section="setReportWorkspaceSection"
                  @select-step="selectReportNode"
                  @reopen="reopenReportStep"
                  @request-info="openReportInfoPanel"
                  @review-busy="reportReviewBusy = $event"
                  @review-changed="loadReportCaseData(reportCase.id, { silent: true })"
                  @review-approved="continueWholeNodeReview"
                >
                <template #review-tools>
                  <div v-if="showInfoPanel && infoStepKey === selectedReportStepKey" class="info-panel report-info-panel">
                    <label>向用户补充提问<textarea v-model.trim="infoReason" rows="3" maxlength="1000" placeholder="说明需要补充的事实及其与当前判断的关系"></textarea></label>
                    <VanButton plain native-type="button" @click="showInfoPanel = false">取消</VanButton><VanButton type="primary" native-type="button" :disabled="infoSaving || !infoReason" @click="requestInfo">发送补充问题</VanButton>
                  </div>
                  <div v-if="reportStepReturn.visible" class="report-return-form">
                    <label>退回到哪一步<select v-model="reportStepReturn.targetStepKey"><option value="">选择前序节点</option><option v-for="step in reportReturnTargets" :key="step.step_key" :value="step.step_key">{{ reportStepLabel(step.step_key) }}</option></select></label>
                    <label>退回原因<textarea v-model.trim="reportStepReturn.reason" rows="2" maxlength="1000"></textarea></label>
                    <VanButton plain native-type="button" @click="reportStepReturn.visible = false">取消</VanButton><VanButton type="primary" native-type="button" :disabled="!reportStepReturn.targetStepKey || !reportStepReturn.reason" @click="returnReportStep">退回修订</VanButton>
                  </div>
                  <p v-if="workspace.request.status === 'needs_info'" class="report-waiting-note">等待用户回复：{{ workspace.request.needs_info_reason }}</p>
                </template>

                <div v-if="workspaceSection === 'overview' && showInfoPanel && infoStepKey === selectedReportStepKey" class="info-panel report-info-panel">
                  <label>向用户补充提问<textarea v-model.trim="infoReason" rows="3" maxlength="1000" placeholder="写清楚需要补充的事实，以及它与当前节点判断的关系。"></textarea></label>
                  <div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="showInfoPanel = false; infoReason = ''; infoStepKey = ''">取消</VanButton><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="infoSaving || !infoReason" :loading="infoSaving" @click="requestInfo">{{ infoSaving ? '发送中…' : '发送补充问题' }}</VanButton></div>
                </div>
                <div v-if="workspace.request.status === 'needs_info' && workspace.request.needs_info_reason" class="report-waiting-note" role="status">等待用户回复：{{ workspace.request.needs_info_reason }}</div>

                <div v-if="workspaceSection === 'overview' && reportStepReturn.visible" class="report-return-form">
                  <label>退回到哪一步<select v-model="reportStepReturn.targetStepKey"><option value="">选择已完成的前序步骤</option><option v-for="step in reportReturnTargets" :key="step.step_key" :value="step.step_key">第 {{ step.sequence_no }} 步 · {{ reportStepLabel(step.step_key) }}</option></select></label>
                  <label>退回原因<textarea v-model.trim="reportStepReturn.reason" rows="2" maxlength="1000"></textarea></label>
                  <VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportStepSaving || !reportStepReturn.targetStepKey || !reportStepReturn.reason" :loading="reportStepSaving" @click="submitReportStepReturn">确认退回</VanButton>
                </div>

                <section id="report-section-writing" v-if="workspaceSection === 'writing'" class="report-data-panel narrative-panel" aria-label="报告主线与写作">
                  <div class="panel-heading">
                    <div><p class="eyebrow">报告内容</p><h3>叙事方案与报告写作</h3></div>
                    <span>{{ narrativePlanStatusLabel }}</span>
                  </div>
                  <p class="narrative-progress">确认主线 → 核对编排 → 生成正文 → 完整报告审阅 → S5 节点复核</p>
                  <div class="node-writing-modes" aria-label="写作工作界面"><VanButton plain native-type="button" :disabled="reportNarrativeSaving || reportReviewBusy" :aria-pressed="nodeWritingMode === 'plan'" @click="nodeWritingMode='plan'">1. 主线方案</VanButton><VanButton plain native-type="button" :disabled="reportNarrativeSaving || reportReviewBusy" :aria-pressed="nodeWritingMode === 'allocation'" @click="nodeWritingMode='allocation'">2. 逐段编排</VanButton><VanButton plain native-type="button" :disabled="reportNarrativeSaving || reportReviewBusy" :aria-pressed="nodeWritingMode === 'progress'" @click="nodeWritingMode='progress'">3. 生成进度</VanButton></div>
                  <VanButton v-if="reportNarrative.current_plan?.status === 'CONFIRMED' && nodeWritingMode === 'plan'" plain native-type="button" :disabled="reportNarrativeSaving || reportReviewBusy" @click="nodeWritingMode='allocation'">主线已确认，继续核对编排</VanButton>
                  <VanButton v-if="reportGeneration.status === 'READY_FOR_REVIEW' && nodeWritingMode !== 'plan'" type="primary" native-type="button" :disabled="reportReviewBusy || reportNarrativeSaving" @click="beginReportFragmentReview">进入完整报告审阅</VanButton>
                  <template v-if="nodeWritingMode === 'plan'">
                  <WorkbenchRecordPicker v-model="nodeRecordKeys.candidate" :items="nodeNarrativeCandidates" label="选择主线候选" />
                  <div v-if="reportNarrative.current_plan" class="narrative-current-plan">
                    <strong>{{ consultantText(reportNarrative.current_plan.plan_json.core_theme, '尚未确定报告主线') }}</strong>
                    <details class="node-source-details"><summary>查看已选主线的重点判断</summary><small>{{ findingTitles(reportNarrative.current_plan.plan_json.must_include_findings) || '尚未选择重点判断' }}</small></details>
                    <p v-if="reportNarrative.current_plan.status === 'STALE'" class="stale-note">前序判断已有更新，需要重新生成并确认报告主线。</p>
                  </div>
                  <div class="narrative-actions">
                    <VanButton v-if="canEditSelectedReportStep && selectedReportStepKey === 'S5'" class="primary-button compact-button" type="primary" native-type="button" :disabled="nodeToolPending" :loading="reportNarrativeSaving" @click="generateNarrativeCandidates">生成报告主线建议</VanButton>
                  </div>
                  <div v-for="run in visibleNarrativeCandidateRuns" :key="run.id" class="narrative-run">
                    <div class="asset-item-heading"><div><strong>报告主线建议</strong><span class="asset-status">{{ assetStatusLabel(run.status) }}</span></div></div>
                    <p class="ai-source-label">AI 生成的主线候选，属于待审核建议；主线引用仍以已确认判断为准。</p>
                    <p v-if="run.status === 'FAILED'" class="task-error">报告主线建议暂时无法生成，请稍后重试。</p>
                    <article v-for="candidate in run.output_parsed?.candidates || []" :key="candidate.candidate_key" class="narrative-candidate">
                      <div class="asset-item-heading"><div><strong>{{ consultantText(candidate.theme, '报告主线建议') }}</strong></div></div>
                      <p>{{ consultantText(candidate.rationale) }}</p>
                      <details class="node-source-details"><summary>查看主线引用的判断</summary><small class="asset-source">主要依据：{{ findingTitles(candidate.supporting_findings) || '暂无' }}<template v-if="candidate.deemphasized_findings?.length"> · 暂不展开：{{ findingTitles(candidate.deemphasized_findings) }}</template></small></details>
                      <div v-if="canEditSelectedReportStep && selectedReportStepKey === 'S5'" class="narrative-choice-form">
                        <label>核心主题<input v-model.trim="narrativeCandidateDrafts[narrativeDraftKey(run, candidate)].core_theme" maxlength="1000"></label>
                        <fieldset><legend>报告需要重点回应的判断</legend><label v-for="findingKey in candidate.supporting_findings" :key="findingKey" class="narrative-checkbox"><input v-model="narrativeCandidateDrafts[narrativeDraftKey(run, candidate)].must_include_findings" type="checkbox" :value="findingKey">{{ findingTitle(findingKey) }}</label></fieldset>
                        <label>报告希望强调的方向<select v-model="narrativeCandidateDrafts[narrativeDraftKey(run, candidate)].self_direction"><option value="">暂不指定</option><option v-for="findingKey in candidate.supporting_findings" :key="findingKey" :value="findingKey">{{ findingTitle(findingKey) }}</option></select></label>
                        <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportNarrativeSaving || run.status !== 'COMPLETED'" :loading="reportNarrativeSaving" @click="confirmNarrativeCandidate(run, candidate)">选择并确认这条主线</VanButton>
                      </div>
                    </article>
                    <div v-if="canEditSelectedReportStep && selectedReportStepKey === 'S5' && run.status === 'COMPLETED'" class="ai-feedback-form">
                      <label>针对这次主线建议的反馈<textarea v-model="narrativeFeedbackDrafts[run.id]" rows="3" maxlength="4000" placeholder="指出需要调整的重点；反馈作为改进线索，不会替代已确认判断。"></textarea></label>
                      <small v-if="run.context_snapshot?.authoring_feedback_source_run_id">本次结果基于运行 #{{ run.context_snapshot.authoring_feedback_source_run_id }} 的反馈生成。</small>
                      <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportNarrativeSaving || !narrativeFeedbackDrafts[run.id]?.trim()" :loading="reportNarrativeSaving" @click="rerunNarrativeWithFeedback(run)">按反馈重跑主线建议</VanButton>
                    </div>
                  </div>
                  <div v-if="reportNarrative.current_plan?.status === 'CONFIRMED' && !reportContentPlan" class="stale-note">这条报告主线还没有逐段内容安排。请重新生成并确认主线后继续。</div>
                  </template>
                  <section v-if="nodeWritingMode === 'allocation' && reportContentPlan" class="narrative-allocation" aria-label="报告内容分配与顺序生成">
                    <div class="narrative-allocation-heading">
                      <strong>内容分配 · {{ reportContentPlan.fragments?.length || 0 }} 段</strong>
                      <span class="asset-status">{{ reportContentPlan.status === 'READY' ? '编排已就绪' : assetStatusLabel(reportContentPlan.status) || '待处理' }}</span>
                    </div>
                    <p class="narrative-progress">
                      {{ reportGenerationStatusLabel }}
                      <template v-if="reportGeneration.completed_fragment_keys?.length"> · 已完成 {{ reportGeneration.completed_fragment_keys.length }}/{{ reportContentPlan.fragments?.length || 0 }} 段</template>
                    </p>
                    <p v-if="reportContentPlan.status === 'BLOCKED'" class="stale-note">报告内容安排缺少已确认的依据，暂时不能开始写作。请先回到前序步骤补充并确认相关判断。</p>
                    <p v-for="issue in reportContentPlan.gaps || []" :key="`${issue.type}:${issue.target_fragment}`" class="stale-note">{{ issueLabel(issue.type) }}：{{ consultantText(issue.needed) }}</p>
                    <p v-for="(issue, issueIndex) in reportGeneration.issues || []" :key="`${issue.type}:${issue.target_fragment || ''}:${issue.skill_run_id || issueIndex}`" class="task-error">
                      {{ issueLabel(issue.type) }}<template v-if="issue.severity"> · {{ issueSeverityLabel(issue.severity) }}</template><template v-if="issue.target_fragment"> · {{ fragmentTitle(issue.target_fragment) }}</template>：{{ consultantText(issue.message) }}
                      <small v-if="issue.suggestion">处理建议：{{ consultantText(issue.suggestion) }}</small>
                    </p>
                    <div class="narrative-chapter-checks" aria-label="章节校验状态">
                      <span v-for="chapter in reportChapterChecks" :key="chapter.chapterKey">
                        {{ chapterLabel(chapter.chapterKey) }} · {{ assetStatusLabel(chapter.status) || '待检查' }}
                      </span>
                    </div>
                    <WorkbenchRecordPicker v-model="nodeRecordKeys.planned" :items="nodePlannedFragments" key-field="fragment_key" label="选择编排段落" />
                    <ol class="narrative-allocation-list">
                      <li v-for="fragment in visiblePlannedFragments" :key="fragment.fragment_key">
                        <div class="narrative-allocation-row">
                            <strong>{{ String(fragment.sequence_no).padStart(2, '0') }} · {{ fragmentTitle(fragment.fragment_key, fragment) }}</strong>
                          <span class="asset-status">{{ reportFragmentStatus(fragment.fragment_key) }}</span>
                        </div>
                        <small>{{ chapterLabel(fragment.chapter) }} · {{ consultantText(fragment.purpose) }}</small>
                        <small>主要依据：{{ findingTitles(fragment.finding_refs) || '暂无' }}</small>
                        <small v-if="fragment.analysis_refs?.length">相关分析：{{ fragmentTitles(fragment.analysis_refs) }}</small>
                        <small v-if="fragment.action_refs?.length">行动建议：{{ fragmentTitles(fragment.action_refs) }}</small>
                        <small>本段重点：{{ fragment.must_cover?.map(item => consultantText(item)).join('、') || '按报告主线展开' }}</small>
                      </li>
                    </ol>
                    <p v-if="reportGeneration.status === 'CHAPTER_COHERENCE_CHECK'" class="narrative-progress">正在检查“{{ chapterLabel(reportGeneration.current_chapter_key) }}”，处理完成后会继续生成下一部分。</p>
                    <p v-if="reportGeneration.status === 'COHERENCE_CHECK'" class="narrative-progress">各部分已生成，正在检查全文主线和内容重复。</p>
                    <p v-if="reportGeneration.coherence?.status === 'PASSED'" class="narrative-progress">全文连贯性检查已通过。请通读完整报告，核对来源并完成整体审阅。</p>
                    <VanButton v-if="canEditSelectedReportStep && selectedReportStepKey === 'S5' && reportContentPlan.status === 'READY' && !['IN_PROGRESS', 'CHAPTER_COHERENCE_CHECK', 'CHAPTER_COHERENCE_BLOCKED', 'CHAPTER_COHERENCE_FAILED', 'CHAPTER_COHERENCE_STALE', 'COHERENCE_CHECK', 'READY_FOR_REVIEW', 'COHERENCE_BLOCKED', 'COHERENCE_FAILED', 'COHERENCE_STALE', 'NEEDS_INPUT', 'BLOCKED'].includes(reportGeneration.status)" class="primary-button compact-button" type="primary" native-type="button" :disabled="reportNarrativeSaving" :loading="reportNarrativeSaving" @click="generateCompleteReport">
                      {{ reportGeneration.status === 'FAILED' || reportGeneration.status === 'PAUSED' ? '继续生成未完成内容' : '按顺序生成报告内容' }}
                    </VanButton>
                    <VanButton v-if="canEditSelectedReportStep && selectedReportStepKey === 'S5' && ['READY_FOR_REVIEW', 'CHAPTER_COHERENCE_BLOCKED', 'CHAPTER_COHERENCE_FAILED', 'CHAPTER_COHERENCE_STALE', 'COHERENCE_BLOCKED', 'COHERENCE_FAILED', 'COHERENCE_STALE'].includes(reportGeneration.status)" class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportNarrativeSaving" :loading="reportNarrativeSaving" @click="runReportCoherenceCheck">
                      {{ reportGeneration.status.startsWith('CHAPTER_') ? `重新检查${chapterLabel(reportGeneration.current_chapter_key)}` : '重新检查整篇报告' }}
                    </VanButton>
                    <p v-if="reportGeneration.status === 'READY_FOR_REVIEW'" class="narrative-progress">报告内容已生成。请通读全文及依据；有问题时局部修订，完成后整体确认。</p>
                  </section>
                  <div v-if="nodeWritingMode === 'progress'" class="narrative-progress">{{ reportGenerationStatusLabel }} · 已完成 {{ reportGeneration.completed_fragment_keys?.length || 0 }} / {{ reportContentPlan?.fragments?.length || 0 }} 段</div>
                  <div v-for="run in nodeWritingMode === 'progress' ? reportNarrative.fragment_runs : []" :key="run.id" class="narrative-run">
                    <div class="asset-item-heading"><div><strong>{{ fragmentTitle(run.target_key) }}</strong><span class="asset-status">{{ assetStatusLabel(run.status) }}</span></div></div>
                    <p v-if="run.output_parsed" class="ai-source-label">AI 生成的报告草稿；请基于原始资料和已确认判断审核后再采用。</p>
                    <p v-if="run.status === 'FAILED'" class="task-error">这段内容暂时无法生成，请稍后重试。</p>
                    <p v-else-if="run.output_parsed?.status === 'MISSING_SEMANTIC_SUPPORT'" class="stale-note">当前内容缺少已确认的判断依据，暂未补写相关结论。请先回到判断审核页面处理。</p>
                    <div v-if="canEditSelectedReportStep && selectedReportStepKey === 'S5' && run.status === 'COMPLETED'" class="ai-feedback-form">
                      <label>针对这段草稿的反馈<textarea v-model="narrativeFeedbackDrafts[run.id]" rows="3" maxlength="4000" placeholder="说明需要改进的表达或报告重点，不要填写未经确认的用户事实。"></textarea></label>
                      <small v-if="run.context_snapshot?.authoring_feedback_source_run_id">本次结果基于运行 #{{ run.context_snapshot.authoring_feedback_source_run_id }} 的反馈生成。</small>
                      <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportNarrativeSaving || !narrativeFeedbackDrafts[run.id]?.trim()" :loading="reportNarrativeSaving" @click="rerunReportFragmentWithFeedback(run)">按反馈重新生成本段</VanButton>
                    </div>
                  </div>
                </section>

                <section v-if="workspaceSection === 'signoff' && selectedReportStepKey === 'S6' && reportCase.review_policy_version !== 'six-node-review-v1'" class="report-data-panel quality-panel" aria-label="第六步最终确认">
                  <div class="panel-heading">
                    <div><p class="eyebrow">最终确认</p><h3>{{ reportQuality.advisory_only ? '确认最终稿并交付' : '完成最终复核' }}</h3></div>
                    <span>{{ reportQuality.final_gate_override ? '交付授权已记录' : reportManuscriptPendingCount ? `还有 ${reportManuscriptPendingCount} 段未确认` : reportManuscriptStaleCount ? `还有 ${reportManuscriptStaleCount} 段来源待复核` : '可以确认' }}</span>
                  </div>
                  <p v-if="reportQuality.advisory_only" class="narrative-progress">AI 检查只提供参考，不设交付门槛；请先在“修改后稿件”通读并确认最终稿，再在这里完成交付授权。这一步不重复节点签核。</p>
                  <p v-else class="narrative-progress">检查条件已满足后，在这里完成最终人工确认并生成交付版本。</p>
                  <p v-if="reportManuscriptPendingCount" class="stale-note" role="status">还有 {{ reportManuscriptPendingCount }} 段修订尚未确认，交付版本只会包含已确认的正文。请先确认修改后稿件。</p>
                  <p v-else-if="reportManuscriptStaleCount" class="stale-note" role="status">有 {{ reportManuscriptStaleCount }} 段正文的来源依据已更新，请先复核来源再确认交付。</p>
                  <p v-if="reportQuality.final_gate_override" class="quality-clear-state">最终复核已完成，交付授权已记录<template v-if="reportQuality.final_gate_override.note">：{{ reportQuality.final_gate_override.note }}</template></p>
                  <p v-else-if="reportFinalGateReady" class="quality-clear-state">{{ reportQuality.advisory_only ? (reportQuality.latest_validator_run ? '检查结果仅供参考，现在就可以完成最终人工确认。' : '尚未运行检查；检查可选、不设门槛，随时可以完成最终人工确认。') : '检查条件已满足，请完成最终人工确认。' }}</p>
                  <div v-if="canEditSelectedReportStep && selectedReportStepKey === 'S6'" class="final-gate-controls final-gate-approval">
                    <div v-if="reportQuality.advisory_only && reportQuality.unresolved_advisories.length" class="advisory-list" role="status">
                      <strong>{{ reportQuality.unresolved_advisories.length }} 条检查建议未处理</strong>
                      <p>这些建议不阻断交付。可以逐条记录处理方式，也可以直接在交付说明里写清保留原因后确认交付。</p>
                      <ul>
                        <li v-for="advisory in reportQuality.unresolved_advisories" :key="advisory.id">{{ issueSeverityLabel(advisory.severity) }} · {{ qualityIssueLabel(advisory.issue_type) }}：{{ consultantText(advisory.message) }}</li>
                      </ul>
                    </div>
                    <label class="final-gate-note">交付说明（可选）<textarea v-model.trim="finalGateNote" rows="2" maxlength="2000" :disabled="reportReviewBusy" placeholder="记录本次复核结论、保留的检查建议或需要后续跟进的事项。"></textarea></label>
                    <VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportStepSaving || reportReviewBusy || reportManuscriptPendingCount > 0 || reportManuscriptStaleCount > 0" :loading="reportStepSaving" @click="approveReportFinalGate">确认最终复核</VanButton>
                  </div>
                  <div v-if="selectedReportStepKey === 'S6' && reportCase.status === 'READY_TO_DELIVER' && canHandleReportStep(selectedReportStep)" class="final-gate-controls">
                    <strong>最终复核已通过</strong>
                    <VanButton class="primary-button compact-button deliver-button" type="primary" native-type="button" :disabled="reportCaseDelivering" :loading="reportCaseDelivering" @click="deliverReportCaseVersion">{{ reportCaseDelivering ? '交付中…' : '生成并交付版本' }}</VanButton>
                  </div>
                  <p v-else-if="reportCase.status === 'DELIVERED'" class="quality-clear-state">报告已交付，版本快照不可覆盖。</p>
                  <div class="signoff-links">
                    <VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="setReportWorkspaceSection('manuscript')">前往修改后稿件</VanButton>
                    <VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="setReportWorkspaceSection('quality')">前往 AI 检查与问题</VanButton>
                  </div>
                </section>

                <section id="report-section-quality" v-if="workspaceSection === 'quality'" class="report-data-panel quality-panel" aria-label="交付前检查">
                  <div class="panel-heading">
                    <div><p class="eyebrow">交付前检查</p><h3>最终复核</h3></div>
                    <span>{{ reportQualitySummaryLabel }}</span>
                  </div>
                  <div class="quality-status-row">
                    <strong>检查结果：{{ qualityStatusLabel(reportQuality.quality_status) }}</strong>
                    <span v-if="reportQuality.latest_validator_run">最近检查：{{ assetStatusLabel(reportQuality.latest_validator_run.status) }}{{ reportQualityProgress ? ` · ${reportQualityProgress.stage}` : '' }}{{ reportQualityProgress?.elapsedLabel ? `（${reportQualityProgress.elapsedLabel}）` : '' }}</span>
                    <VanButton v-if="canEditSelectedReportStep && selectedReportStepKey === 'S6'" class="primary-button compact-button" type="primary" native-type="button" :disabled="nodeToolPending || reportReviewBusy" :loading="reportQualitySaving" @click="runReportQuality">{{ reportQuality.latest_validator_run ? '重新检查完整报告' : '运行交付前检查' }}</VanButton>
                  </div>
                  <p v-if="reportQualityProgress" class="narrative-progress" :class="{ 'quality-run-stalled': reportQualityProgress.stalled }" role="status" aria-live="polite">{{ reportQualityProgress.hint }}</p>
                  <p v-if="reportQuality.latest_validator_run?.error === 'quality_run_stalled'" class="task-error">上次检查任务长时间没有返回结果，已按中断处理。请重新检查完整报告。</p>
                  <p v-else-if="reportQuality.latest_validator_run?.status === 'FAILED'" class="task-error">交付前检查暂时无法完成，请稍后重试。</p>
                  <p v-if="reportQuality.quality_status === 'PROGRAMMATIC_BLOCKED'" class="stale-note">{{ reportQuality.advisory_only ? '程序化检查提示了需要人工确认的内容；请核对正文与来源，确认无误后可以继续最终复核。' : '检查发现必须处理的问题；修订报告内容后重新检查。' }}</p>
                  <p v-if="reportQuality.latest_validator_run" class="ai-source-label">{{ reportQuality.advisory_only ? 'AI 检查结果和评分是复核线索，仅供参考；是否交付由咨询师确认。' : 'AI 检查结果是复核线索；评分、问题和最终交付仍受完整检查项及人工门禁约束。' }}</p>
                  <div v-if="canEditSelectedReportStep && selectedReportStepKey === 'S6' && reportQuality.latest_validator_run?.status === 'COMPLETED' && reportQuality.latest_validator_run?.current" class="ai-feedback-form">
                    <label>针对这次检查结果的反馈<textarea v-model="qualityFeedbackDraft" rows="3" maxlength="4000" placeholder="指出漏检、误报或需要重新核对的内容；系统会重新检查完整报告。"></textarea></label>
                    <small v-if="reportQuality.latest_validator_run.feedback_source_run_id">本次结果基于运行 #{{ reportQuality.latest_validator_run.feedback_source_run_id }} 的反馈生成。</small>
                    <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportQualitySaving || reportReviewBusy || !qualityFeedbackDraft.trim()" :loading="reportQualitySaving" @click="rerunReportQualityWithFeedback">按反馈重新检查完整报告</VanButton>
                  </div>
                  <QualityScorecard :scorecard="reportQuality.latest_validator_run?.scorecard" />
                  <QualityIssueReview v-model:selected-issue-key="nodeRecordKeys.quality" :quality="reportQuality" :content="reportCaseContent" :read-only="!canEditSelectedReportStep" :saving="reportQualitySaving" :fragment-saving="reportFragmentSaving" :issue-label="qualityIssueLabel" :issue-message="qualityIssueMessage" :issue-suggestion="qualityIssueSuggestion" :severity-label="issueSeverityLabel" :status-label="assetStatusLabel" @save-issue="saveReportQualityReview" @save-issue-group="saveReportQualityReviewGroup" @save-fragment="saveReportFragmentReview" @repair-source="repairReportFragmentSource" @busy="reportReviewBusy = $event" @rerun="runReportQuality" />
                  <div v-if="selectedReportStepKey === 'S6' && reportCase.review_policy_version !== 'six-node-review-v1'" class="quality-next-step">
                    <p>{{ reportQuality.advisory_only ? '需要修订的问题可以直接在下方处理；改动保存后，进入“修改后稿件”通读并确认最终稿。' : '处理完必须处理的问题并重新检查通过后，进入“修改后稿件”通读并确认最终稿。' }}</p>
                    <VanButton plain native-type="button" :disabled="reportReviewBusy" @click="setReportWorkspaceSection('manuscript')">前往修改后稿件</VanButton>
                  </div>
                </section>

                <section id="report-section-manuscript" v-if="workspaceSection === 'manuscript' && selectedReportStepKey === 'S6'" class="report-data-panel report-asset-panel" aria-label="修改后的报告稿件">
                  <div class="panel-heading">
                    <div><p class="eyebrow">修改后稿件</p><h3>通读修改后的完整报告</h3></div>
                    <span>{{ nodeFragments.length }} 段 · {{ reportManuscriptPendingCount ? `${reportManuscriptPendingCount} 段待确认` : reportManuscriptStaleCount ? `${reportManuscriptStaleCount} 段来源待复核` : '全部已确认' }}</span>
                  </div>
                  <p class="narrative-progress">这里按报告顺序展示当前稿件（含本次修订）；对具体问题可继续局部修订，确认无误后整体确认，最终交付会使用这份稿件。</p>
                  <p v-if="reportManuscriptStaleCount" class="stale-note" role="status">有 {{ reportManuscriptStaleCount }} 段正文的来源依据已更新，请先复核来源再确认。</p>
                  <ReportFragmentReview v-for="fragment in nodeFragments" :id="`report-fragment-${fragment.fragment_key}`" :key="fragment.fragment_key" :fragment="fragment" :content="reportCaseContent" :read-only="!canEditSelectedReportStep" :saving="reportFragmentSaving" batch-mode @save-review="saveReportFragmentReview" @repair-source="repairReportFragmentSource" @busy="reportReviewBusy = $event" />
                  <p v-if="!nodeFragments.length" class="empty-cell">当前没有可通读的报告正文。</p>
                  <div v-if="canEditSelectedReportStep && nodeFragments.length" class="manuscript-confirm" role="status">
                    <p>{{ reportManuscriptStaleCount ? `有 ${reportManuscriptStaleCount} 段正文的来源依据已更新，请先复核来源；确认后交付版本才会包含这些段落。` : reportManuscriptPendingCount ? `本次修订有 ${reportManuscriptPendingCount} 段尚未确认；确认后交付版本会使用修改后的正文。` : '修改后的稿件已全部确认，可以完成最终复核并交付。' }}</p>
                    <div class="manuscript-confirm-actions">
                      <VanButton v-if="reportManuscriptPendingCount" type="primary" native-type="button" :disabled="reportFragmentSaving || reportReviewBusy || reportManuscriptStaleCount > 0" :loading="reportFragmentSaving" @click="confirmReportManuscript">确认修改后稿件</VanButton>
                      <VanButton plain native-type="button" :disabled="reportReviewBusy" @click="setReportWorkspaceSection('signoff')">前往最终确认</VanButton>
                    </div>
                  </div>
                </section>

                <section v-if="workspaceSection === 'calculation' && selectedReportStepKey === 'S1'" class="report-data-panel" aria-label="程序计算与人工核对">
                  <FoundationCalculationPanel :evidence="reportFoundationEvidence" :read-only="!canEditSelectedReportStep" :saving="foundationSaving" :error-message="foundationError" @calculate="calculateReportFoundation" @save-correction="correctReportFoundation" />
                </section>

                <section v-if="workspaceSection === 'analysis'" class="report-data-panel" aria-label="本节点 AI 分析">
                  <AnalysisDraftsPanel
                    :key="selectedReportStepKey"
                    :case-id="reportCase.id"
                    :review-policy-version="reportCase.review_policy_version"
                    :runs="reportAnalysisRuns"
                    :content="reportCaseContent"
                    :step-key="selectedReportStepKey"
                    :current-step="canEditSelectedReportStep ? currentReportStep : null"
                    :read-only="!canEditSelectedReportStep"
                    :saving="Boolean(reportAnalysisFindingSavingKey || reportAnalysisFragmentSavingKey)"
                    :feedback-saving="reportAnalysisSaving"
                    :feedback-disabled="reportAnalysisPending"
                    :analysis-ready="selectedReportStepKey !== 'S1' || Boolean(reportFoundationEvidence)"
                    @apply-candidates="applyReportAnalysisCandidates"
                    @busy="reportReviewBusy = $event"
                    @go-overview="setReportWorkspaceSection('overview')"
                    @run-analysis="startReportAnalysisDraft"
                    @go-calculation="setReportWorkspaceSection('calculation')"
                    @go-birth-time="setReportWorkspaceSection('birth-time')"
                  />
                </section>
                <section id="report-section-findings" v-if="workspaceSection === 'findings'" class="report-data-panel report-asset-panel">
                  <div class="panel-heading"><div><p class="eyebrow">工作流第 {{ selectedReportStep.sequence_no }} 节点 · 人工审核</p><h3>{{ aggregateReviewPolicy ? '本步判断整体审阅' : '逐条审核判断' }}</h3><p>{{ aggregateReviewPolicy ? '完整判断和来源一并展示；普通条目统一确认，争议项可单独修改或拒绝。' : '选择一条判断查看完整内容和来源；确认或拒绝后继续处理下一条。' }}</p></div><span>{{ nodeFindings.length }} 条本节点判断</span></div>
                  <WorkbenchRecordPicker v-if="!aggregateReviewPolicy" v-model="nodeRecordKeys.findings" :items="nodeFindings" key-field="finding_key" title-field="claim" label="选择判断" />
                  <VanButton v-if="(aggregateReviewPolicy ? nodeFindings : visibleNodeFindings)[0]?.source_skill_run_id" class="secondary-button compact-button" plain native-type="button" @click="setReportWorkspaceSection('analysis')">返回 AI 分析，继续处理关联内容</VanButton>
                  <article v-for="finding in aggregateReviewPolicy ? nodeFindings : visibleNodeFindings" :id="`report-finding-${finding.finding_key}`" :key="finding.id" class="finding-item" tabindex="-1">
                    <template v-if="canEditSelectedReportStep && editingFindingKey === finding.finding_key && reportFindingDraft">
                      <div class="finding-editor">
                        <label>判断内容<textarea v-model.trim="reportFindingDraft.claim" rows="3" maxlength="5000"></textarea></label>
                      <div class="form-grid two"><label>判断类别<select v-model="reportFindingDraft.semantic_role"><option v-if="!semanticRoleOptions.some(role => role.value === reportFindingDraft.semantic_role)" :value="reportFindingDraft.semantic_role">其他类别</option><option v-for="role in semanticRoleOptions" :key="role.value" :value="role.value">{{ role.label }}</option></select></label><label>把握程度<select v-model="reportFindingDraft.confidence"><option value="LOW">较低</option><option value="MEDIUM">一般</option><option value="HIGH">较高</option></select></label></div>
                        <div class="form-grid two"><label>参考优先级<select v-model="reportFindingDraft.importance"><option value="LOW">普通</option><option value="MEDIUM">关注</option><option value="HIGH">重要</option><option value="CRITICAL">优先处理</option></select></label><label>报告中的呈现程度<select v-model="reportFindingDraft.reportability"><option value="INTERNAL_ONLY">仅供内部参考</option><option value="OPTIONAL">可酌情呈现</option><option value="RECOMMENDED">建议呈现</option><option value="MUST_INCLUDE">报告需要包含</option></select></label></div>
                        <EvidenceReferencePicker v-model="reportFindingDraft.evidence_refs" :items="reportEvidenceItems" :preferred-keys="reportPreferredEvidenceKeys" label="判断依据" />
                        <div class="asset-actions"><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="editingFindingKey = null">取消</VanButton><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportFindingSaving" :loading="reportFindingSaving" @click="saveReportFinding">保存新版本</VanButton></div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="asset-item-heading"><div><strong>{{ semanticRoleLabel(finding.semantic_role) }}</strong><span class="asset-status">{{ assetStatusLabel(finding.status) }}</span></div><small>{{ confidenceLabel(finding.confidence) }}把握 · {{ importanceLabel(finding.importance) }}</small></div>
                      <p>{{ finding.claim }}</p>
                      <small class="asset-source">参考依据：{{ evidenceTitles(finding.evidence_refs) || '暂未关联资料' }}</small>
                      <div v-if="canEditSelectedReportStep" class="asset-actions">
                        <VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="editReportFinding(finding)">修改</VanButton>
                        <VanButton v-if="!aggregateReviewPolicy && finding.status !== 'CONFIRMED'" class="primary-button compact-button" type="primary" native-type="button" :disabled="reportFindingSaving" @click="setReportFindingStatus(finding, 'CONFIRMED')">接受</VanButton>
                        <VanButton v-if="finding.status !== 'REJECTED'" class="text-button danger-text" type="danger" plain native-type="button" :disabled="reportFindingSaving" @click="setReportFindingStatus(finding, 'REJECTED')">拒绝</VanButton>
                      </div>
                    </template>
                  </article>
                  <p v-if="!nodeFindings.length" class="empty-cell">暂无专业判断，可以在当前步骤新增。</p>
                  <VanButton v-if="canEditSelectedReportStep" plain native-type="button" @click="showNodeAddForm = !showNodeAddForm">{{ showNodeAddForm ? '收起补充表单' : '人工补充本节点内容' }}</VanButton>
                  <form v-if="canEditSelectedReportStep && showNodeAddForm" class="new-asset-form" @submit.prevent="addReportFinding">
                    <h4>新增专业判断</h4>
                    <label>判断类别<select v-model="newReportFinding.semantic_role"><option v-for="role in semanticRoleOptions" :key="role.value" :value="role.value">{{ role.label }}</option></select></label>
                    <label>判断内容<textarea v-model.trim="newReportFinding.claim" rows="3" maxlength="5000"></textarea></label>
                    <EvidenceReferencePicker v-model="newReportFinding.evidence_refs" :items="reportEvidenceItems" :preferred-keys="reportPreferredEvidenceKeys" label="判断依据" />
                    <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="reportFindingSaving || !newReportFinding.claim.trim()" :loading="reportFindingSaving">新增为待审核</VanButton>
                  </form>
                </section>

                <section id="report-section-fragments" v-if="workspaceSection === 'fragments'" class="report-data-panel report-asset-panel">
                  <div class="panel-heading"><div><p class="eyebrow">报告内容</p><h3>{{ selectedReportStepKey === 'S5' ? (aggregateReviewPolicy ? '完整报告审阅' : '逐段审阅报告正文') : '本节点分析内容' }}</h3></div><span>{{ nodeFragments.length }} 项</span></div>
                  <template v-if="selectedReportStepKey === 'S5'">
                    <template v-if="aggregateReviewPolicy">
                      <p class="narrative-progress">通读完整正文及来源；只对具体问题局部修订，完成后一次整体确认。 · 共 {{ nodeFragments.length }} 段</p>
                      <ReportFragmentReview v-for="fragment in nodeFragments" :id="`report-fragment-${fragment.fragment_key}`" :key="fragment.fragment_key" :fragment="fragment" :content="reportCaseContent" :read-only="!canEditSelectedReportStep" :saving="reportFragmentSaving" batch-mode @save-review="saveReportFragmentReview" @repair-source="repairReportFragmentSource" @busy="reportReviewBusy = $event" />
                      <div v-if="nodeFragments.length && !nodeFragments.some(row => row.status === 'STALE')" class="narrative-progress" role="status">
                        <p>完整报告与来源已展示。完成通读后，在节点复核中一次确认本阶段。</p>
                        <VanButton plain native-type="button" :disabled="reportReviewBusy" @click="setReportWorkspaceSection('signoff')">前往节点复核</VanButton>
                      </div>
                    </template>
                    <template v-else>
                      <p class="narrative-progress">按编排顺序核对正文与依据，确认一段后继续下一待审段落。 · 已确认 {{ nodeFragments.filter(row => row.status === 'CONFIRMED').length }} / {{ nodeFragments.length }} 段</p>
                      <WorkbenchRecordPicker v-model="nodeRecordKeys.fragments" :items="nodeFragments" key-field="fragment_key" title-field="title" label="选择正文段落" :disabled="reportReviewBusy || reportFragmentSaving" />
                      <ReportFragmentReview v-for="fragment in visibleNodeFragments" :key="fragment.fragment_key" :fragment="fragment" :content="reportCaseContent" :read-only="!canEditSelectedReportStep" :saving="reportFragmentSaving" advance @save-review="saveReportFragmentReview" @continue-next="continueReportFragmentReview" @repair-source="repairReportFragmentSource" @busy="reportReviewBusy = $event" />
                      <div v-if="nodeFragments.length && nodeFragments.every(row => row.status === 'CONFIRMED')" class="narrative-progress" role="status">
                        <p>正文已逐段确认。修改后的完整报告须核对连贯性，再完成写作节点。</p>
                        <VanButton v-if="canEditSelectedReportStep" plain native-type="button" :disabled="reportReviewBusy || nodeToolPending" :loading="reportNarrativeSaving" @click="runReportCoherenceCheck">重新检查报告连贯性</VanButton>
                        <VanButton plain native-type="button" :disabled="reportReviewBusy" @click="setReportWorkspaceSection('overview')">回节点总览核对并完成</VanButton>
                      </div>
                    </template>
                  </template>
                  <template v-else>
                  <WorkbenchRecordPicker v-if="!aggregateReviewPolicy" v-model="nodeRecordKeys.fragments" :items="nodeFragments" key-field="fragment_key" title-field="title" label="选择内容" />
                  <article v-for="fragment in aggregateReviewPolicy ? nodeFragments : visibleNodeFragments" :id="`report-fragment-${fragment.fragment_key}`" :key="fragment.id" class="fragment-item" tabindex="-1">
                    <div class="asset-item-heading"><div><strong>{{ fragmentTitle(fragment.fragment_key, fragment) }}</strong><span class="asset-status">{{ assetStatusLabel(fragment.status) }}</span></div><small>{{ editKindLabel(fragment.edit_kind) }}</small></div>
                    <label>标题<input v-model.trim="reportFragmentDrafts[fragment.fragment_key].title" :disabled="!canEditSelectedReportStep || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"></label>
                    <label>正文<textarea v-model="reportFragmentDrafts[fragment.fragment_key].content" rows="5" :disabled="!canEditSelectedReportStep || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"></textarea></label>
                    <div class="form-grid two"><label>修改范围<select v-model="reportFragmentDrafts[fragment.fragment_key].edit_kind" :disabled="!canEditSelectedReportStep || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"><option value="STYLE">只调整表达方式</option><option value="SEMANTIC">调整内容含义</option></select></label><label v-if="!aggregateReviewPolicy">审核结果<select v-model="reportFragmentDrafts[fragment.fragment_key].status" :disabled="!canEditSelectedReportStep || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"><option value="PROPOSED">待确认</option><option value="CONFIRMED">已确认</option></select></label><span v-else class="asset-status">{{ assetStatusLabel(fragment.status) }}</span></div>
                    <p class="asset-source">关联依据：{{ findingTitles(reportFragmentDrafts[fragment.fragment_key].finding_refs) || '待补充' }}<template v-if="reportFragmentDrafts[fragment.fragment_key].evidence_refs"> · {{ evidenceTitles(reportFragmentDrafts[fragment.fragment_key].evidence_refs) }}</template></p>
                    <div v-if="fragment.stale_reason" class="stale-note">前序内容已有调整，这段报告需要重新审核后才能使用。</div>
                    <div v-if="canEditSelectedReportStep && !(fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')" class="asset-actions"><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportFragmentSaving" :loading="reportFragmentSaving" @click="saveReportFragment(fragment)">保存新版本</VanButton></div>
                  </article>
                  </template>
                  <p v-if="!nodeFragments.length" class="empty-cell">暂无本节点内容，请先运行对应技能。</p>
                  <VanButton v-if="canEditSelectedReportStep && ['S1', 'S2', 'S3', 'S4'].includes(selectedReportStepKey)" plain native-type="button" @click="showNodeAddForm = !showNodeAddForm">{{ showNodeAddForm ? '收起补充表单' : '人工补充本节点分析' }}</VanButton>
                  <form v-if="canEditSelectedReportStep && ['S1', 'S2', 'S3', 'S4'].includes(selectedReportStepKey) && showNodeAddForm" class="new-asset-form" @submit.prevent="addReportFragment">
                    <h4>新增分析内容</h4>
                    <label>标题<input v-model.trim="newReportFragment.title" maxlength="240"></label>
                    <label>正文<textarea v-model.trim="newReportFragment.content" rows="5" maxlength="30000"></textarea></label>
                    <fieldset class="reference-picker"><legend>关联本节点与前序已确认判断</legend><label v-for="finding in reportReferenceFindings" :key="finding.id"><input type="checkbox" :checked="hasReference(newReportFragment.finding_refs, finding.finding_key)" @change="toggleReference(newReportFragment, 'finding_refs', finding.finding_key, $event)"><span>{{ finding.claim }}</span></label><small v-if="!reportReferenceFindings.length">当前没有可关联的已确认判断。</small></fieldset>
                    <EvidenceReferencePicker v-model="newReportFragment.evidence_refs" :items="reportEvidenceItems" :preferred-keys="reportPreferredEvidenceKeys" label="直接资料依据" />
                    <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="reportFragmentSaving || !newReportFragment.content.trim()" :loading="reportFragmentSaving">新增待确认内容</VanButton>
                  </form>
                </section>
                </ReportNodeWorkbench>
              </template>
              <div v-else class="empty-cell">暂时无法打开这份报告，请返回列表刷新后重试。</div>
            </section>

            <div v-if="workspace.request.service_type === 'calendar'" class="workspace-actions">
              <VanButton v-if="workspace.request.status === 'submitted' && !workspace.request.assigned_consultant_id" class="primary-button" type="primary" native-type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接收中…' : '接受并处理' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'accepted' || workspace.request.status === 'failed'" class="primary-button" type="primary" native-type="button" :disabled="aiStarting" :aria-busy="aiStarting" @click="startAI">{{ aiStarting ? '启动中…' : workspace.request.status === 'failed' ? '重新生成内容建议' : '生成内容建议' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing'" class="secondary-button" type="default" plain native-type="button" :disabled="aiStarting" @click="regenerateAI">重新生成内容建议</VanButton>
              <VanButton v-if="workspace.draft && (workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing')" class="secondary-button" type="default" plain native-type="button" :disabled="saving" :aria-busy="saving" @click="saveDraft">{{ saving ? '保存中…' : '保存草稿' }}</VanButton>
              <VanButton v-if="workspace.draft && (workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing')" class="primary-button deliver-button" type="primary" native-type="button" :disabled="delivering" :aria-busy="delivering" @click="deliver">{{ delivering ? '交付中…' : '提交最终交付' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'accepted' || workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing' || workspace.request.status === 'failed'" class="text-button" type="default" plain native-type="button" @click="showInfoPanel = !showInfoPanel">待用户补充</VanButton>
              <VanButton v-if="admin && ['submitted', 'accepted', 'needs_info', 'failed'].includes(workspace.request.status)" class="text-button danger-text" type="danger" plain native-type="button" @click="rejectRequest">关闭申请</VanButton>
            </div>

            <div v-if="workspace.request.service_type === 'calendar' && showInfoPanel" class="info-panel">
              <label>请补充的资料或原因<textarea v-model.trim="infoReason" rows="3" maxlength="1000" placeholder="说明用户需要补充什么，以及为什么这会影响分析。"></textarea></label>
              <div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="showInfoPanel = false">取消</VanButton><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="infoSaving || !infoReason" :aria-busy="infoSaving" @click="requestInfo">{{ infoSaving ? '发送中…' : '标记待补充' }}</VanButton></div>
            </div>

            <div v-if="workspace.request.service_type === 'calendar'" class="workspace-grid">
              <section class="facts-panel">
                <div class="panel-heading"><div><p class="eyebrow">SOURCE / USER INPUT</p><h3>资料与需求</h3></div><span>申请快照</span></div>
                <dl class="detail-list source-list"><div><dt>姓名</dt><dd>{{ workspace.user.name || workspace.request.request_payload?.profile?.name || '—' }}</dd></div><div><dt>性别</dt><dd>{{ genderLabel(workspace.user.gender || workspace.request.request_payload?.profile?.gender) }}</dd></div><div><dt>出生资料</dt><dd>{{ birthSummary }}</dd></div><div><dt>出生地</dt><dd>{{ workspace.user.birth_place || workspace.request.request_payload?.profile?.birth_place || '—' }}</dd></div><div><dt>关注议题</dt><dd>{{ requestTopicLabel(workspace.request.request_payload) }}</dd></div><div><dt>本次困惑</dt><dd>{{ workspace.request.request_payload?.context?.current_challenge || workspace.request.request_payload?.calendar_goal || '—' }}</dd></div><div><dt>期望结果</dt><dd>{{ expectedOutcomeLabel(workspace.request.request_payload) }}</dd></div><div><dt>补充说明</dt><dd>{{ workspace.request.request_payload?.context?.additional_info || workspace.request.request_payload?.additional_info || '—' }}</dd></div></dl>
              </section>

              <section v-if="workspace.draft" class="ai-panel">
                <div class="panel-heading"><div><p class="eyebrow">内部参考</p><h3>生成内容参考</h3></div><span>第 {{ workspace.draft.ai_version }} 版</span></div>
                <p class="ai-privacy">仅咨询师和管理员可见。请以用户资料与专业判断为准，不要直接交付未审校内容。</p>
                <details class="ai-details"><summary>查看生成内容详情</summary><pre>{{ pretty(workspace.draft.ai_payload) }}</pre></details>
              </section>
              <section v-else class="ai-panel ai-empty"><div class="panel-heading"><div><p class="eyebrow">内部参考</p><h3>等待生成内容</h3></div></div><p>确认资料后，点击“生成内容建议”。</p></section>
            </div>

            <section v-if="workspace.draft && workspace.request.service_type === 'calendar'" class="editor-panel">
              <div class="panel-heading editor-heading"><div><p class="eyebrow">咨询师编辑</p><h3>内容编辑</h3></div><span>第 {{ workspace.draft.content_version }} 版</span></div>
              <div v-if="workspace.request.service_type === 'report'" class="report-editor">
                <label class="wide-field">报告标题<input v-model.trim="reportEditor.title" maxlength="100"></label>
                <fieldset class="editor-fieldset"><legend>个人属性 / 能量画像</legend><div class="form-grid two"><label>属性类型<input v-model.trim="reportEditor.energy.type"></label><label>核心特质<input v-model.trim="reportEditor.energy.core_traits"></label></div><label>画像说明<textarea v-model="reportEditor.energy.description" rows="5"></textarea></label></fieldset>
                <fieldset class="editor-fieldset"><legend>职业与方向</legend><label>适合路径 <small>每行一项</small><textarea v-model="reportEditor.career.suitable_paths" rows="4"></textarea></label><label>工作方式<textarea v-model="reportEditor.career.work_style" rows="3"></textarea></label><label>发展建议 <small>每行一项</small><textarea v-model="reportEditor.career.development_suggestions" rows="4"></textarea></label></fieldset>
                <fieldset class="editor-fieldset"><legend>关系模式</legend><label>关系风格<textarea v-model="reportEditor.relationship.style" rows="3"></textarea></label><div class="form-grid two"><label>关系优势 <small>每行一项</small><textarea v-model="reportEditor.relationship.strengths" rows="4"></textarea></label><label>关系挑战 <small>每行一项</small><textarea v-model="reportEditor.relationship.challenges" rows="4"></textarea></label></div><label>成长方向<textarea v-model="reportEditor.relationship.growth_direction" rows="3"></textarea></label></fieldset>
                <fieldset class="editor-fieldset"><legend>个人成长与行动方案</legend><label>当前议题 <small>每行一项</small><textarea v-model="reportEditor.growth.current_issues" rows="3"></textarea></label><label>行动方案 <small>每行一项</small><textarea v-model="reportEditor.growth.action_plan" rows="5"></textarea></label><label>成长资源 <small>每行一项</small><textarea v-model="reportEditor.growth.resources" rows="3"></textarea></label></fieldset>
                <label class="wide-field">总结与寄语<textarea v-model="reportEditor.summary" rows="6"></textarea></label>
              </div>

              <div v-else class="calendar-editor">
                <div class="form-grid two"><label>日历标题<input v-model.trim="calendarEditor.title" maxlength="150"></label><label>起始日期<input v-model="calendarEditor.start_date" type="date" readonly></label><label>结束日期<input v-model="calendarEditor.end_date" type="date" readonly></label><label>节奏说明<input v-model.trim="calendarEditor.meta_payload.rhythm"></label></div>
                <label class="wide-field">开篇说明<textarea v-model="calendarEditor.meta_payload.intro" rows="3"></textarea></label>
                <div class="entry-toolbar"><div><strong>每日条目</strong><small>固定 30 天 · 已填 {{ calendarEditor.entries.length }} 条 · 保存和交付时会再次校验</small></div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="addEntry">添加条目</VanButton></div>
                <div class="entry-list">
                  <article v-for="(entry, index) in calendarEditor.entries" :key="entry._key" class="entry-editor">
                    <div class="entry-head">
                      <strong>第 {{ index + 1 }} 天</strong>
                      <VanButton class="text-button danger-text" type="danger" plain native-type="button" @click="removeEntry(index)">移除</VanButton>
                    </div>
                    <div class="form-grid three">
                      <label>日期<input v-model="entry.entry_date" type="date"></label>
                      <label>色调<select v-model="entry.tone"><option value="green">推进</option><option value="green-yellow">先推后收</option><option value="yellow-green">先备后行</option><option value="yellow">观察</option><option value="red-yellow">缓冲</option><option value="red">收气</option><option value="rest">休整</option></select></label>
                      <label>状态标签<input v-model.trim="entry.status_label" placeholder="例如：准备期"></label>
                      <label>关键词<input v-model.trim="entry.keyword" placeholder="例如：观察"></label>
                      <label class="span-two">摘要<input v-model.trim="entry.summary" placeholder="给用户的一句话提示"></label>
                    </div>
                    <div class="form-grid two">
                      <label>适合事项 <small>用逗号或换行分隔</small><textarea v-model="entry.suitableText" rows="3"></textarea></label>
                      <label>不适合事项 <small>用逗号或换行分隔</small><textarea v-model="entry.unsuitableText" rows="3"></textarea></label>
                    </div>
                    <label>时间窗口<input v-model.trim="entry.time_window" placeholder="例如：上午适合整理，下午适合轻推"></label>
                    <label>咨询师备注 <small>仅工作台可见</small><textarea v-model="entry.admin_note" rows="2"></textarea></label>
                  </article>
                </div>
              </div>
            </section>
            <p v-if="workspace.request.service_type === 'calendar' && workspace.task && workspace.task.status === 'failed'" class="task-error" role="alert">内容生成暂时失败：{{ consultantText(workspace.task.error || workspace.request.last_error, '请稍后重试。') }}</p>
          </div>

          <div v-else class="empty-state"><IconMark class="empty-icon" name="compass" /><p>从左侧选择一份申请开始处理。</p><small>待接单申请只展示必要摘要；接单后才会打开完整资料。</small></div>
        </section>
      </section>
    </main>
    </OperationsShell>

    <VanDialog
      v-model:show="rejectDialog.visible"
      class="mobile-form-dialog"
      title="关闭申请"
      :close-on-click-overlay="false"
      :keyboard-enabled="!rejectSaving"
      :show-confirm-button="false"
    >
      <p class="mobile-form-dialog__copy">关闭后用户会在申请中心看到原因，当前处理结果不会继续流转。</p>
      <VanField
        v-model.trim="rejectDialog.reason"
        class="mobile-form-dialog__field mobile-form-dialog__field--textarea"
        label="关闭原因"
        type="textarea"
        rows="3"
        autosize
        maxlength="1000"
        :disabled="rejectSaving"
        :error-message="rejectDialog.error"
        @update:model-value="rejectDialog.error = ''"
      />
      <template #footer>
        <div class="mobile-form-dialog__footer">
          <VanButton block plain native-type="button" :disabled="rejectSaving" @click="rejectDialog.visible = false">取消</VanButton>
          <VanButton
            block
            type="danger"
            native-type="button"
            :disabled="rejectSaving || !rejectDialog.reason.trim()"
            :loading="rejectSaving"
            loading-text="关闭中…"
            @click="submitReject"
          >
            确认关闭
          </VanButton>
        </div>
      </template>
    </VanDialog>

    <VanDialog
      v-model:show="reportImportDialog.visible"
      class="mobile-form-dialog report-import-dialog"
      title="快速导入报告"
      :close-on-click-overlay="false"
      :keyboard-enabled="!reportImportDialog.saving"
      :show-confirm-button="false"
    >
      <p class="mobile-form-dialog__copy">支持常见报告格式，系统会自动整理为“你是谁 / 卡在哪 / 往哪去”三段。导入后前五个节点会标记为已完成，报告直接进入第 6 步。AI 检查可选、仅供参考、不设硬性门槛；咨询师核对报告后随时可以确认并交付。</p>
      <VanField
        v-model.trim="reportImportDialog.title"
        class="mobile-form-dialog__field"
        label="报告标题"
        maxlength="240"
        placeholder="可留空，默认取“你是谁”首句"
        :disabled="reportImportDialog.saving"
      />
      <VanField
        v-model.trim="reportImportDialog.sourceFilename"
        class="mobile-form-dialog__field"
        label="来源文件"
        maxlength="240"
        placeholder="可留空，便于日后追溯"
        :disabled="reportImportDialog.saving"
      />
      <div class="report-import-file">
        <label for="report-import-file-input">从本地选择 .md 或 .txt 文件</label>
        <input
          id="report-import-file-input"
          type="file"
          accept=".md,.markdown,.txt,text/plain,text/markdown"
          :disabled="reportImportDialog.saving"
          @change="handleReportImportFile"
        >
      </div>
      <VanField
        v-model="reportImportDialog.content"
        class="mobile-form-dialog__field mobile-form-dialog__field--textarea report-import-dialog__content"
        label="报告正文"
        type="textarea"
        rows="12"
        maxlength="100000"
        placeholder="粘贴完整报告内容，系统将自动整理为“你是谁 / 卡在哪 / 往哪去”。"
        :disabled="reportImportDialog.saving"
        :error-message="reportImportDialog.error"
        @update:model-value="reportImportDialog.error = ''"
      />
      <template #footer>
        <div class="mobile-form-dialog__footer">
          <VanButton block plain native-type="button" :disabled="reportImportDialog.saving" @click="reportImportDialog.visible = false">取消</VanButton>
          <VanButton
            block
            type="primary"
            native-type="button"
            :disabled="reportImportDialog.saving || !reportImportDialog.content.trim()"
            :loading="reportImportDialog.saving"
            loading-text="正在整理并导入…"
            @click="submitReportImport"
          >
            确认导入
          </VanButton>
        </div>
      </template>
    </VanDialog>
  </div>
</template>

<script src="./StaffConsole.js"></script>

<style scoped src="./StaffConsole.css"></style>
