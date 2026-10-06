<template>
  <div class="staff-shell">
    <BrandNav />
    <main class="staff-main">
      <BrandPageHeader class="staff-heading" contained compact eyebrow="REVIEW ROOM" title="咨询申请工作台" description="从认真理解一份资料开始，让每一次交付都有依据。接收申请、审校初稿，再把清晰的结果交给用户。" seal="照见">
        <template #actions>
          <span class="live-state" role="status" aria-live="polite"><i :class="{ active: loading || pollingTask }"></i>{{ pollingTask ? 'AI 初稿处理中' : loading ? '正在同步' : '已同步' }}</span>
          <VanButton class="secondary-button" type="default" plain native-type="button" :disabled="loading" @click="loadRequests">刷新申请</VanButton>
        </template>
      </BrandPageHeader>

      <p v-if="message" class="console-message" role="status" aria-live="polite">{{ message }}</p>

      <section class="staff-toolbar paper-card" aria-label="申请筛选">
        <div class="scope-tabs" role="tablist" aria-label="申请范围">
          <button v-for="item in scopeOptions" :key="item.id" type="button" role="tab" :aria-selected="scope === item.id" :class="{ active: scope === item.id }" @click="changeScope(item.id)">{{ item.label }}</button>
        </div>
        <div class="staff-filters">
          <label><span>类型</span><select v-model="serviceType" @change="loadRequests"><option value="">全部报告申请</option><option value="report">报告</option></select></label>
          <label><span>状态</span><select v-model="statusFilter" @change="loadRequests"><option value="">全部状态</option><option v-for="status in statusOptions" :key="status" :value="status">{{ statusLabel(status) }}</option></select></label>
        </div>
      </section>

      <section class="staff-workspace-grid">
        <aside class="console-card paper-card request-list-panel">
          <div class="section-row"><div><p class="eyebrow">INBOX / {{ requests.total }}</p><h2>申请列表</h2><p>{{ scopeDescription }}</p></div></div>
          <div class="request-list" aria-label="服务申请列表">
            <button v-for="item in requests.items" :key="item.id" type="button" class="request-item" :class="{ selected: selectedRequest?.id === item.id }" :aria-pressed="selectedRequest?.id === item.id" @click="selectRequest(item)">
              <span class="request-item-icon" :class="`type-${item.service_type}`"><IconMark :name="item.service_type === 'report' ? 'reports' : 'calendar'" /></span>
              <span class="request-item-copy"><strong>{{ item.service_type === 'report' ? '人生说明书' : '决策日历' }}</strong><small>{{ item.user_name || `用户 #${item.user_id}` }} · #{{ item.id }}</small><em>{{ item.service_type === 'report' ? `${consultationTypeLabel(item.consultation_type)} · ` : '' }}{{ formatDate(item.created_at) }}</em></span>
              <span class="request-item-status">{{ statusLabel(item.status) }}</span>
            </button>
            <div v-if="!requests.items.length" class="empty-cell">当前筛选下没有申请。</div>
          </div>
        </aside>

        <section class="console-card paper-card workspace-panel" aria-live="polite">
          <div v-if="selectedRequest && !workspace" class="request-preview">
            <div class="workspace-header"><div><p class="eyebrow">REQUEST #{{ selectedRequest.id }}</p><h2>{{ selectedRequest.service_type === 'report' ? '人生说明书申请' : '决策日历申请' }}</h2></div><span :class="['status-badge', `staff-status-${selectedRequest.status}`]">{{ statusLabel(selectedRequest.status) }}</span></div>
            <div class="preview-note"><strong>{{ selectedRequest.user_name || `用户 #${selectedRequest.user_id}` }}</strong><p>这是待接单申请的摘要。接受申请后，才能查看完整出生资料并进入工作区。</p></div>
            <dl class="detail-list"><div><dt>关注议题</dt><dd>{{ requestGoal(selectedRequest) }}</dd></div><div><dt>本次困惑</dt><dd>{{ selectedRequest.request_preview?.current_challenge || '—' }}</dd></div><div><dt>补充说明</dt><dd>{{ selectedRequest.request_preview?.additional_info || '—' }}</dd></div></dl>
            <VanButton v-if="selectedRequest.status === 'submitted' && !selectedRequest.assigned_consultant_id" class="primary-button" type="primary" native-type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接单中…' : '接受申请' }}</VanButton>
            <p v-else class="preview-lock">这份申请已经被其他咨询师接收，列表刷新后会更新状态。</p>
          </div>

          <div v-else-if="workspace" class="workspace-content">
            <header class="workspace-header">
              <div><p class="eyebrow">{{ workspace.request.service_type === 'report' ? 'REPORT REVIEW' : 'CALENDAR REVIEW' }} / #{{ workspace.request.id }}</p><h2>{{ workspace.request.service_type === 'report' ? '人生说明书审校' : '决策日历审校' }}</h2><p class="workspace-user">{{ workspace.user.name }} · {{ workspace.user.phone || '未填写联系方式' }}</p><p v-if="workspace.request.service_type === 'report'" class="workspace-user">咨询方向：{{ consultationTypeLabel(workspace.request.consultation_type) }}</p></div>
              <span :class="['status-badge', `staff-status-${workspace.request.status}`]">{{ statusLabel(workspace.request.status) }}</span>
            </header>

            <div v-if="admin" class="assignment-row">
              <label v-if="workspace.request.service_type === 'report'">咨询方向<select v-model="consultationType" :disabled="assignmentSaving" @change="changeConsultationType"><option value="metaphysics">命理</option><option value="psychology">心理</option><option value="integrated">综合（命理 + 心理）</option></select></label>
              <label>处理咨询师<select v-model="assignmentId" :disabled="assignmentSaving"><option :value="null">未分配</option><option v-for="consultant in assignableConsultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select></label>
              <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!assignmentChanged || assignmentSaving" :loading="assignmentSaving" loading-text="保存中…" @click="assignConsultant">保存分配</VanButton>
              <small>仅列出具备所选方向能力的咨询师；修改不会覆盖已有版本。</small>
            </div>

            <div class="workspace-actions">
              <VanButton v-if="workspace.request.status === 'submitted' && !workspace.request.assigned_consultant_id" class="primary-button" type="primary" native-type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接收中…' : '接受并处理' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'accepted' || workspace.request.status === 'failed'" class="primary-button" type="primary" native-type="button" :disabled="aiStarting" :aria-busy="aiStarting" @click="startAI">{{ aiStarting ? '启动中…' : workspace.request.status === 'failed' ? '重试 AI 初稿' : '生成 AI 初稿' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing'" class="secondary-button" type="default" plain native-type="button" :disabled="aiStarting" @click="regenerateAI">重新生成 AI 初稿</VanButton>
              <VanButton v-if="workspace.draft && (workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing')" class="secondary-button" type="default" plain native-type="button" :disabled="saving" :aria-busy="saving" @click="saveDraft">{{ saving ? '保存中…' : '保存草稿' }}</VanButton>
              <VanButton v-if="workspace.draft && (workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing')" class="primary-button deliver-button" type="primary" native-type="button" :disabled="delivering" :aria-busy="delivering" @click="deliver">{{ delivering ? '交付中…' : '提交最终交付' }}</VanButton>
              <VanButton v-if="workspace.request.status === 'accepted' || workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing' || workspace.request.status === 'failed'" class="text-button" type="default" plain native-type="button" @click="showInfoPanel = !showInfoPanel">待用户补充</VanButton>
              <VanButton v-if="admin && ['submitted', 'accepted', 'needs_info', 'failed'].includes(workspace.request.status)" class="text-button danger-text" type="danger" plain native-type="button" @click="rejectRequest">关闭申请</VanButton>
            </div>

            <div v-if="showInfoPanel" class="info-panel">
              <label>请补充的资料或原因<textarea v-model.trim="infoReason" rows="3" maxlength="1000" placeholder="说明用户需要补充什么，以及为什么这会影响分析。"></textarea></label>
              <div><VanButton class="secondary-button compact-button" type="default" plain native-type="button" @click="showInfoPanel = false">取消</VanButton><VanButton class="primary-button compact-button" type="primary" native-type="button" :disabled="infoSaving || !infoReason" :aria-busy="infoSaving" @click="requestInfo">{{ infoSaving ? '发送中…' : '标记待补充' }}</VanButton></div>
            </div>

            <div class="workspace-grid">
              <section class="facts-panel">
                <div class="panel-heading"><div><p class="eyebrow">SOURCE / USER INPUT</p><h3>资料与需求</h3></div><span>申请快照</span></div>
                <dl class="detail-list source-list"><div><dt>姓名</dt><dd>{{ workspace.user.name || workspace.request.request_payload?.profile?.name || '—' }}</dd></div><div><dt>性别</dt><dd>{{ genderLabel(workspace.user.gender || workspace.request.request_payload?.profile?.gender) }}</dd></div><div><dt>出生资料</dt><dd>{{ birthSummary }}</dd></div><div><dt>出生地</dt><dd>{{ workspace.user.birth_place || workspace.request.request_payload?.profile?.birth_place || '—' }}</dd></div><div><dt>关注议题</dt><dd>{{ topicLabel(workspace.request.request_payload?.context?.focus_topics || workspace.request.request_payload?.selected_topics) }}</dd></div><div><dt>本次困惑</dt><dd>{{ workspace.request.request_payload?.context?.current_challenge || '—' }}</dd></div><div><dt>期望结果</dt><dd>{{ (workspace.request.request_payload?.context?.expected_outcomes || []).join('、') || '—' }}</dd></div><div><dt>补充说明</dt><dd>{{ workspace.request.request_payload?.context?.additional_info || workspace.request.request_payload?.additional_info || '—' }}</dd></div></dl>
              </section>

              <section v-if="workspace.draft" class="ai-panel">
                <div class="panel-heading"><div><p class="eyebrow">AI SOURCE / PRIVATE</p><h3>AI 初稿参考</h3></div><span>v{{ workspace.draft.ai_version }}</span></div>
                <p class="ai-privacy">仅咨询师和管理员可见。请以用户资料与专业判断为准，不要直接交付未审校内容。</p>
                <details class="ai-details"><summary>查看 AI 初稿字段</summary><pre>{{ pretty(workspace.draft.ai_payload) }}</pre></details>
              </section>
              <section v-else class="ai-panel ai-empty"><div class="panel-heading"><div><p class="eyebrow">AI SOURCE / PRIVATE</p><h3>等待生成初稿</h3></div></div><p>确认资料后，点击“生成 AI 初稿”。</p></section>
            </div>

            <section v-if="workspace.draft" class="editor-panel">
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
            <p v-if="workspace.task && workspace.task.status === 'failed'" class="task-error" role="alert">AI 初稿生成失败：{{ workspace.task.error || workspace.request.last_error || '请重试' }}</p>
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
