<template>
  <section class="report-node-workbench" aria-label="报告工作流进度与节点工作区">
    <div class="workflow-progress-header">
      <div>
        <p class="eyebrow">REPORT WORKFLOW</p>
        <h4>{{ progressTitle }}</h4>
        <p>{{ progressDescription }}</p>
      </div>
      <span class="workflow-version">流程 v{{ reportCase.workflow_instance?.workflow_version_id || '—' }}</span>
    </div>

    <ol class="workflow-progress-rail" aria-label="六步报告进度">
      <li
        v-for="(step, index) in steps"
        :key="step.id"
        class="workflow-progress-step"
        :class="[`progress-${String(step.status || '').toLowerCase()}`, { 'progress-current': step.id === currentStep?.id }]"
        :aria-current="step.id === currentStep?.id ? 'step' : undefined"
      >
        <span class="progress-marker">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="progress-copy">
          <strong>{{ stageFor(step.step_key)?.shortName || step.step_key }}</strong>
          <small>{{ statusLabel(step.status) }}</small>
        </span>
        <VanButton
          v-if="step.status === 'COMPLETED' && canReopen"
          class="reopen-step-button"
          type="default"
          plain
          native-type="button"
          :disabled="loading"
          :aria-label="`重新打开${stageFor(step.step_key)?.shortName || step.step_key}`"
          @click="$emit('reopen', step)"
        >
          重开
        </VanButton>
      </li>
    </ol>

    <div v-if="stage && currentStep" class="node-workspace">
      <header class="node-heading">
        <div>
          <p class="node-step-label">{{ currentStep.step_key }} · 第 {{ currentStep.sequence_no }} 步</p>
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
            <h4>本节点输入</h4>
            <VanButton class="node-link-button" type="default" plain native-type="button" @click="$emit('to-section', 'case-context')">查看完整情境</VanButton>
          </div>
          <dl class="node-input-list">
            <div>
              <dt>申请情境</dt>
              <dd>{{ contextCount }} 项 · 档案 v{{ reportCase.application_snapshot?.profile_version || '—' }}</dd>
            </div>
            <div>
              <dt>有效 Evidence</dt>
              <dd>{{ activeEvidence.length }} 条<template v-if="systemEvidenceCount"> · 系统计算 {{ systemEvidenceCount }} 条</template></dd>
            </div>
            <div v-if="currentStep.sequence_no > 1 && currentStep.step_key !== 'S5' && currentStep.step_key !== 'S6'">
              <dt>上游确认判断</dt>
              <dd>{{ upstreamFindings.length }} 条 Finding · {{ upstreamFragments.length }} 条分析片段</dd>
            </div>
            <div v-if="['S5', 'S6'].includes(currentStep.step_key)">
              <dt>已确认专业语义</dt>
              <dd>{{ confirmedFindingCount }} 条 Finding · {{ confirmedAnalysisCount }} 条 Analysis Fragment</dd>
            </div>
            <div v-if="currentStep.step_key === 'S5'">
              <dt>NarrativePlan</dt>
              <dd>{{ narrativePlanStatus || '尚未确认' }}</dd>
            </div>
            <div v-if="currentStep.step_key === 'S6'">
              <dt>质量审核</dt>
              <dd>{{ qualityStatus || '尚未运行' }}</dd>
            </div>
          </dl>
          <details class="node-context-details">
            <summary>展开本次用户情境</summary>
            <dl class="node-context-values">
              <div v-for="item in contextItems" :key="item.key">
                <dt>{{ item.label }}</dt>
                <dd>{{ item.value }}</dd>
              </div>
              <p v-if="!contextItems.length">申请快照中没有额外情境字段。</p>
            </dl>
          </details>
        </section>

        <section class="node-tools" aria-label="当前节点工具与检查">
          <div class="node-section-heading"><h4>可用工具</h4><span>{{ executionMode }}</span></div>
          <ul class="node-tool-list">
            <li v-for="tool in stage.tools" :key="tool">{{ tool }}</li>
          </ul>
          <div class="node-checklist">
            <h5>本节点待核对</h5>
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
          已确认 {{ completionGate.confirmed_finding_count }} 条 Finding、{{ completionGate.confirmed_fragment_count }} 条分析片段。
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
            {{ latestAnalysisRun ? '重新生成分析草稿' : '生成 AI 分析草稿' }}
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
          {{ statusLabel(currentStep.status) }}，请查看对应运行记录。
        </span>
      </footer>
    </div>
    <div v-else class="workflow-finished-state" :class="`workflow-finished-${String(reportCase.status || '').toLowerCase()}`">
      <strong>{{ reportCase.status === 'DELIVERED' ? '报告已交付' : reportCase.status === 'READY_TO_DELIVER' ? '六个工作节点已完成' : '工作流节点已完成' }}</strong>
      <span>{{ reportCase.status === 'DELIVERED' ? '当前版本已锁定，可在质量审核区查看交付记录。' : '请在最终质量审核区继续完成门禁与交付。' }}</span>
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
  additional_info: '补充说明'
}

export default {
  name: 'ReportNodeWorkbench',
  components: { VanButton },
  props: {
    reportCase: { type: Object, required: true },
    content: { type: Object, required: true },
    currentStep: { type: Object, default: null },
    qualityStatus: { type: String, default: '' },
    narrativePlanStatus: { type: String, default: '' },
    latestAnalysisRun: { type: Object, default: null },
    completionGate: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    analysisSaving: { type: Boolean, default: false },
    canReopen: { type: Boolean, default: false }
  },
  emits: ['start-step', 'complete-step', 'toggle-return', 'to-section', 'run-analysis', 'reopen'],
  computed: {
    executionMode() {
      if (['S1', 'S2', 'S3', 'S4'].includes(this.currentStep?.step_key)) {
        return 'AI 草稿 + 咨询师审核'
      }
      return this.currentStep?.executor === 'HYBRID' ? 'AI + 人工复核' : '人工审核'
    },
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
          label: CONTEXT_LABELS[key] || key,
          value: Array.isArray(value) ? value.join('、') : typeof value === 'object' ? JSON.stringify(value) : String(value)
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
    progressTitle() {
      if (this.currentStep) return `第 ${this.currentStep.sequence_no} / ${this.workflowSteps.length} 步 · ${this.stage?.shortName || this.currentStep.step_key}`
      return this.reportCase.status === 'DELIVERED' ? '报告流程已交付' : '工作节点已完成 · 等待最终交付'
    },
    progressDescription() {
      if (this.currentStep) return `${this.stage?.name || this.currentStep.step_key}是当前待处理节点；节点完成后，下游工作会按流程激活。`
      if (this.reportCase.status === 'DELIVERED') return '所有节点和最终交付均已完成。'
      return 'S1–S6 均已完成；请在最终质量审核区执行最终门禁与版本交付。'
    }
  },
  methods: {
    gateBlockerLabel(code) {
      return {
        report_analysis_output_required: '至少确认一条 Finding 或分析片段。',
        report_analysis_findings_unreviewed: '仍有待审核 Finding，请接受或拒绝。',
        report_analysis_fragments_unreviewed: '仍有待审核分析片段，请确认或修改。',
        report_analysis_fragments_stale: '存在已过期分析片段，请重新审核。'
      }[code] || code
    },
    stageFor(stepKey) {
      return reportStage(stepKey)
    },
    statusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || status || '未知'
    },
    sectionLabel(section) {
      return {
        'case-context': '申请情境',
        'case-evidence': 'Evidence',
        'case-findings': 'Finding 审核',
        'case-fragments': '内容片段',
        'case-narrative': '叙事与写作',
        'case-quality': '最终 QA'
      }[section] || section
    }
  }
}
</script>

<style scoped src="./ReportNodeWorkbench.css"></style>
