<template>
  <div class="staff-shell">
    <BrandNav />
    <main class="staff-main">
      <header class="staff-heading">
        <div>
          <p class="section-kicker">SERVICE REQUESTS / REVIEW ROOM</p>
          <h1>咨询申请工作台</h1>
          <p>处理已分配的咨询师报告 Case 与日历申请。</p>
        </div>
        <div class="heading-actions">
          <router-link class="secondary-button compact-button" to="/skills">Skill Studio</router-link>
          <span class="live-state" role="status" aria-live="polite"><i :class="{ active: loading || pollingTask || reportCaseLoading }"></i>{{ pollingTask ? 'AI 初稿处理中' : reportCaseLoading ? '正在读取 Case' : loading ? '正在同步' : '已同步' }}</span>
          <VanButton class="secondary-button" type="default" plain native-type="button" :disabled="loading" @click="loadRequests">刷新申请</VanButton>
        </div>
      </header>

      <p v-if="message" class="console-message" role="status" aria-live="polite">{{ message }}</p>

      <section class="staff-toolbar paper-card" aria-label="申请筛选">
        <div class="scope-tabs" role="tablist" aria-label="申请范围">
          <button v-for="item in scopeOptions" :key="item.id" type="button" role="tab" :aria-selected="scope === item.id" :class="{ active: scope === item.id }" @click="changeScope(item.id)">{{ item.label }}</button>
        </div>
        <div class="staff-filters">
          <label><span>类型</span><select v-model="serviceType" @change="loadRequests"><option value="">全部</option><option value="report">报告</option><option value="calendar">日历</option></select></label>
          <label><span>状态</span><select v-model="statusFilter" @change="loadRequests"><option value="">全部状态</option><option v-for="status in statusOptions" :key="status" :value="status">{{ statusLabel(status) }}</option></select></label>
        </div>
      </section>

      <section class="staff-workspace-grid">
        <aside class="console-card paper-card request-list-panel">
          <div class="section-row"><div><p class="eyebrow">INBOX / {{ requests.total }}</p><h2>申请列表</h2><p>{{ scopeDescription }}</p></div></div>
          <div class="request-list" aria-label="服务申请列表">
            <button v-for="item in requests.items" :key="item.id" type="button" class="request-item" :class="{ selected: selectedRequest?.id === item.id }" :aria-pressed="selectedRequest?.id === item.id" @click="selectRequest(item)">
              <span class="request-item-icon" :class="`type-${item.service_type}`"><IconMark :name="item.service_type === 'report' ? 'reports' : 'calendar'" /></span>
              <span class="request-item-copy"><strong>{{ item.service_type === 'report' ? '人生说明书' : '决策日历' }}</strong><small>{{ item.user_name || `用户 #${item.user_id}` }} · #{{ item.id }}</small><em>{{ formatDate(item.created_at) }}</em></span>
              <span class="request-item-status">{{ statusLabel(item.status) }}</span>
            </button>
            <div v-if="!requests.items.length" class="empty-cell">当前筛选下没有申请。</div>
          </div>
        </aside>

        <section class="console-card paper-card workspace-panel" aria-live="polite">
          <div v-if="selectedRequest && !workspace" class="request-preview">
            <div class="workspace-header"><div><p class="eyebrow">REQUEST #{{ selectedRequest.id }}</p><h2>{{ selectedRequest.service_type === 'report' ? '人生说明书申请' : '决策日历申请' }}</h2></div><span :class="['status-badge', `staff-status-${selectedRequest.status}`]">{{ statusLabel(selectedRequest.status) }}</span></div>
            <div class="preview-note"><strong>{{ selectedRequest.user_name || `用户 #${selectedRequest.user_id}` }}</strong><p>这是待接单申请的摘要。接受申请后，才能查看完整出生资料并进入工作区。</p></div>
            <dl class="detail-list"><div><dt>关注目标</dt><dd>{{ requestGoal(selectedRequest) }}</dd></div><div><dt>补充说明</dt><dd>{{ selectedRequest.request_preview?.additional_info || '—' }}</dd></div><div v-if="selectedRequest.service_type === 'calendar'"><dt>起始日期</dt><dd>{{ selectedRequest.request_preview?.start_date || '—' }}</dd></div></dl>
            <VanButton v-if="selectedRequest.status === 'submitted' && !selectedRequest.assigned_consultant_id" class="primary-button" type="primary" native-type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接单中…' : '接受申请' }}</VanButton>
            <p v-else class="preview-lock">这份申请已经被其他咨询师接收，列表刷新后会更新状态。</p>
          </div>

          <div v-else-if="workspace" class="workspace-content">
            <header class="workspace-header">
              <div><p class="eyebrow">{{ workspace.request.service_type === 'report' ? 'REPORT REVIEW' : 'CALENDAR REVIEW' }} / #{{ workspace.request.id }}</p><h2>{{ workspace.request.service_type === 'report' ? '人生说明书审校' : '决策日历审校' }}</h2><p class="workspace-user">{{ workspace.user.name }} · {{ workspace.user.phone || '未填写联系方式' }}</p></div>
              <span :class="['status-badge', `staff-status-${workspace.request.status}`]">{{ statusLabel(workspace.request.status) }}</span>
            </header>

            <div v-if="admin" class="assignment-row">
              <label>处理咨询师<select v-model="assignmentId" :disabled="assignmentSaving" @change="assignConsultant"><option :value="null">未分配</option><option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select></label>
              <small>管理员可改派；改派不会覆盖已有版本。</small>
            </div>

            <section v-if="workspace.request.service_type === 'report'" class="report-case-workspace" aria-label="报告 Case 工作区">
              <div v-if="reportCaseLoading" class="empty-cell" role="status">正在读取 Case 内容…</div>
              <template v-else-if="reportCase">
                <div class="report-case-heading">
                  <div><p class="eyebrow">REPORT CASE / #{{ reportCase.id }}</p><h3>咨询师审核</h3><p>工作流版本 v{{ reportCase.workflow_instance?.workflow_version_id }} · {{ reportCase.status }}</p></div>
                  <div v-if="currentReportStep" class="report-step-controls">
                    <span class="step-current">当前步骤 {{ currentReportStep.step_key }} · {{ currentReportStep.status }}</span>
                    <VanButton v-if="currentReportStep.status === 'READY'" class="primary-button compact-button" type="primary" native-type="button" :disabled="reportStepSaving" :loading="reportStepSaving" @click="startReportStep">开始审核</VanButton>
                    <template v-else-if="currentReportStep.status === 'IN_REVIEW'">
                      <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportStepSaving" @click="reportStepReturn.visible = !reportStepReturn.visible">退回上一步</VanButton>
                      <VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportStepSaving" :loading="reportStepSaving" @click="completeReportStep">完成步骤</VanButton>
                    </template>
                  </div>
                  <p v-else class="case-complete-state">工作流步骤已完成，等待后续质量审核与交付阶段。</p>
                </div>

                <div v-if="reportStepReturn.visible" class="report-return-form">
                  <label>退回步骤<select v-model="reportStepReturn.targetStepKey"><option value="">选择已完成的上游步骤</option><option v-for="step in reportReturnTargets" :key="step.step_key" :value="step.step_key">{{ step.step_key }} · 第 {{ step.sequence_no }} 步</option></select></label>
                  <label>退回原因<textarea v-model.trim="reportStepReturn.reason" rows="2" maxlength="1000"></textarea></label>
                  <VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportStepSaving || !reportStepReturn.targetStepKey || !reportStepReturn.reason" :loading="reportStepSaving" @click="submitReportStepReturn">确认退回</VanButton>
                </div>

                <ol class="report-step-list" aria-label="报告工作流步骤">
                  <li v-for="step in reportCase.workflow_instance?.steps || []" :key="step.id" :class="`step-${step.status.toLowerCase()}`">
                    <span><strong>{{ step.step_key }}</strong><small>第 {{ step.sequence_no }} 步 · {{ step.required_capability || '无额外能力要求' }}</small></span>
                    <span class="step-state">{{ step.status }}</span>
                    <VanButton v-if="step.status === 'COMPLETED'" class="text-button" type="default" plain native-type="button" :disabled="reportStepSaving" @click="reopenReportStep(step)">重开</VanButton>
                  </li>
                </ol>

                <section class="report-data-panel narrative-panel" aria-label="报告叙事方案与写作">
                  <div class="panel-heading">
                    <div><p class="eyebrow">NARRATIVE / AUTHORING</p><h3>叙事方案与报告写作</h3></div>
                    <span v-if="reportNarrative.current_plan">Plan v{{ reportNarrative.current_plan.version_no }} · {{ reportNarrative.current_plan.status }}</span>
                    <span v-else>尚未确认 NarrativePlan</span>
                  </div>
                  <div v-if="reportNarrative.current_plan" class="narrative-current-plan">
                    <strong>{{ reportNarrative.current_plan.plan_json.core_theme }}</strong>
                    <small>候选 {{ reportNarrative.current_plan.selected_candidate_key }} · 必须纳入 {{ reportNarrative.current_plan.plan_json.must_include_findings.join('、') || '无' }}</small>
                    <details class="snapshot-details"><summary>查看计划与语义来源</summary><pre>{{ pretty({ plan: reportNarrative.current_plan.plan_json, source_snapshot: reportNarrative.current_plan.source_snapshot }) }}</pre></details>
                    <p v-if="reportNarrative.current_plan.status === 'STALE'" class="stale-note">语义来源已变化，需要重新生成候选并确认新计划。</p>
                  </div>
                  <div class="narrative-actions">
                    <VanButton v-if="currentReportStep?.step_key === 'S5' && currentReportStep.status === 'IN_REVIEW'" class="primary-button compact-button" type="primary" native-type="button" :disabled="reportNarrativeSaving" :loading="reportNarrativeSaving" @click="generateNarrativeCandidates">生成 2–3 个叙事候选</VanButton>
                  </div>
                  <div v-for="run in reportNarrative.candidate_runs" :key="run.id" class="narrative-run">
                    <div class="asset-item-heading"><div><strong>叙事候选运行 #{{ run.id }}</strong><span class="asset-status">{{ run.status }}</span></div><small>{{ run.model_trace?.model || '' }}</small></div>
                    <p v-if="run.status === 'FAILED'" class="task-error">候选生成失败：{{ run.error || '请重试' }}</p>
                    <article v-for="candidate in run.output_parsed?.candidates || []" :key="candidate.candidate_key" class="narrative-candidate">
                      <div class="asset-item-heading"><div><strong>{{ candidate.theme }}</strong><span class="asset-status">{{ candidate.candidate_key }}</span></div></div>
                      <p>{{ candidate.rationale }}</p>
                      <small class="asset-source">支持：{{ candidate.supporting_findings.join('、') || '无' }} · 弱化：{{ candidate.deemphasized_findings.join('、') || '无' }}</small>
                      <div v-if="currentReportStep?.step_key === 'S5' && currentReportStep.status === 'IN_REVIEW'" class="narrative-choice-form">
                        <label>核心主题<input v-model.trim="narrativeCandidateDrafts[narrativeDraftKey(run, candidate)].core_theme" maxlength="1000"></label>
                        <fieldset><legend>必须纳入的判断</legend><label v-for="findingKey in candidate.supporting_findings" :key="findingKey" class="narrative-checkbox"><input v-model="narrativeCandidateDrafts[narrativeDraftKey(run, candidate)].must_include_findings" type="checkbox" :value="findingKey">{{ findingKey }}</label></fieldset>
                        <label>自我方向<select v-model="narrativeCandidateDrafts[narrativeDraftKey(run, candidate)].self_direction"><option value="">暂不指定</option><option v-for="findingKey in candidate.supporting_findings" :key="findingKey" :value="findingKey">{{ findingKey }}</option></select></label>
                        <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="reportNarrativeSaving || run.status !== 'COMPLETED'" :loading="reportNarrativeSaving" @click="confirmNarrativeCandidate(run, candidate)">选择并确认方案</VanButton>
                      </div>
                    </article>
                  </div>
                  <form v-if="currentReportStep?.step_key === 'S5' && currentReportStep.status === 'IN_REVIEW' && reportNarrative.current_plan?.status === 'CONFIRMED'" class="narrative-writing-form" @submit.prevent="generateReportFragment">
                    <div><strong>按片段写作</strong><small>每次生成一个可追溯来源的报告小节，结果进入待审核状态。</small></div>
                    <div class="form-grid two"><label>稳定标识<input v-model.trim="newReportWritingFragment.fragment_key" maxlength="200" placeholder="例如 report.identity.world_view"></label><label>标题<input v-model.trim="newReportWritingFragment.title" maxlength="240" placeholder="例如：世界看到的你"></label></div>
                    <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="reportNarrativeSaving || !newReportWritingFragment.fragment_key.trim()" :loading="reportNarrativeSaving">生成报告片段</VanButton>
                  </form>
                  <div v-for="run in reportNarrative.fragment_runs" :key="run.id" class="narrative-run">
                    <div class="asset-item-heading"><div><strong>{{ run.target_key || '报告片段' }} · 运行 #{{ run.id }}</strong><span class="asset-status">{{ run.status }}</span></div><small>{{ run.model_trace?.model || '' }}</small></div>
                    <p v-if="run.status === 'FAILED'" class="task-error">片段写作失败：{{ run.error || '请重试' }}</p>
                    <p v-else-if="run.output_parsed?.status === 'MISSING_SEMANTIC_SUPPORT'" class="stale-note">缺少语义支撑，AI 未补写结论。请回到 Finding / Analysis Fragment 审核。</p>
                  </div>
                </section>

                <div class="report-case-grid">
                  <section class="report-data-panel">
                    <div class="panel-heading"><div><p class="eyebrow">APPLICATION SNAPSHOT</p><h3>本次情境</h3></div><span>档案 v{{ reportCase.application_snapshot?.profile_version || '—' }}</span></div>
                    <dl class="context-values"><div v-for="(value, key) in reportCase.application_snapshot?.context || {}" :key="key"><dt>{{ key }}</dt><dd>{{ Array.isArray(value) ? value.join('、') || '—' : value || '—' }}</dd></div></dl>
                    <details class="snapshot-details"><summary>查看完整资料快照</summary><pre>{{ pretty(reportCase.application_snapshot) }}</pre></details>
                  </section>
                  <section class="report-data-panel">
                    <div class="panel-heading"><div><p class="eyebrow">EVIDENCE</p><h3>Evidence 来源</h3></div><span>{{ reportCaseContent.evidence.length }} 条</span></div>
                    <div v-if="!reportCaseContent.evidence.length" class="empty-cell">当前没有 Evidence。</div>
                    <article v-for="evidence in reportCaseContent.evidence" :key="evidence.id" class="case-evidence-item">
                      <div><strong>{{ evidence.evidence_key }}</strong><span>{{ evidence.source_type }} · {{ evidence.status }}</span></div>
                      <small>{{ evidence.source_ref }}</small><pre>{{ pretty(evidence.value_json) }}</pre>
                    </article>
                  </section>
                </div>

                <section class="report-data-panel report-asset-panel">
                  <div class="panel-heading"><div><p class="eyebrow">FINDINGS</p><h3>专业判断审核</h3></div><span>{{ reportCaseContent.findings.length }} 条 · 只有确认项会进入已确认语义</span></div>
                  <article v-for="finding in reportCaseContent.findings" :key="finding.id" class="finding-item">
                    <template v-if="editingFindingKey === finding.finding_key && reportFindingDraft">
                      <div class="finding-editor">
                        <label>判断内容<textarea v-model.trim="reportFindingDraft.claim" rows="3" maxlength="5000"></textarea></label>
                        <div class="form-grid two"><label>语义角色<input v-model.trim="reportFindingDraft.semantic_role" maxlength="48"></label><label>置信度<select v-model="reportFindingDraft.confidence"><option>LOW</option><option>MEDIUM</option><option>HIGH</option></select></label></div>
                        <div class="form-grid two"><label>重要度<select v-model="reportFindingDraft.importance"><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label><label>可报告性<select v-model="reportFindingDraft.reportability"><option>INTERNAL_ONLY</option><option>OPTIONAL</option><option>RECOMMENDED</option><option>MUST_INCLUDE</option></select></label></div>
                        <label>Evidence 引用 <small>每行一个 evidence key</small><textarea v-model="reportFindingDraft.evidence_refs" rows="2"></textarea></label>
                        <label>审核状态<select v-model="reportFindingDraft.status"><option value="PROPOSED">待审核</option><option value="CONFIRMED">已接受</option><option value="REJECTED">已拒绝</option></select></label>
                        <div class="asset-actions"><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="editingFindingKey = null">取消</VanButton><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportFindingSaving" :loading="reportFindingSaving" @click="saveReportFinding">保存新版本</VanButton></div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="asset-item-heading"><div><strong>{{ finding.finding_key }}</strong><span class="asset-status">{{ finding.status }} · {{ finding.semantic_role }} · v{{ finding.revision_no }}</span></div><small>{{ finding.confidence }} / {{ finding.importance }} / {{ finding.reportability }}</small></div>
                      <p>{{ finding.claim }}</p>
                      <small class="asset-source">Evidence：{{ finding.evidence_refs.join('、') || '无' }}</small>
                      <div v-if="currentReportStep?.status === 'IN_REVIEW'" class="asset-actions">
                        <VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="editReportFinding(finding)">修改</VanButton>
                        <VanButton v-if="finding.status !== 'CONFIRMED'" class="primary-button compact-button" type="primary" native-type="button" :disabled="reportFindingSaving" @click="setReportFindingStatus(finding, 'CONFIRMED')">接受</VanButton>
                        <VanButton v-if="finding.status !== 'REJECTED'" class="text-button danger-text" type="danger" plain native-type="button" :disabled="reportFindingSaving" @click="setReportFindingStatus(finding, 'REJECTED')">拒绝</VanButton>
                      </div>
                    </template>
                  </article>
                  <p v-if="!reportCaseContent.findings.length" class="empty-cell">暂无 Finding，可在当前审核步骤新增。</p>
                  <form v-if="currentReportStep?.status === 'IN_REVIEW'" class="new-asset-form" @submit.prevent="addReportFinding">
                    <h4>新增 Finding</h4>
                    <div class="form-grid two"><label>稳定标识<input v-model.trim="newReportFinding.finding_key" maxlength="200" placeholder="例如 psychology.core_pattern"></label><label>语义角色<input v-model.trim="newReportFinding.semantic_role" maxlength="48" placeholder="例如 CONFLICT"></label></div>
                    <label>判断内容<textarea v-model.trim="newReportFinding.claim" rows="3" maxlength="5000"></textarea></label>
                    <label>Evidence 引用 <small>每行一个 evidence key</small><textarea v-model="newReportFinding.evidence_refs" rows="2"></textarea></label>
                    <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="reportFindingSaving || !newReportFinding.finding_key.trim() || !newReportFinding.claim.trim()" :loading="reportFindingSaving">新增为待审核</VanButton>
                  </form>
                </section>

                <section class="report-data-panel report-asset-panel">
                  <div class="panel-heading"><div><p class="eyebrow">FRAGMENTS</p><h3>内容片段</h3></div><span>{{ reportCaseContent.fragments.length }} 条</span></div>
                  <article v-for="fragment in reportCaseContent.fragments" :key="fragment.id" class="fragment-item">
                    <div class="asset-item-heading"><div><strong>{{ fragment.fragment_key }}</strong><span class="asset-status">{{ fragment.status }} · v{{ fragment.revision_no }}</span></div><small>{{ fragment.edit_kind }} 修改</small></div>
                    <label>标题<input v-model.trim="reportFragmentDrafts[fragment.fragment_key].title" :disabled="currentReportStep?.status !== 'IN_REVIEW' || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"></label>
                    <label>正文<textarea v-model="reportFragmentDrafts[fragment.fragment_key].content" rows="5" :disabled="currentReportStep?.status !== 'IN_REVIEW' || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"></textarea></label>
                    <div class="form-grid two"><label>修改类型<select v-model="reportFragmentDrafts[fragment.fragment_key].edit_kind" :disabled="currentReportStep?.status !== 'IN_REVIEW' || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"><option value="STYLE">纯文风修改</option><option value="SEMANTIC">语义修改</option></select></label><label>状态<select v-model="reportFragmentDrafts[fragment.fragment_key].status" :disabled="currentReportStep?.status !== 'IN_REVIEW' || (fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')"><option value="PROPOSED">待确认</option><option value="CONFIRMED">已确认</option></select></label></div>
                    <details class="snapshot-details"><summary>查看来源映射</summary><pre>{{ pretty(fragment.source_snapshot) }}</pre></details>
                    <div v-if="fragment.stale_reason" class="stale-note"><template v-if="fragment.fragment_type === 'REPORT'">报告来源已变化，需要确认新计划后重新生成。</template><template v-else>STALE：{{ fragment.stale_reason }}</template></div>
                    <div v-if="currentReportStep?.status === 'IN_REVIEW' && !(fragment.fragment_type === 'REPORT' && fragment.status === 'STALE')" class="asset-actions"><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="reportFragmentSaving" :loading="reportFragmentSaving" @click="saveReportFragment(fragment)">保存新版本</VanButton></div>
                  </article>
                  <p v-if="!reportCaseContent.fragments.length" class="empty-cell">暂无内容片段，可在当前步骤新增。</p>
                  <form v-if="currentReportStep?.status === 'IN_REVIEW'" class="new-asset-form" @submit.prevent="addReportFragment">
                    <h4>新增内容片段</h4>
                    <div class="form-grid two"><label>稳定标识<input v-model.trim="newReportFragment.fragment_key" maxlength="200" placeholder="例如 analysis.core"></label><label>标题<input v-model.trim="newReportFragment.title" maxlength="240"></label></div>
                    <label>正文<textarea v-model.trim="newReportFragment.content" rows="5" maxlength="30000"></textarea></label>
                    <label>Finding 来源 <small>每行一个 finding key</small><textarea v-model="newReportFragment.finding_refs" rows="2"></textarea></label>
                    <label>Evidence 来源 <small>每行一个 evidence key</small><textarea v-model="newReportFragment.evidence_refs" rows="2"></textarea></label>
                    <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="reportFragmentSaving || !newReportFragment.fragment_key.trim() || !newReportFragment.content.trim()" :loading="reportFragmentSaving">新增待确认片段</VanButton>
                  </form>
                </section>
              </template>
              <div v-else class="empty-cell">未找到关联的 ReportCase。请刷新申请列表并检查服务端关联状态。</div>
            </section>

            <div v-if="workspace.request.service_type === 'calendar'" class="workspace-actions">
              <VanButton v-if="workspace.request.status === 'submitted' && !workspace.request.assigned_consultant_id" class="primary-button" type="primary" native-type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接收中…' : '接受并处理' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'accepted' || workspace.request.status === 'failed'" class="primary-button" type="primary" native-type="button" :disabled="aiStarting" :aria-busy="aiStarting" @click="startAI">{{ aiStarting ? '启动中…' : workspace.request.status === 'failed' ? '重试 AI 初稿' : '生成 AI 初稿' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing'" class="secondary-button" type="default" plain native-type="button" :disabled="aiStarting" @click="regenerateAI">重新生成 AI 初稿</VanButton>
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
                <dl class="detail-list source-list"><div><dt>姓名</dt><dd>{{ workspace.user.name || workspace.request.request_payload?.profile?.name || '—' }}</dd></div><div><dt>性别</dt><dd>{{ genderLabel(workspace.user.gender || workspace.request.request_payload?.profile?.gender) }}</dd></div><div><dt>出生资料</dt><dd>{{ birthSummary }}</dd></div><div><dt>出生地</dt><dd>{{ workspace.user.birth_place || workspace.request.request_payload?.profile?.birth_place || '—' }}</dd></div><div><dt>关注议题</dt><dd>{{ workspace.request.service_type === 'report' ? topicLabel(workspace.request.request_payload?.selected_topics) : workspace.request.request_payload?.calendar_goal || '—' }}</dd></div><div><dt>补充说明</dt><dd>{{ workspace.request.request_payload?.additional_info || '—' }}</dd></div></dl>
              </section>

              <section v-if="workspace.draft" class="ai-panel">
                <div class="panel-heading"><div><p class="eyebrow">AI SOURCE / PRIVATE</p><h3>AI 初稿参考</h3></div><span>v{{ workspace.draft.ai_version }}</span></div>
                <p class="ai-privacy">仅咨询师和管理员可见。请以用户资料与专业判断为准，不要直接交付未审校内容。</p>
                <details class="ai-details"><summary>查看 AI 初稿字段</summary><pre>{{ pretty(workspace.draft.ai_payload) }}</pre></details>
              </section>
              <section v-else class="ai-panel ai-empty"><div class="panel-heading"><div><p class="eyebrow">AI SOURCE / PRIVATE</p><h3>等待生成初稿</h3></div></div><p>确认资料后，点击“生成 AI 初稿”。</p></section>
            </div>

            <section v-if="workspace.draft && workspace.request.service_type === 'calendar'" class="editor-panel">
              <div class="panel-heading editor-heading"><div><p class="eyebrow">CONSULTANT EDITOR</p><h3>结构化编辑</h3></div><span>当前版本 v{{ workspace.draft.content_version }}</span></div>
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
                      <strong>DAY {{ String(index + 1).padStart(2, '0') }}</strong>
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
            <p v-if="workspace.request.service_type === 'calendar' && workspace.task && workspace.task.status === 'failed'" class="task-error" role="alert">AI 初稿生成失败：{{ workspace.task.error || workspace.request.last_error || '请重试' }}</p>
          </div>

          <div v-else class="empty-state"><IconMark class="empty-icon" name="compass" /><p>从左侧选择一份申请开始处理。</p><small>待接单申请只展示必要摘要；接单后才会打开完整资料。</small></div>
        </section>
      </section>
    </main>

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
  </div>
</template>

<script src="./StaffConsole.js"></script>

<style scoped src="./StaffConsole.css"></style>
