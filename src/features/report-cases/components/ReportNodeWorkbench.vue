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
        :class="[`progress-${String(step.status || '').toLowerCase()}`, { 'progress-current': step.id === currentStep?.id, 'progress-selected': step.id === viewStep?.id }]"
        :aria-current="step.id === currentStep?.id ? 'step' : undefined"
      >
        <button
          class="workflow-step-select"
          type="button"
          :aria-pressed="step.id === viewStep?.id"
          @click="selectStep(step)"
        >
          <span class="progress-marker">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="progress-copy">
            <strong>{{ stageFor(step.step_key)?.shortName || '处理步骤' }}</strong>
            <small>{{ statusLabel(step.status) }}</small>
          </span>
        </button>
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

    <aside v-if="compact && currentStep && currentStage" class="compact-step-guidance" aria-label="当前节点任务">
      <div class="compact-step-summary">
        <span>当前待处理 · 第 {{ currentStep.sequence_no }} 步</span>
        <strong>{{ currentStage.name }}</strong>
        <p>{{ currentStage.task }}</p>
        <small>可用输入：{{ compactInputSummary }}</small>
      </div>
      <div class="compact-step-actions">
        <div class="compact-step-tools" aria-label="当前节点可用工具">
          <VanButton
            v-for="tool in currentStage.tools"
            :key="tool.section"
            class="compact-tool-link"
            type="default"
            plain
            native-type="button"
            @click="$emit('to-section', tool.section)"
          >
            {{ tool.label }}
          </VanButton>
        </div>
        <VanButton
          class="primary-button compact-button compact-return-button"
          type="primary"
          native-type="button"
          aria-label="返回当前节点处理总览"
          @click="$emit('to-section', 'overview')"
        >
          返回本阶段总览
        </VanButton>
      </div>
    </aside>

    <div v-if="!compact && stage && viewStep" class="node-workspace">
      <header class="node-heading">
        <div>
          <p class="node-step-label">第 {{ viewStep.sequence_no }} 步 / 共 {{ workflowSteps.length }} 步</p>
          <h3>{{ stage.name }}</h3>
          <p>{{ stage.purpose }}</p>
        </div>
        <span class="node-status" :class="`node-status-${String(viewStep.status).toLowerCase()}`">
          {{ statusLabel(viewStep.status) }}
        </span>
      </header>

      <section class="node-task-banner" aria-label="本阶段任务与完成目标">
        <div>
          <p>本阶段任务</p>
          <strong>{{ stage.task }}</strong>
          <ol v-if="stage.actions?.length" class="node-task-steps">
            <li v-for="(action, index) in stage.actions" :key="action">
              <span>{{ index + 1 }}</span>
              <strong>{{ action }}</strong>
            </li>
          </ol>
        </div>
        <div>
          <p>完成后应得到</p>
          <strong>{{ stage.deliverable }}</strong>
        </div>
      </section>

      <section v-if="stepViewMode === 'CURRENT' && completionGate?.sop_contract" class="node-sop" aria-label="分析清单与职责分工">
        <h4>本步骤怎么做</h4>
        <dl class="node-sop-roles">
          <div><dt>程序已完成</dt><dd>{{ completionGate.sop_contract.responsibilities.program }}</dd></div>
          <div><dt>AI 提供候选</dt><dd>{{ completionGate.sop_contract.responsibilities.ai }}</dd></div>
          <div><dt>你来确认</dt><dd>{{ completionGate.sop_contract.responsibilities.human }}</dd></div>
        </dl>
        <details>
          <summary>逐项核对分析范围 · {{ completionGate.sop_contract.topics.length }} 项，{{ completionGate.missing_topics?.length || 0 }} 项待确认</summary>
          <ul class="node-sop-topics">
            <li v-for="topic in completionGate.sop_contract.topics" :key="topic.fragment_key">
              <strong>{{ topic.title }}</strong>
              <span>{{ completionGate.missing_topics?.some(item => item.fragment_key === topic.fragment_key) ? '待审核' : '已确认' }}</span>
              <p>{{ topic.task }}</p>
            </li>
          </ul>
          <p>{{ completionGate.sop_contract.missing_information_policy }}</p>
        </details>
      </section>

      <div class="node-workspace-columns">
        <section class="node-inputs" aria-label="当前节点分析依据">
          <div class="node-section-heading">
            <h4>本阶段可以依据这些信息</h4>
            <VanButton class="node-link-button" type="default" plain native-type="button" @click="$emit('to-section', 'case-context')">查看完整申请资料</VanButton>
          </div>
          <p class="node-input-guidance">{{ stage.inputGuidance }}</p>
          <div class="node-input-groups">
            <article v-for="group in inputGroups" :key="group.key" class="node-input-group">
              <h5>{{ group.title }}</h5>
              <p v-if="group.reason" class="node-input-reason">{{ group.reason }}</p>
              <div v-if="group.items.length" class="node-material-list">
                <article v-for="item in group.items" :key="item.key || item.title" class="node-material-item">
                  <div class="node-material-heading">
                    <strong>{{ item.title }}</strong>
                    <span v-if="item.meta">{{ item.meta }}</span>
                  </div>
                  <p>{{ item.body }}</p>
                  <small v-if="item.source">{{ item.source }}</small>
                </article>
              </div>
              <p v-else class="node-input-empty">{{ group.empty }}</p>
            </article>
          </div>
        </section>

        <section class="node-tools" aria-label="当前步骤的操作与核对事项">
          <div class="node-section-heading"><h4>可用工具</h4></div>
          <div class="node-tool-list">
            <template v-for="tool in stage.tools" :key="tool.section">
              <VanButton
                v-if="stepViewMode === 'CURRENT'"
                class="node-link-button node-tool-button"
                type="default"
                plain
                native-type="button"
                @click="$emit('to-section', tool.section)"
              >
                {{ tool.label }}
              </VanButton>
              <span v-else class="node-tool-static">{{ tool.label }}</span>
            </template>
          </div>
          <div class="node-checklist">
            <h5>完成前逐项确认</h5>
            <ul>
              <li v-for="item in stage.checklist" :key="item">{{ item }}</li>
            </ul>
          </div>
        </section>
      </div>

      <section class="node-stage-results" aria-label="本阶段审核结果">
        <div class="node-section-heading"><h4>本阶段建议与审核结果</h4></div>
        <div v-if="stageOutputItems.length" class="node-material-list">
          <article v-for="item in stageOutputItems" :key="item.key || item.title" class="node-material-item">
            <div class="node-material-heading">
              <strong>{{ item.title }}</strong>
              <span v-if="item.meta">{{ item.meta }}</span>
            </div>
            <p>{{ item.body }}</p>
            <small v-if="item.source">{{ item.source }}</small>
          </article>
        </div>
        <p v-else class="node-input-empty">{{ stage.outputEmpty }}</p>
      </section>

      <div v-if="isHistoricalView || isUpcomingView" class="node-history-note" :class="{ 'node-upcoming-note': isUpcomingView }" role="status">
        <strong>{{ isUpcomingView ? '后续步骤预览' : '历史记录（只读）' }}</strong>
        <span v-if="isUpcomingView">目前还不能处理这一步；请先完成前面的节点。</span>
        <span v-else-if="currentStep">当前待处理的是第 {{ currentStep.sequence_no }} 步 · {{ stageFor(currentStep.step_key)?.name }}。</span>
        <span v-else>报告流程已结束；这里保留了本步骤当时的输入和审核结果。</span>
        <VanButton
          v-if="currentStep"
          class="node-link-button node-return-current"
          type="default"
          plain
          native-type="button"
          @click="returnToCurrentStep"
        >
          回到当前待办
        </VanButton>
      </div>

      <div
        v-if="stepViewMode === 'CURRENT' && completionGate && ['S1', 'S2', 'S3', 'S4'].includes(currentStep.step_key)"
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
          v-if="stepViewMode === 'CURRENT' && currentStep?.status === 'READY'"
          class="primary-button compact-button"
          type="primary"
          native-type="button"
          :disabled="loading"
          :loading="loading"
          @click="$emit('start-step')"
        >
          开始本节点
        </VanButton>
        <template v-else-if="stepViewMode === 'CURRENT' && currentStep?.status === 'IN_REVIEW'">
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
        <span v-else-if="stepViewMode === 'CURRENT' && ['EXECUTING', 'WAITING_REVIEW'].includes(currentStep?.status)" class="node-running-state">
          {{ statusLabel(currentStep.status) }}，内容完成后可在对应页面继续处理。
        </span>
      </footer>
    </div>
    <div v-else-if="!viewStep || !stage" class="workflow-finished-state" :class="`workflow-finished-${String(reportCase.status || '').toLowerCase()}`">
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
import {
  buildWorkbenchInputGroups,
  buildWorkbenchStageOutputs,
  classifyWorkbenchStepView,
  qualitySummaryLabel
} from '../workbench-inputs.js'

export default {
  name: 'ReportNodeWorkbench',
  components: { VanButton },
  data() {
    return { selectedStepKey: null }
  },
  props: {
    reportCase: { type: Object, required: true },
    compact: { type: Boolean, default: false },
    content: { type: Object, required: true },
    currentStep: { type: Object, default: null },
    qualityStatus: { type: String, default: '' },
    narrativePlanStatus: { type: String, default: '' },
    latestAnalysisRun: { type: Object, default: null },
    analysisRuns: { type: Array, default: () => [] },
    narrativePlan: { type: Object, default: null },
    quality: { type: Object, default: () => ({}) },
    completionGate: { type: Object, default: null },
    qualityIssueCount: { type: Number, default: 0 },
    qualityBlockingCount: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
    analysisSaving: { type: Boolean, default: false },
    canReopen: { type: Boolean, default: false }
  },
  emits: ['start-step', 'complete-step', 'toggle-return', 'to-section', 'run-analysis', 'reopen'],
  watch: {
    'currentStep.step_key'(next, previous) {
      if (next !== previous) this.selectedStepKey = null
    }
  },
  computed: {
    viewStep() {
      return this.workflowSteps.find(step => step.step_key === this.selectedStepKey) || this.currentStep
    },
    isHistoricalView() {
      return this.stepViewMode === 'HISTORY'
    },
    isUpcomingView() {
      return this.stepViewMode === 'UPCOMING'
    },
    stepViewMode() {
      return classifyWorkbenchStepView(this.viewStep, this.currentStep)
    },
    stage() {
      return this.viewStep ? reportStage(this.viewStep.step_key) : null
    },
    currentStage() {
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
    inputGroups() {
      return buildWorkbenchInputGroups({
        stage: this.stage,
        reportCase: this.reportCase,
        content: this.content,
        narrativePlan: this.narrativePlan,
        quality: this.quality
      })
    },
    currentInputGroups() {
      return buildWorkbenchInputGroups({
        stage: this.currentStage,
        reportCase: this.reportCase,
        content: this.content,
        narrativePlan: this.narrativePlan,
        quality: this.quality
      })
    },
    compactInputSummary() {
      if (!this.currentInputGroups.length) return '当前节点暂无可用输入'
      return this.currentInputGroups
        .map(group => `${group.title}（${group.items.length ? `${group.items.length}项` : '暂无资料'}）`)
        .join('、')
    },
    stageOutputItems() {
      return buildWorkbenchStageOutputs({
        stage: this.stage,
        reportCase: this.reportCase,
        content: this.content,
        narrativePlan: this.narrativePlan,
        quality: this.quality,
        analysisRuns: this.analysisRuns
      })
    },
    confirmedFindingCount() {
      return (this.content.findings || []).filter(item => item.status === 'CONFIRMED').length
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
          label: '分析输入',
          value: this.activeEvidence.length ? '资料已留存' : '等待系统测算',
          note: '用户档案、申请情境与可追溯依据'
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
      if (this.compact && this.currentStep) {
        return `当前待处理：第 ${this.currentStep.sequence_no} 步 / 共 ${this.workflowSteps.length} 步 · ${this.currentStage?.shortName || ''}`
      }
      if (this.viewStep) return `第 ${this.viewStep.sequence_no} 步 / 共 ${this.workflowSteps.length} 步 · ${this.stage?.shortName || ''}`
      return this.reportCase.status === 'DELIVERED'
        ? '报告已交付'
        : this.reportCase.status === 'READY_TO_DELIVER'
          ? '六步处理和最终复核已完成'
          : '内容处理步骤已完成'
    },
    progressDescription() {
      if (this.isUpcomingView) return `${this.stage?.name || '后续步骤'}尚未开放；请先完成当前待办。`
      if (this.isHistoricalView) return `正在查看第 ${this.viewStep.sequence_no} 步的输入与审核结果；实际待办不会改变。`
      if (!this.currentStep && this.viewStep) return `报告流程已结束，正在查看第 ${this.viewStep.sequence_no} 步的历史记录。`
      if (this.currentStep) return `${this.stage?.name || '当前步骤'}是目前需要处理的部分；完成后会进入下一步。`
      if (this.reportCase.status === 'DELIVERED') return '所有处理步骤和最终交付均已完成。'
      if (this.reportCase.status === 'READY_TO_DELIVER') return '报告已通过最终复核，请进入交付前检查生成交付版本。'
      return '当前没有待处理的工作步骤。'
    },
    nextAction() {
      if (this.isUpcomingView) return '先完成当前待办，这个步骤之后会自动开放。'
      if (this.isHistoricalView) return '查看该节点当时参考的资料和已保存结果。'
      if (!this.currentStep && this.viewStep) return '报告流程已结束，可从上方选择其他节点查看历史输入和审核结果。'
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
        S3: '只整合前两步已确认的内容，核对彼此支持或冲突的地方。',
        S4: '结合具体情境理解应对方式，再整理可执行、可调整的行动。',
        S5: '先确认报告主线，再生成报告内容并逐段审阅。',
        S6: '先运行交付前检查，处理问题后再完成最终复核。'
      }[this.currentStep.step_key] || '查看本步骤建议和相关资料，完成审核后再继续。'
    },
    qualityStatusLabel() {
      return qualitySummaryLabel(this.quality, this.qualityStatus)
    }
  },
  methods: {
    selectStep(step) {
      this.selectedStepKey = step.id === this.currentStep?.id || this.selectedStepKey === step.step_key
        ? null
        : step.step_key
    },
    returnToCurrentStep() {
      this.selectedStepKey = null
    },
    gateBlockerLabel(code) {
      return {
        report_analysis_output_required: '至少需要确认一条专业判断或一段分析内容。',
        report_analysis_sop_coverage_required: '分析清单仍有未确认条目；缺少资料时请记录暂缓原因并审核。',
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
