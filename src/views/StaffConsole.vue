<template>
  <div class="staff-shell">
    <BrandNav />
    <main class="staff-main">
      <header class="staff-heading">
        <div>
          <p class="section-kicker">SERVICE REQUESTS / REVIEW ROOM</p>
          <h1>咨询申请工作台</h1>
          <p>接收用户申请，参考 AI 初稿完成结构化审校，再将可交付的结果发回用户。</p>
        </div>
        <div class="heading-actions">
          <span class="live-state" role="status" aria-live="polite"><i :class="{ active: loading || pollingTask }"></i>{{ pollingTask ? 'AI 初稿处理中' : loading ? '正在同步' : '已同步' }}</span>
          <button class="secondary-button" type="button" :disabled="loading" @click="loadRequests">刷新申请</button>
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
            <button v-if="selectedRequest.status === 'submitted' && !selectedRequest.assigned_consultant_id" class="primary-button" type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接单中…' : '接受申请' }}</button>
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

            <div class="workspace-actions">
              <button v-if="workspace.request.status === 'submitted' && !workspace.request.assigned_consultant_id" class="primary-button" type="button" :disabled="accepting" :aria-busy="accepting" @click="acceptRequest">{{ accepting ? '接收中…' : '接受并处理' }}</button>
              <button v-if="workspace.request.status === 'accepted' || workspace.request.status === 'failed'" class="primary-button" type="button" :disabled="aiStarting" :aria-busy="aiStarting" @click="startAI">{{ aiStarting ? '启动中…' : workspace.request.status === 'failed' ? '重试 AI 初稿' : '生成 AI 初稿' }}</button>
              <button v-if="workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing'" class="secondary-button" type="button" :disabled="aiStarting" @click="regenerateAI">重新生成 AI 初稿</button>
              <button v-if="workspace.draft && (workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing')" class="secondary-button" type="button" :disabled="saving" :aria-busy="saving" @click="saveDraft">{{ saving ? '保存中…' : '保存草稿' }}</button>
              <button v-if="workspace.draft && (workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing')" class="primary-button deliver-button" type="button" :disabled="delivering" :aria-busy="delivering" @click="deliver">{{ delivering ? '交付中…' : '提交最终交付' }}</button>
              <button v-if="workspace.request.status === 'accepted' || workspace.request.status === 'ai_ready' || workspace.request.status === 'reviewing' || workspace.request.status === 'failed'" class="text-button" type="button" @click="showInfoPanel = !showInfoPanel">待用户补充</button>
              <button v-if="admin && ['submitted', 'accepted', 'needs_info', 'failed'].includes(workspace.request.status)" class="text-button danger-text" type="button" @click="rejectRequest">关闭申请</button>
            </div>

            <div v-if="showInfoPanel" class="info-panel">
              <label>请补充的资料或原因<textarea v-model.trim="infoReason" rows="3" maxlength="1000" placeholder="说明用户需要补充什么，以及为什么这会影响分析。"></textarea></label>
              <div><button class="secondary-button compact-button" type="button" @click="showInfoPanel = false">取消</button><button class="primary-button compact-button" type="button" :disabled="infoSaving || !infoReason" @click="requestInfo">{{ infoSaving ? '发送中…' : '标记待补充' }}</button></div>
            </div>

            <div class="workspace-grid">
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
                <div class="entry-toolbar"><div><strong>每日条目</strong><small>固定 30 天 · 已填 {{ calendarEditor.entries.length }} 条 · 保存和交付时会再次校验</small></div><button class="secondary-button compact-button" type="button" @click="addEntry">添加条目</button></div>
                <div class="entry-list">
                  <article v-for="(entry, index) in calendarEditor.entries" :key="entry._key" class="entry-editor"><div class="entry-head"><strong>DAY {{ String(index + 1).padStart(2, '0') }}</strong><button class="text-button danger-text" type="button" @click="removeEntry(index)">移除</button></div><div class="form-grid three"><label>日期<input v-model="entry.entry_date" type="date"></label><label>色调<select v-model="entry.tone"><option value="green">推进</option><option value="green-yellow">先推后收</option><option value="yellow-green">先备后行</option><option value="yellow">观察</option><option value="red-yellow">缓冲</option><option value="red">收气</option><option value="rest">休整</option></select></label><label>状态标签<input v-model.trim="entry.status_label" placeholder="例如：准备期"></label><label>关键词<input v-model.trim="entry.keyword" placeholder="例如：观察"></label><label class="span-two">摘要<input v-model.trim="entry.summary" placeholder="给用户的一句话提示"></label></div><div class="form-grid two"><label>适合事项 <small>用逗号或换行分隔</small><textarea v-model="entry.suitableText" rows="3"></textarea></label><label>不适合事项 <small>用逗号或换行分隔</small><textarea v-model="entry.unsuitableText" rows="3"></textarea></label></div><label>时间窗口<input v-model.trim="entry.time_window" placeholder="例如：上午适合整理，下午适合轻推"></label><label>咨询师备注 <small>仅工作台可见</small><textarea v-model="entry.admin_note" rows="2"></textarea></label></article>
                </div>
              </div>
            </section>
            <p v-if="workspace.task && workspace.task.status === 'failed'" class="task-error" role="alert">AI 初稿生成失败：{{ workspace.task.error || workspace.request.last_error || '请重试' }}</p>
          </div>

          <div v-else class="empty-state"><IconMark class="empty-icon" name="compass" /><p>从左侧选择一份申请开始处理。</p><small>待接单申请只展示必要摘要；接单后才会打开完整资料。</small></div>
        </section>
      </section>
    </main>
  </div>
</template>

<script>
import { getAllAdminUsers } from '../utils/businessService'
import { hasRole } from '../stores/auth'
import {
  acceptStaffServiceRequest,
  deliverStaffServiceRequest,
  getStaffServiceRequestTask,
  getStaffServiceRequestWorkspace,
  getStaffServiceRequests,
  rejectAdminServiceRequest,
  requestStaffInfo,
  retryStaffAIDraft,
  saveStaffDraft,
  startStaffAIDraft,
  updateAdminServiceRequestAssignment
} from '../utils/serviceRequestService'

const STATUS_LABELS = {
  submitted: '待接单',
  accepted: '待生成初稿',
  ai_processing: 'AI 处理中',
  ai_ready: '待审校',
  reviewing: '审校中',
  needs_info: '待补资料',
  failed: '生成失败',
  delivered: '已交付',
  withdrawn: '已撤回',
  rejected: '已拒绝'
}

function clone(value) {
  return value ? JSON.parse(JSON.stringify(value)) : value
}

function splitList(value) {
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean)
  return String(value || '').split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
}

function listText(value) {
  return Array.isArray(value) ? value.join('\n') : String(value || '')
}

function reportEditorFromPayload(payload = {}) {
  const energy = payload.energy_profile || {}
  const career = payload.career_guidance || {}
  const relationship = payload.relationship_pattern || {}
  const growth = payload.personal_growth || {}
  const actionPlan = (growth.action_plan || []).map(item => typeof item === 'string' ? item : [item.area, item.action, item.timeline].filter(Boolean).join(' · '))
  return {
    title: payload.title || '辰鉴·人生说明书',
    energy: { type: energy.type || '', core_traits: energy.core_traits || energy.coreTraits || '', description: energy.description || '' },
    career: { suitable_paths: listText(career.suitable_paths || career.suitablePaths), work_style: career.work_style || career.workStyle || '', development_suggestions: listText(career.development_suggestions || career.developmentSuggestions) },
    relationship: { style: relationship.style || '', strengths: listText(relationship.strengths), challenges: listText(relationship.challenges), growth_direction: relationship.growth_direction || relationship.growthDirection || '' },
    growth: { current_issues: listText(growth.current_issues || growth.currentIssues), action_plan: actionPlan.join('\n'), resources: listText(growth.resources) },
    summary: payload.summary || ''
  }
}

function calendarEditorFromPayload(payload = {}) {
  const meta = payload.meta_payload || {}
  return {
    title: payload.title || '辰鉴·你的决策时机说明书',
    start_date: payload.start_date || '',
    end_date: payload.end_date || '',
    meta_payload: { ...meta, rhythm: meta.rhythm || '', intro: meta.intro || '' },
    entries: (payload.entries || []).map((entry, index) => ({
      ...clone(entry),
      _key: `${entry.entry_date || 'entry'}-${index}-${Math.random().toString(36).slice(2, 7)}`,
      suitableText: listText(entry.suitable),
      unsuitableText: listText(entry.unsuitable)
    }))
  }
}

export default {
  name: 'StaffConsole',
  data() {
    const admin = hasRole('admin')
    return {
      admin,
      scope: admin ? 'all' : 'available',
      scopeOptions: admin ? [{ id: 'all', label: '全部申请' }, { id: 'available', label: '待接单' }, { id: 'mine', label: '我的处理中' }] : [{ id: 'available', label: '待接单' }, { id: 'mine', label: '我的处理中' }],
      serviceType: '',
      statusFilter: '',
      statusOptions: ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing', 'needs_info', 'failed', 'delivered'],
      requests: { total: 0, items: [] },
      selectedRequest: null,
      workspace: null,
      loading: false,
      accepting: false,
      aiStarting: false,
      saving: false,
      delivering: false,
      infoSaving: false,
      pollingTask: false,
      task: null,
      pollTimer: null,
      message: '',
      showInfoPanel: false,
      infoReason: '',
      reportEditor: reportEditorFromPayload(),
      calendarEditor: calendarEditorFromPayload(),
      consultants: [],
      assignmentId: null,
      assignmentSaving: false
    }
  },
  computed: {
    scopeDescription() {
      if (this.scope === 'available') return '仅展示还未被接单的申请。'
      if (this.scope === 'mine') return '展示分配给当前咨询师的申请。'
      return '管理员可查看全量申请并介入处理。'
    },
    birthSummary() {
      const profile = this.workspace?.request?.request_payload?.profile || {}
      const user = this.workspace?.user || {}
      const year = user.birth_year || profile.birth_year
      const month = user.birth_month || profile.birth_month
      const day = user.birth_day || profile.birth_day
      if (!year || !month || !day) return '—'
      return `${year} 年 ${month} 月 ${day} 日 · ${profile.calendar_type === 'lunar' ? '农历' : '公历'}${profile.birth_hour !== null && profile.birth_hour !== undefined ? ` · ${profile.birth_hour}:${String(profile.birth_minute || 0).padStart(2, '0')}` : ''}`
    }
  },
  mounted() {
    this.loadRequests()
    this.loadConsultants()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async loadRequests() {
      this.loading = true
      try {
        this.requests = await getStaffServiceRequests({ scope: this.scope, service_type: this.serviceType || undefined, status: this.statusFilter || undefined })
        if (this.selectedRequest) {
          const refreshed = this.requests.items.find(item => item.id === this.selectedRequest.id)
          if (refreshed) this.selectedRequest = refreshed
        }
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.loading = false
      }
    },
    async changeScope(scope) {
      this.scope = scope
      this.selectedRequest = null
      this.workspace = null
      this.stopPolling()
      await this.loadRequests()
    },
    async selectRequest(item) {
      this.stopPolling()
      this.selectedRequest = item
      this.workspace = null
      this.message = ''
      if (item.assigned_consultant_id || this.admin) await this.loadWorkspace(item.id)
    },
    async loadWorkspace(requestId) {
      this.loading = true
      try {
        this.workspace = await getStaffServiceRequestWorkspace(requestId)
        this.assignmentId = this.workspace.request.assigned_consultant_id ?? null
        if (this.workspace.draft) {
          if (this.workspace.request.service_type === 'report') this.reportEditor = reportEditorFromPayload(this.workspace.draft.editable_payload)
          else this.calendarEditor = calendarEditorFromPayload(this.workspace.draft.editable_payload)
        }
        if (this.workspace.task?.status === 'processing') this.startPolling(this.workspace.task)
      } catch (error) {
        this.workspace = null
        this.message = this.errorText(error)
      } finally {
        this.loading = false
      }
    },
    async acceptRequest() {
      if (!this.selectedRequest || this.accepting) return
      this.accepting = true
      try {
        await acceptStaffServiceRequest(this.selectedRequest.id)
        this.message = '申请已接收，完整资料已开放。'
        await this.loadRequests()
        await this.loadWorkspace(this.selectedRequest.id)
      } catch (error) {
        this.message = this.errorText(error)
        await this.loadRequests()
      } finally {
        this.accepting = false
      }
    },
    async startAI() {
      if (!this.workspace || this.aiStarting) return
      this.aiStarting = true
      try {
        const task = await startStaffAIDraft(this.workspace.request.id)
        this.task = task
        this.workspace.task = task
        this.message = 'AI 初稿已启动，完成后会出现在工作区。'
        this.startPolling(task)
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.aiStarting = false
      }
    },
    async regenerateAI() {
      if (!this.workspace || this.aiStarting) return
      if (!window.confirm('重新生成前会保存当前咨询师修改的版本快照，确定继续吗？')) return
      this.aiStarting = true
      try {
        const task = await retryStaffAIDraft(this.workspace.request.id, true)
        this.task = task
        this.workspace.task = task
        this.message = '已保存当前版本并重新启动 AI 初稿。'
        this.startPolling(task)
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.aiStarting = false
      }
    },
    startPolling(task) {
      this.stopPolling()
      if (!task?.task_id) return
      this.task = task
      this.pollingTask = true
      const tick = async () => {
        try {
          const updated = await getStaffServiceRequestTask(task.task_id)
          this.task = updated
          if (this.workspace) this.workspace.task = updated
          if (updated.status === 'processing') {
            this.pollTimer = window.setTimeout(tick, 1500)
          } else {
            this.pollingTask = false
            await this.loadWorkspace(this.workspace?.request?.id || task.request_id)
            this.message = updated.status === 'completed' ? 'AI 初稿已准备完成，请开始审校。' : 'AI 初稿生成失败，可在工作区重试。'
          }
        } catch (error) {
          this.pollingTask = false
          this.message = this.errorText(error)
        }
      }
      this.pollTimer = window.setTimeout(tick, 800)
    },
    stopPolling() {
      if (this.pollTimer) window.clearTimeout(this.pollTimer)
      this.pollTimer = null
      this.pollingTask = false
    },
    buildReportPayload() {
      const current = this.workspace.draft.editable_payload || {}
      return {
        ...clone(current),
        title: this.reportEditor.title,
        energy_profile: { ...current.energy_profile, type: this.reportEditor.energy.type, core_traits: this.reportEditor.energy.core_traits, description: this.reportEditor.energy.description },
        career_guidance: { ...current.career_guidance, suitable_paths: splitList(this.reportEditor.career.suitable_paths), work_style: this.reportEditor.career.work_style, development_suggestions: splitList(this.reportEditor.career.development_suggestions) },
        relationship_pattern: { ...current.relationship_pattern, style: this.reportEditor.relationship.style, strengths: splitList(this.reportEditor.relationship.strengths), challenges: splitList(this.reportEditor.relationship.challenges), growth_direction: this.reportEditor.relationship.growth_direction },
        personal_growth: { ...current.personal_growth, current_issues: splitList(this.reportEditor.growth.current_issues), action_plan: splitList(this.reportEditor.growth.action_plan).map(action => ({ area: '咨询师审校', action, timeline: '按个人节奏推进' })), resources: splitList(this.reportEditor.growth.resources) },
        summary: this.reportEditor.summary
      }
    },
    buildCalendarPayload() {
      const current = this.workspace.draft.editable_payload || {}
      return {
        ...clone(current),
        title: this.calendarEditor.title,
        start_date: this.calendarEditor.start_date,
        end_date: this.calendarEditor.end_date,
        meta_payload: clone(this.calendarEditor.meta_payload),
        entries: this.calendarEditor.entries.map(entry => ({
          entry_date: entry.entry_date,
          day_pillar: entry.day_pillar || null,
          tone: entry.tone || null,
          status_label: entry.status_label || null,
          keyword: entry.keyword || null,
          summary: entry.summary || null,
          suitable: splitList(entry.suitableText),
          unsuitable: splitList(entry.unsuitableText),
          time_window: entry.time_window || null,
          admin_note: entry.admin_note || null
        }))
      }
    },
    async saveDraft() {
      if (!this.workspace?.draft || this.saving) return
      this.saving = true
      try {
        const payload = this.workspace.request.service_type === 'report' ? this.buildReportPayload() : this.buildCalendarPayload()
        const saved = await saveStaffDraft(this.workspace.request.id, payload, this.workspace.draft.content_version)
        this.workspace.draft = { ...this.workspace.draft, ...saved }
        this.workspace.request.status = 'reviewing'
        if (this.workspace.request.service_type === 'report') this.reportEditor = reportEditorFromPayload(saved.editable_payload)
        else this.calendarEditor = calendarEditorFromPayload(saved.editable_payload)
        this.message = '咨询师修改已保存。'
      } catch (error) {
        this.message = this.errorText(error)
        if (error.response?.status === 409) await this.loadWorkspace(this.workspace.request.id)
      } finally {
        this.saving = false
      }
    },
    async requestInfo() {
      if (!this.workspace || !this.infoReason || this.infoSaving) return
      this.infoSaving = true
      try {
        const updated = await requestStaffInfo(this.workspace.request.id, this.infoReason)
        this.workspace.request = { ...this.workspace.request, ...updated }
        this.message = '已标记为待用户补充，用户会在申请中心看到原因。'
        this.showInfoPanel = false
        this.infoReason = ''
        await this.loadRequests()
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.infoSaving = false
      }
    },
    async deliver() {
      if (!this.workspace || this.delivering) return
      if (!window.confirm('确认已完成人工审校并交付给用户吗？交付后申请和结果将进入只读状态。')) return
      this.delivering = true
      try {
        const updated = await deliverStaffServiceRequest(this.workspace.request.id)
        this.workspace.request = { ...this.workspace.request, ...updated }
        this.message = '申请已交付，用户现在可以查看最终结果。'
        await this.loadRequests()
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.delivering = false
      }
    },
    async rejectRequest() {
      if (!this.admin || !this.workspace) return
      const reason = window.prompt('请输入关闭原因', '当前申请暂不具备处理条件')
      if (!reason?.trim()) return
      try {
        const updated = await rejectAdminServiceRequest(this.workspace.request.id, reason.trim())
        this.workspace.request = { ...this.workspace.request, ...updated }
        this.message = '申请已关闭，用户会在申请中心看到状态。'
        await this.loadRequests()
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    addEntry() {
      this.calendarEditor.entries.push({ _key: `new-${Date.now()}-${Math.random()}`, entry_date: '', tone: 'yellow', status_label: '', keyword: '', summary: '', suitableText: '', unsuitableText: '', time_window: '', admin_note: '' })
    },
    removeEntry(index) {
      this.calendarEditor.entries.splice(index, 1)
    },
    async loadConsultants() {
      if (!this.admin) return
      try {
        const response = await getAllAdminUsers({ role: 'consultant', is_active: true, size: 100 })
        this.consultants = response.items || []
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
    async assignConsultant() {
      if (!this.admin || !this.workspace || this.assignmentSaving) return
      this.assignmentSaving = true
      try {
        const updated = await updateAdminServiceRequestAssignment(this.workspace.request.id, this.assignmentId ? Number(this.assignmentId) : null)
        this.workspace.request = { ...this.workspace.request, ...updated }
        this.message = this.assignmentId ? '已改派咨询师。' : '已取消分配，申请回到待接单池。'
        await this.loadRequests()
      } catch (error) {
        this.message = this.errorText(error)
      } finally {
        this.assignmentSaving = false
      }
    },
    statusLabel(status) { return STATUS_LABELS[status] || status },
    genderLabel(gender) { return { male: '男', female: '女' }[gender] || '—' },
    topicLabel(topics) {
      const labels = { career: '职业发展', relationship: '亲密关系', family: '家庭议题', self: '自我价值', growth: '个人成长', stress: '压力焦虑' }
      return (topics || []).map(topic => labels[topic] || topic).join('、') || '综合自我探索'
    },
    requestGoal(item) {
      return item.service_type === 'calendar' ? item.request_preview?.calendar_goal || '—' : this.topicLabel(item.request_preview?.selected_topics)
    },
    formatDate(value) { return value ? new Date(value).toLocaleDateString('zh-CN') : '—' },
    pretty(value) { return JSON.stringify(value || {}, null, 2) },
    errorText(error) { return error.response?.data?.detail || '工作台请求失败，请稍后重试' }
  }
}
</script>

<style scoped>
.staff-shell { min-height: 100dvh; background: var(--paper, #f8f1e6); }
.staff-main { width: min(1320px, calc(100% - 32px)); margin: 0 auto; padding: 72px 0 96px; }
.staff-heading, .section-row, .workspace-header, .panel-heading, .entry-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.staff-heading { align-items: flex-end; }
.staff-heading h1 { margin: 8px 0; color: var(--ink, #3b2d24); font-size: clamp(34px, 6vw, 60px); line-height: 1.06; }
.staff-heading p:not(.section-kicker), .console-card p { color: var(--muted, #7d6653); line-height: 1.7; }
.heading-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.live-state { display: inline-flex; align-items: center; gap: 7px; color: var(--muted, #7d6653); font-size: 13px; font-weight: 800; }
.live-state i { width: 8px; height: 8px; border-radius: 50%; background: #a59786; }
.live-state i.active { background: var(--cinnabar, #b85c50); box-shadow: 0 0 0 5px rgba(184, 92, 80, .11); }
.console-message { margin: 18px 0 0; color: var(--jade-deep, #356b59); line-height: 1.6; }
.staff-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-top: 28px; padding: 12px 14px; }
.scope-tabs { display: flex; flex-wrap: wrap; gap: 5px; }
.scope-tabs button { min-height: 44px; border: 1px solid transparent; border-radius: 999px; padding: 0 14px; background: transparent; color: var(--muted, #7d6653); font: inherit; font-weight: 800; cursor: pointer; }
.scope-tabs button.active { border-color: rgba(184, 92, 80, .28); background: rgba(184, 92, 80, .1); color: var(--cinnabar-deep, #9e3f35); }
.staff-filters { display: flex; flex-wrap: wrap; gap: 10px; }
.staff-filters label { display: flex; align-items: center; gap: 7px; color: var(--muted, #7d6653); font-size: 13px; font-weight: 800; }
.staff-filters select { min-height: 42px; border: 1px solid rgba(80, 54, 32, .16); border-radius: 9px; background: #fffaf0; padding: 0 9px; color: var(--ink, #3b2d24); font: inherit; }
.staff-workspace-grid { display: grid; grid-template-columns: minmax(310px, .65fr) minmax(0, 1.35fr); gap: 16px; margin-top: 16px; align-items: start; }
.console-card { padding: 22px; }
.console-card h2 { margin: 0 0 5px; color: var(--ink, #3b2d24); }
.console-card h3 { margin: 0; color: var(--ink, #3b2d24); }
.eyebrow { color: var(--gold-deep, #8a621b); font-size: 11px; font-weight: 900; letter-spacing: .12em; }
.request-list { display: grid; gap: 8px; margin-top: 18px; }
.request-item { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 10px; min-width: 0; border: 1px solid rgba(80, 54, 32, .12); border-radius: 12px; background: rgba(255, 250, 240, .7); padding: 12px; text-align: left; cursor: pointer; }
.request-item:hover, .request-item.selected { border-color: rgba(184, 92, 80, .42); background: rgba(255, 239, 222, .84); }
.request-item-icon { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: rgba(184, 92, 80, .11); color: var(--cinnabar-deep, #9e3f35); }
.request-item-icon.type-calendar { background: rgba(93, 145, 126, .13); color: var(--jade-deep, #356b59); }
.request-item-icon :deep(svg) { width: 20px; height: 20px; }
.request-item-copy { display: grid; gap: 3px; min-width: 0; }
.request-item-copy strong { overflow: hidden; color: var(--ink, #3b2d24); text-overflow: ellipsis; white-space: nowrap; }
.request-item-copy small, .request-item-copy em { overflow: hidden; color: var(--muted, #7d6653); font-size: 12px; font-style: normal; text-overflow: ellipsis; white-space: nowrap; }
.request-item-status { max-width: 76px; color: var(--gold-deep, #8a621b); font-size: 11px; font-weight: 800; line-height: 1.35; text-align: right; }
.empty-cell, .empty-state { padding: 34px 12px; color: var(--muted, #7d6653); text-align: center; }
.empty-state small { display: block; margin-top: 8px; color: var(--muted, #7d6653); }
.empty-icon { display: block; width: 42px; height: 42px; margin: 0 auto 14px; color: var(--cinnabar, #b85c50); }
.workspace-panel { min-height: 600px; }
.workspace-header { align-items: flex-start; padding-bottom: 18px; border-bottom: 1px solid rgba(80, 54, 32, .11); }
.workspace-header h2 { margin: 5px 0; font-size: clamp(22px, 3vw, 30px); }
.workspace-user { margin: 0; font-size: 13px; }
.status-badge { display: inline-flex; min-height: 28px; align-items: center; border-radius: 999px; padding: 0 10px; background: rgba(184, 92, 80, .1); color: var(--cinnabar-deep, #9e3f35); font-size: 12px; font-weight: 800; white-space: nowrap; }
.staff-status-delivered { background: rgba(93, 145, 126, .14); color: var(--jade-deep, #356b59); }
.staff-status-needs_info { background: rgba(196, 151, 57, .14); color: #78561c; }
.preview-note { margin: 22px 0; border-left: 2px solid rgba(184, 92, 80, .25); padding: 14px 16px; background: rgba(255, 250, 240, .55); }
.preview-note strong { color: var(--ink, #3b2d24); }
.preview-note p { margin: 5px 0 0; }
.preview-lock { margin-top: 18px; font-size: 13px; }
.detail-list { display: grid; gap: 11px; margin: 20px 0; }
.detail-list div { display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 12px; }
.detail-list dt { color: var(--muted, #7d6653); font-size: 13px; }
.detail-list dd { min-width: 0; margin: 0; color: var(--ink-soft, #51463d); line-height: 1.6; word-break: break-word; }
.assignment-row { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 15px; border-bottom: 1px solid rgba(80, 54, 32, .1); padding-bottom: 14px; }
.assignment-row label { display: flex; align-items: center; gap: 8px; color: var(--ink-soft, #51463d); font-size: 13px; font-weight: 800; }
.assignment-row select { min-height: 42px; border: 1px solid rgba(80, 54, 32, .16); border-radius: 8px; background: #fffaf0; padding: 0 9px; font: inherit; }
.assignment-row small { color: var(--muted, #7d6653); }
.workspace-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 16px 0; }
.deliver-button { background: linear-gradient(145deg, #658f73, #356b59); border-color: #356b59; }
.text-button { min-height: 44px; border: 0; padding: 0 6px; background: transparent; color: var(--cinnabar-deep, #9e3f35); font: inherit; font-weight: 800; cursor: pointer; }
.info-panel { display: grid; gap: 10px; margin-bottom: 16px; border: 1px solid rgba(196, 151, 57, .28); border-radius: 11px; padding: 14px; background: rgba(196, 151, 57, .08); }
.info-panel label, .editor-panel label, .editor-fieldset label { display: grid; gap: 6px; color: var(--ink-soft, #51463d); font-size: 13px; font-weight: 800; }
.info-panel textarea, .editor-panel input, .editor-panel textarea, .editor-panel select { width: 100%; border: 1px solid rgba(80, 54, 32, .16); border-radius: 9px; background: rgba(255, 250, 240, .9); padding: 10px 11px; color: var(--ink, #3b2d24); font: inherit; font-weight: 500; line-height: 1.6; }
.info-panel textarea, .editor-panel textarea { resize: vertical; }
.info-panel > div { display: flex; justify-content: flex-end; gap: 8px; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; margin-top: 4px; }
.facts-panel, .ai-panel, .editor-panel { border: 1px solid rgba(80, 54, 32, .11); border-radius: 13px; padding: 15px; background: rgba(255, 250, 240, .5); }
.panel-heading { align-items: flex-start; margin-bottom: 12px; }
.panel-heading > span { color: var(--muted, #7d6653); font-size: 12px; }
.source-list { margin: 0; }
.source-list div { grid-template-columns: 74px minmax(0, 1fr); }
.ai-panel { background: rgba(61, 88, 77, .06); }
.ai-privacy { margin: 0 0 12px; color: var(--jade-deep, #356b59) !important; font-size: 12px; }
.ai-details { border-top: 1px solid rgba(53, 107, 89, .15); padding-top: 10px; }
.ai-details summary { min-height: 44px; display: flex; align-items: center; color: var(--jade-deep, #356b59); font-size: 13px; font-weight: 800; cursor: pointer; }
.ai-details pre { max-height: 280px; overflow: auto; margin: 8px 0 0; border-radius: 8px; padding: 10px; background: rgba(31, 49, 43, .08); color: #334c41; font: 12px/1.55 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; word-break: break-word; }
.ai-empty { min-height: 168px; }
.editor-panel { margin-top: 14px; background: rgba(255, 250, 240, .7); }
.editor-heading { padding-bottom: 12px; border-bottom: 1px solid rgba(80, 54, 32, .11); }
.report-editor, .calendar-editor { display: grid; gap: 15px; }
.wide-field { width: 100%; }
.editor-fieldset { display: grid; gap: 12px; min-width: 0; border: 1px solid rgba(80, 54, 32, .13); border-radius: 10px; padding: 13px; }
.editor-fieldset legend { padding: 0 6px; color: var(--cinnabar-deep, #9e3f35); font-size: 14px; font-weight: 900; }
.editor-fieldset small, .editor-panel label small { color: var(--muted, #7d6653); font-size: 11px; font-weight: 500; }
.form-grid { display: grid; gap: 11px; }
.form-grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.form-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.span-two { grid-column: span 2; }
.entry-toolbar { align-items: flex-end; border-top: 1px solid rgba(80, 54, 32, .1); padding-top: 14px; }
.entry-toolbar > div { display: grid; gap: 3px; }
.entry-toolbar strong { color: var(--ink, #3b2d24); }
.entry-toolbar small { color: var(--muted, #7d6653); font-size: 12px; }
.entry-list { display: grid; gap: 10px; }
.entry-editor { display: grid; gap: 11px; border: 1px solid rgba(80, 54, 32, .12); border-radius: 10px; padding: 13px; background: rgba(255, 250, 240, .7); }
.entry-head { display: flex; justify-content: space-between; align-items: center; color: var(--gold-deep, #8a621b); font-size: 12px; letter-spacing: .08em; }
.danger-text { color: var(--cinnabar-deep, #9e3f35); }
.task-error { margin-top: 16px; border-radius: 9px; padding: 12px 14px; background: rgba(158, 63, 53, .09); color: var(--cinnabar-deep, #9e3f35) !important; }
@media (max-width: 920px) {
  .staff-main { padding: 32px 0 calc(98px + var(--safe-bottom, 0px)); }
  .staff-heading, .staff-toolbar { align-items: flex-start; flex-direction: column; }
  .heading-actions, .staff-filters { width: 100%; justify-content: space-between; }
  .heading-actions .secondary-button { margin-left: auto; }
  .staff-workspace-grid { grid-template-columns: 1fr; }
  .request-list-panel { min-height: 0; }
}
@media (max-width: 620px) {
  .staff-main { width: calc(100% - 24px); }
  .console-card { padding: 15px 13px; border-radius: 14px; }
  .staff-filters { display: grid; grid-template-columns: 1fr 1fr; }
  .staff-filters label { display: grid; gap: 4px; }
  .staff-filters select { width: 100%; }
  .request-item { grid-template-columns: auto minmax(0, 1fr); }
  .request-item-status { grid-column: 2; justify-self: start; text-align: left; }
  .workspace-header { gap: 8px; }
  .workspace-header h2 { font-size: 22px; }
  .workspace-grid, .form-grid.two, .form-grid.three { grid-template-columns: 1fr; }
  .span-two { grid-column: auto; }
  .workspace-actions { align-items: stretch; }
  .workspace-actions > .primary-button, .workspace-actions > .secondary-button { flex: 1; }
  .workspace-actions > .text-button { width: 100%; text-align: left; }
  .entry-toolbar { align-items: flex-start; flex-direction: column; }
  .entry-toolbar .secondary-button { width: 100%; }
  .entry-editor { padding: 11px; }
}
</style>
