<template>
  <section id="report-section-overview" class="report-node-workbench" :class="{ 'workbench-compact': compact }" aria-label="报告处理进度">
    <div class="workflow-progress-header">
      <div>
        <p class="eyebrow">处理进度</p>
        <h4>{{ progressTitle }}</h4>
        <p>{{ progressDescription }}</p>
      </div>
    </div>

    <ol class="workflow-progress-rail" aria-label="报告六步处理进度">
      <li
        v-for="(step, index) in steps"
        :key="step.id"
        class="workflow-progress-step"
        :class="[`progress-${String(step.status || '').toLowerCase()}`, { 'progress-current': step.id === currentStep?.id }]"
        :aria-current="step.id === currentStep?.id ? 'step' : undefined"
      >
        <span class="progress-marker">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="progress-copy">
          <strong>{{ stageFor(step.step_key)?.shortName || '处理步骤' }}</strong>
          <small>{{ statusLabel(step.status) }}</small>
        </span>
        <VanButton
          v-if="step.status === 'COMPLETED' && canReopen"
          class="reopen-step-button"
          type="default"
          plain
          native-type="button"
          :disabled="loading"
          :aria-label="`重新打开${stageFor(step.step_key)?.shortName || '处理步骤'}`"
          @click="$emit('reopen', step)"
        >
          重开
        </VanButton>
      </li>
    </ol>

    <dl v-if="!compact" class="report-overview-stats" aria-label="报告处理概况">
      <div v-for="item in overviewStats" :key="item.label">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
        <small>{{ item.note }}</small>
      </div>
    </dl>

    <aside v-if="compact && stage && currentStep" class="compact-step-guidance">
      <span>当前步骤</span>
      <strong>第 {{ currentStep.sequence_no }} 步 · {{ stage.name }}</strong>
      <p>{{ nextAction }}</p>
    </aside>

    <div v-if="!compact && stage && currentStep" class="node-workspace">
      <header class="node-heading">
        <div>
          <p class="node-step-label">第 {{ currentStep.sequence_no }} 步 / 共 {{ workflowSteps.length }} 步</p>
          <h3>{{ stage.name }}</h3>
          <p>{{ stage.purpose }}</p>
        </div>
        <span class="node-status" :class="`node-status-${String(currentStep.status).toLowerCase()}`">
          {{ statusLabel(currentStep.status) }}
        </span>
      </header>

      <div class="node-workspace-columns">
        <section class="node-inputs" aria-label="当前节点输入">
          <div class="node-section-heading">
            <h4>本步骤参考信息</h4>
            <VanButton class="node-link-button" type="default" plain native-type="button" @click="$emit('to-section', 'case-context')">查看用户情境</VanButton>
          </div>
          <dl class="node-input-list">
            <div>
              <dt>本次申请</dt>
              <dd>{{ contextCount }} 项用户情况</dd>
            </div>
            <div>
              <dt>可参考资料</dt>
              <dd>{{ activeEvidence.length }} 项<template v-if="systemEvidenceCount">，其中 {{ systemEvidenceCount }} 项来自系统测算</template></dd>
            </div>
            <div v-if="currentStep.sequence_no > 1 && currentStep.step_key !== 'S5' && currentStep.step_key !== 'S6'">
              <dt>前序已确认内容</dt>
              <dd>{{ upstreamFindings.length }} 条判断、{{ upstreamFragments.length }} 段分析</dd>
            </div>
            <div v-if="['S5', 'S6'].includes(currentStep.step_key)">
              <dt>已确认的专业内容</dt>
              <dd>{{ confirmedFindingCount }} 条判断、{{ confirmedAnalysisCount }} 段分析</dd>
            </div>
            <div v-if="currentStep.step_key === 'S5'">
              <dt>报告主线</dt>
              <dd>{{ narrativePlanLabel }}</dd>
            </div>
            <div v-if="currentStep.step_key === 'S6'">
              <dt>交付前检查</dt>
              <dd>{{ qualityStatusLabel }}</dd>
            </div>
          </dl>
          <details class="node-context-details">
            <summary>查看本次用户情境</summary>
            <dl class="node-context-values">
              <div v-for="item in contextItems" :key="item.key">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value }}</dd>
              </div>
              <p v-if="!contextItems.length">申请快照中没有额外情境字段。</p>
            </dl>
          </details>
        </section>

        <section class="node-tools" aria-label="当前步骤的操作与核对事项">
          <div class="node-section-heading"><h4>可以进行的操作</h4></div>
          <ul class="node-tool-list">
            <li v-for="tool in stage.tools" :key="tool">{{ tool }}</li>
          </ul>
          <div class="node-checklist">
            <h5>建议按顺序核对</h5>
            <ul>
              <li v-for="item in stage.checklist" :key="item">{{ item }}</li>
            </ul>
          </div>
        </section>
      </div>

      <div
        v-if="completionGate && ['S1', 'S2', 'S3', 'S4'].includes(currentStep.step_key)"
        class="node-completion-gate"
        :class="{ 'gate-ready': completionGate.can_complete }"
        role="status"
        aria-live="polite"
      >
        <strong>{{ completionGate.can_complete ? '本节点审核条件已满足' : '完成前还需处理' }}</strong>
        <span v-if="completionGate.can_complete">
          已确认 {{ completionGate.confirmed_finding_count }} 条判断、{{ completionGate.confirmed_fragment_count }} 段分析内容。
        </span>
        <ul v-else>
          <li v-for="blocker in completionGate.blockers" :key="blocker">{{ gateBlockerLabel(blocker) }}</li>
        </ul>
      </div>

      <footer class="node-actions">
        <VanButton
          v-if="currentStep.status === 'READY'"
          class="primary-button compact-button"
          type="primary"
          native-type="button"
          :disabled="loading"
          :loading="loading"
          @click="$emit('start-step')"
        >
          开始本节点
        </VanButton>
        <template v-else-if="currentStep.status === 'IN_REVIEW'">
          <VanButton
            v-if="['S1', 'S2', 'S3', 'S4'].includes(currentStep.step_key)"
            class="primary-button compact-button"
            type="primary"
            native-type="button"
            :disabled="analysisSaving"
            :loading="analysisSaving"
            @click="$emit('run-analysis')"
          >
            {{ latestAnalysisRun ? '重新生成分析建议' : '生成分析建议' }}
          </VanButton>
          <VanButton
            v-for="section in stage.sections"
            :key="section"
            class="node-link-button"
            type="default"
            plain
            native-type="button"
            @click="$emit('to-section', section)"
          >
            {{ sectionLabel(section) }}
          </VanButton>
          <VanButton
            v-if="currentStep.step_key !== 'S6'"
            class="secondary-button compact-button"
            type="default"
            plain
            native-type="button"
            :disabled="loading"
            @click="$emit('toggle-return')"
          >
            退回上游
          </VanButton>
          <VanButton
            v-if="currentStep.step_key !== 'S6'"
            class="primary-button compact-button"
            type="primary"
            native-type="button"
            :disabled="loading || (completionGate && !completionGate.can_complete)"
            :loading="loading"
            @click="$emit('complete-step')"
          >
            完成本节点
          </VanButton>
        </template>
        <span v-else-if="currentStep.status === 'EXECUTING' || currentStep.status === 'WAITING_REVIEW'" class="node-running-state">
          {{ statusLabel(currentStep.status) }}，内容完成后可在对应页面继续处理。
        </span>
      </footer>
    </div>
    <div v-else-if="!currentStep || !stage" class="workflow-finished-state" :class="`workflow-finished-${String(reportCase.status || '').toLowerCase()}`">
      <strong>{{ finishedTitle }}</strong>
      <span>{{ finishedDescription }}</span>
      <VanButton
        v-if="reportCase.status === 'READY_TO_DELIVER'"
        class="node-link-button"
        type="default"
        plain
        native-type="button"
        @click="$emit('to-section', 'case-quality')"
      >
        前往交付前检查
      </VanButton>
    </div>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import { REPORT_STEP_STATUS_LABELS, reportStage } from '../stages.js'

const CONTEXT_LABELS = {
  focus_topics: '关注主题',
  selected_topics: '关注主题',
  current_challenge: '当前挑战',
  expected_outcomes: '期待结果',
  issue_duration: '持续时间',
  impact_level: '影响程度',
  decision_status: '决策状态',
  decision_description: '决策描述',
  decision_style: '决策方式',
  additional_info: '补充说明',
  usage_scenario: '使用场景',
  calendar_goal: '当前目标',
  goal: '当前目标',
  gender: '性别',
  birth_date: '出生日期',
  birth_time: '出生时间',
  birth_place: '出生地点'
}

const CONTEXT_VALUE_LABELS = {
  male: '男', female: '女', solar: '公历', lunar: '农历',
  career: '职业发展', relationship: '亲密关系', family: '家庭议题',
  self: '自我价值', growth: '个人成长', stress: '压力焦虑',
  low: '较低', medium: '一般', high: '较高', critical: '非常高',
  not_started: '尚未开始', considering: '正在考虑', decided: '已经决定',
  undecided: '尚未决定', unsure: '尚未确定', yes: '是', no: '否'
}

function contextDisplayValue(value) {
  if (Array.isArray(value)) return value.map(contextDisplayValue).filter(Boolean).join('、') || '—'
  if (value && typeof value === 'object') return Object.values(value).map(contextDisplayValue).filter(Boolean).join('、') || '—'
  if (value === true) return '是'
  if (value === false) return '否'
  if (value === null || value === undefined || value === '') return '—'
  const text = String(value)
  return CONTEXT_VALUE_LABELS[text.toLowerCase().replace(/[ -]+/g, '_')] || (/[A-Za-z]{2,}/.test(text) ? '已填写' : text)
}

export default {
  name: 'ReportNodeWorkbench',
  components: { VanButton },
  props: {
    reportCase: { type: Object, required: true },
    compact: { type: Boolean, default: false },
    content: { type: Object, required: true },
    currentStep: { type: Object, default: null },
    qualityStatus: { type: String, default: '' },
    narrativePlanStatus: { type: String, default: '' },
    latestAnalysisRun: { type: Object, default: null },
    completionGate: { type: Object, default: null },
    qualityIssueCount: { type: Number, default: 0 },
    qualityBlockingCount: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
    analysisSaving: { type: Boolean, default: false },
    canReopen: { type: Boolean, default: false }
  },
  emits: ['start-step', 'complete-step', 'toggle-return', 'to-section', 'run-analysis', 'reopen'],
  computed: {
    stage() {
      return this.currentStep ? reportStage(this.currentStep.step_key) : null
    },
    workflowSteps() {
      return this.reportCase.workflow_instance?.steps || []
    },
    steps() {
      return this.workflowSteps
    },
    activeEvidence() {
      return (this.content.evidence || []).filter(item => item.status === 'ACTIVE')
    },
    systemEvidenceCount() {
      return this.activeEvidence.filter(item => item.source_type === 'SYSTEM_CALCULATED').length
    },
    contextCount() {
      return Object.keys(this.reportCase.application_snapshot?.context || {}).length
    },
    contextItems() {
      return Object.entries(this.reportCase.application_snapshot?.context || {})
        .filter(([, value]) => value !== null && value !== '' && !(Array.isArray(value) && value.length === 0))
        .map(([key, value]) => ({
          key,
          label: CONTEXT_LABELS[key] || '其他补充信息',
          value: contextDisplayValue(value)
        }))
    },
    upstreamStepIds() {
      if (!this.currentStep) return new Set()
      return new Set(this.workflowSteps
        .filter(step => step.sequence_no < this.currentStep.sequence_no)
        .map(step => step.id))
    },
    upstreamFindings() {
      return (this.content.findings || []).filter(item =>
        item.status === 'CONFIRMED' && this.upstreamStepIds.has(item.owner_step_task_id)
      )
    },
    upstreamFragments() {
      return (this.content.fragments || []).filter(item =>
        item.fragment_type === 'ANALYSIS' && item.status === 'CONFIRMED' && this.upstreamStepIds.has(item.owner_step_task_id)
      )
    },
    confirmedFindingCount() {
      return (this.content.findings || []).filter(item => item.status === 'CONFIRMED').length
    },
    confirmedAnalysisCount() {
      return (this.content.fragments || []).filter(item => item.fragment_type === 'ANALYSIS' && item.status === 'CONFIRMED').length
    },
    pendingFindingCount() {
      return (this.content.findings || []).filter(item => ['PROPOSED', 'STALE'].includes(item.status)).length
    },
    confirmedContentCount() {
      return (this.content.fragments || []).filter(item => item.status === 'CONFIRMED').length
    },
    pendingContentCount() {
      return (this.content.fragments || []).filter(item => ['PROPOSED', 'STALE'].includes(item.status)).length
    },
    overviewStats() {
      return [
        {
          label: '资料依据',
          value: `${this.activeEvidence.length} 项`,
          note: `${this.contextCount} 项用户情境信息`
        },
        {
          label: '专业判断',
          value: `已确认 ${this.confirmedFindingCount} 条`,
          note: `${this.pendingFindingCount} 条待审核或复核`
        },
        {
          label: '报告内容',
          value: `已确认 ${this.confirmedContentCount} 段`,
          note: `${this.pendingContentCount} 段待审核或复核`
        },
        {
          label: '交付前检查',
          value: this.qualityStatusLabel,
          note: `${this.qualityIssueCount} 项待处理，其中 ${this.qualityBlockingCount} 项必须处理`
        }
      ]
    },
    finishedTitle() {
      return {
        DELIVERED: '报告已交付',
        READY_TO_DELIVER: '最终复核已通过',
        CANCELLED: '报告处理已关闭'
      }[this.reportCase.status] || '内容处理步骤已完成'
    },
    finishedDescription() {
      return {
        DELIVERED: '报告已交付，当前版本已留存。',
        READY_TO_DELIVER: '最终复核已完成，请前往交付前检查生成交付版本。',
        CANCELLED: '这份报告已关闭，不能继续处理。'
      }[this.reportCase.status] || '请查看报告处理概况并继续完成交付。'
    },
    progressTitle() {
      if (this.currentStep) return `第 ${this.currentStep.sequence_no} 步 / 共 ${this.workflowSteps.length} 步 · ${this.stage?.shortName || ''}`
      return this.reportCase.status === 'DELIVERED'
        ? '报告已交付'
        : this.reportCase.status === 'READY_TO_DELIVER'
          ? '六步处理和最终复核已完成'
          : '内容处理步骤已完成'
    },
    progressDescription() {
      if (this.currentStep) return `${this.stage?.name || '当前步骤'}是目前需要处理的部分；完成后会进入下一步。`
      if (this.reportCase.status === 'DELIVERED') return '所有处理步骤和最终交付均已完成。'
      if (this.reportCase.status === 'READY_TO_DELIVER') return '报告已通过最终复核，请进入交付前检查生成交付版本。'
      return '当前没有待处理的工作步骤。'
    },
    nextAction() {
      if (!this.currentStep) {
        if (this.reportCase.status === 'DELIVERED') return '报告已经交付。'
        if (this.reportCase.status === 'READY_TO_DELIVER') return '最终复核已通过，请生成并交付报告版本。'
        if (this.reportCase.status === 'CANCELLED') return '这份报告已关闭，不能继续处理。'
        return '请查看交付前检查并完成最后确认。'
      }
      if (this.currentStep.status === 'READY') return '先开始本步骤，查看本次需要处理的内容。'
      if (['EXECUTING', 'WAITING_REVIEW'].includes(this.currentStep.status)) return '内容正在准备，完成后回来查看并审核。'
      return {
        S1: '先核对用户出生资料和系统测算依据，再审核初步判断。',
        S2: '对照用户自述和已确认资料，审核可能的思考与应对模式。',
        S3: '只整合前序已确认内容，核对彼此支持或冲突的地方。',
        S4: '结合具体情境理解应对方式，再整理可执行、可调整的行动。',
        S5: '先确认报告主线，再生成报告内容并逐段审阅。',
        S6: '先运行交付前检查，处理问题后再完成最终复核。'
      }[this.currentStep.step_key] || '查看本步骤建议和相关资料，完成审核后再继续。'
    },
    narrativePlanLabel() {
      return {
        CONFIRMED: '已确认',
        STALE: '需要重新确认',
        PROPOSED: '待确认'
      }[this.narrativePlanStatus] || '尚未确定'
    },
    qualityStatusLabel() {
      return {
        NOT_RUN: '尚未检查',
        PASSED: '检查通过',
        PROGRAMMATIC_BLOCKED: '发现需处理的问题',
        BLOCKED: '暂不能交付',
        READY: '可以进行最终复核'
      }[this.qualityStatus] || '尚未检查'
    }
  },
  methods: {
    gateBlockerLabel(code) {
      return {
        report_analysis_output_required: '至少需要确认一条专业判断或一段分析内容。',
        report_analysis_findings_unreviewed: '还有待审核的专业判断，请逐条确认、修改或拒绝。',
        report_analysis_fragments_unreviewed: '还有待审核的分析内容，请确认或修改。',
        report_analysis_fragments_stale: '有分析内容需要重新审核。'
      }[code] || '请先处理本步骤尚未完成的事项。'
    },
    stageFor(stepKey) {
      return reportStage(stepKey)
    },
    statusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || '处理中'
    },
    sectionLabel(section) {
      return {
        'case-context': '用户情境',
        'case-evidence': '资料依据',
        'case-findings': '专业判断',
        'case-fragments': '报告内容',
        'case-narrative': '叙事与写作',
        'case-quality': '交付前检查'
      }[section] || section
    }
  }
}
</script>

<style scoped src="./ReportNodeWorkbench.css"></style>
