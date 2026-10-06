<template>
  <section class="analysis-drafts-panel" aria-label="本节点 AI 分析">
    <div class="analysis-drafts-heading">
      <div>
        <p class="eyebrow">节点工作流程 · AI 分析</p>
        <h3>AI 分析</h3>
      </div>
      <span>{{ stageRuns.length }} 份建议记录</span>
    </div>
    <p class="analysis-drafts-notice">以下是 AI 生成的候选判断与分析，不是用户事实，也不是已确认结论。请对照标出的原始资料依据审核；只有你确认后，内容才会用于后续报告。</p>

    <div v-if="!stageRuns.length" class="analysis-drafts-empty">
      还没有 AI 分析结果。核对上游输入{{ stepKey === 'S1' ? '和程序计算' : '及前序已确认内容' }}后，可以运行分析并生成候选判断与分析内容。
    </div>

    <label v-if="stageRuns.length" class="analysis-run-select">AI 分析记录<select v-model="activeRunId" :disabled="reviewBusy || saving"><option v-for="(record, index) in stageRuns" :key="record.id" :value="String(record.id)">记录 {{ stageRuns.length - index }} · {{ formatDate(record.created_at) }} · {{ runStatusLabel(record.status) }}</option></select></label>
    <form v-if="!readOnly && currentStep" class="analysis-feedback" @submit.prevent="submitAnalysis">
      <label for="analysis-feedback">分析要求或本次调整意见</label>
      <p v-if="!analysisReady" class="analysis-prerequisite-note">请先完成程序计算并核对结果，再开始 S1 分析。</p>
      <VanButton v-if="!analysisReady" class="secondary-button compact-button" plain native-type="button" @click="$emit('go-calculation')">前往程序计算</VanButton>
      <VanField
        id="analysis-feedback"
        v-model="feedbackText"
        class="analysis-feedback-field"
        type="textarea"
        rows="3"
        autosize
        maxlength="4000"
        show-word-limit
        :disabled="feedbackSaving || feedbackDisabled || reviewBusy"
        placeholder="可留空直接运行。也可以说明需要关注的资料、希望澄清的判断或上一版需要调整的地方。"
      />
      <div class="analysis-feedback-actions">
        <small>运行结果只作为待审核候选；需要由你确认后才会传给后续节点。</small>
        <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="feedbackSaving || feedbackDisabled || reviewBusy || !analysisReady" :loading="feedbackSaving">
          {{ feedbackSaving ? '正在生成分析' : feedbackText.trim() ? '提交要求并运行 AI 分析' : stageRuns.length ? '重新运行 AI 分析' : '运行 AI 分析' }}
        </VanButton>
      </div>
    </form>
    <article v-for="run in visibleRuns" :key="run.id" class="analysis-run">
      <header class="analysis-run-header">
        <div>
          <strong>AI 分析结果</strong>
          <span class="analysis-run-state" :class="`run-${String(run.status).toLowerCase()}`">{{ runStatusLabel(run.status) }}</span>
          <small v-if="run.context_snapshot?.analysis_feedback_source_run_id">根据运行记录 {{ run.context_snapshot.analysis_feedback_source_run_id }} 的结果重跑</small>
        </div>
        <small v-if="run.created_at">生成于 {{ formatDate(run.created_at) }}</small>
      </header>

      <details v-if="run.runtime_instruction" class="analysis-run-feedback">
        <summary>本次咨询师反馈</summary>
        <p>{{ run.runtime_instruction }}</p>
      </details>

      <p v-if="run.status === 'FAILED'" class="analysis-run-error" role="alert">建议暂时无法生成，请稍后重试。{{ friendlyError(run.error) }}</p>
      <div v-else-if="['PENDING', 'RUNNING'].includes(run.status)" class="analysis-run-pending" role="status">
        {{ run.status === 'PENDING' ? '正在准备分析建议…' : '正在生成分析建议…' }}
      </div>
      <template v-else-if="run.status === 'COMPLETED' && run.output_parsed">
        <details class="analysis-run-context"><summary>生成摘要与注意事项 · {{ run.output_parsed.risk_flags?.length || 0 }} 项提示</summary>
        <p class="analysis-run-summary">{{ consultantText(run.output_parsed.summary, '分析建议已生成，请查看下方内容并结合资料审核。') }}</p>
        <div v-if="run.output_parsed.risk_flags?.length" class="analysis-risk-list">
          <strong>需要留意</strong>
          <p v-for="(flag, index) in run.output_parsed.risk_flags" :key="`${run.id}-risk-${index}`">
            {{ consultantText(flag.message, '这项建议需要结合资料进一步核对。') }}<small v-if="flag.references?.length">依据：{{ referenceLabels(flag.references) }}</small>
          </p>
        </div>

        </details>
        <AnalysisDirectionReview
          :key="run.id" :run="run" :content="content" :step-id="currentStepId"
          :read-only="readOnly" :saving="saving" :sources-current="candidateSourcesCurrent"
          @review-candidate="$emit('review-candidate', $event)" @busy="reviewBusy = $event; $emit('busy', $event)"
          @go-overview="$emit('go-overview')"
        />
        <p v-if="!run.output_parsed.findings?.length && !run.output_parsed.analysis_fragments?.length" class="analysis-drafts-empty">暂无可审核的候选，请调整分析要求后重试。</p>
      </template>
    </article>
  </section>
</template>

<script>
import { Button as VanButton, Field as VanField } from 'vant'
import AnalysisDirectionReview from './AnalysisDirectionReview.vue'
import { currentReportFoundation, reportEvidenceTitle } from '../workbench-inputs.js'
import { formatDate } from '../../service-requests/formatters.js'

export default {
  name: 'AnalysisDraftsPanel',
  components: { VanButton, VanField, AnalysisDirectionReview },
  data: () => ({ selectedRunId: '', feedbackText: '', reviewBusy: false }),
  beforeUnmount() { this.$emit('busy', false) },
  props: {
    readOnly: Boolean,
    runs: { type: Array, default: () => [] },
    content: { type: Object, required: true },
    stepKey: { type: String, default: '' },
    currentStep: { type: Object, default: null },
    saving: { type: Boolean, default: false },
    feedbackSaving: { type: Boolean, default: false },
    feedbackDisabled: { type: Boolean, default: false },
    analysisReady: { type: Boolean, default: true }
  },
  emits: ['review-candidate', 'go-overview', 'run-analysis', 'go-calculation', 'busy'],
  methods: {
    formatDate,
    submitAnalysis() {
      const feedback = this.feedbackText.trim()
      if (this.readOnly || !this.currentStep || this.feedbackSaving || this.reviewBusy || !this.analysisReady) return
      const latestRun = this.visibleRuns[0]
      const sourceRunId = latestRun?.status === 'COMPLETED'
        && this.candidateSourcesCurrent(latestRun, { evidence_refs: [] })
        ? latestRun.id
        : null
      this.$emit('run-analysis', feedback ? {
        runtimeInstruction: feedback,
        sourceRunId
      } : null)
    },
    runStatusLabel(status) {
      return { PENDING: '正在准备', RUNNING: '正在生成', COMPLETED: '已生成', FAILED: '暂时失败' }[status] || '处理中'
    },
    friendlyError(error) {
      if (!error || !/^[a-z][a-z0-9_]+$/.test(String(error))) return ''
      return ' 请刷新页面后重试；如仍无法完成，请联系管理员。'
    },
    consultantText(value, fallback = '请结合相关资料进一步核对。') {
      const text = String(value || '').trim()
      return text && /[\u3400-\u9fff]/.test(text) ? text : fallback
    },
    evidenceLabel(key) {
      const evidence = (this.content.evidence || []).find(item => item.evidence_key === key)
      if (!evidence) return '相关资料依据'
      return reportEvidenceTitle(evidence)
    },
    referenceLabels(keys) {
      return [...new Set((keys || []).map(key => this.evidenceLabel(key)))].join('、')
    },
    candidateSourcesCurrent(run, candidate) {
      const evidence = this.content.evidence || []
      if ((candidate.evidence_refs || []).some(key => !evidence.some(item => item.evidence_key === key && item.status === 'ACTIVE'))) return false
      if (this.stepKey === 'S1') {
        const runFoundation = (run.input_snapshot?.analysis_context?.evidence || []).find(item =>
          ['SYSTEM_CALCULATED', 'CONSULTANT_CORRECTED'].includes(item.source_type)
          && (String(item.evidence_key || '').startsWith('calculated.mingli_foundation.v2')
            || String(item.evidence_key || '').startsWith('calculated.mingli_foundation.consultant.'))
          && item.value?.calculation_version === 'mingli-v2'
        )
        const currentFoundation = currentReportFoundation(evidence)
        if (runFoundation && currentFoundation?.evidence_key !== runFoundation.evidence_key) return false
      }
      return true
    },

  },
  computed: {
    activeRunId: { get() { return String(this.visibleRuns[0]?.id || '') }, set(value) { this.selectedRunId=value } },
    visibleRuns() { const run = this.stageRuns.find(item => String(item.id) === this.selectedRunId) || this.stageRuns[0]; return run ? [run] : [] },
    stageRuns() {
      return this.runs
        .filter(run => !this.currentStep || run.context_snapshot?.analysis_activation_no === this.currentStep.activation_no)
        .filter(run => run.target_type === 'REPORT_ANALYSIS_DRAFT' && run.target_key === this.stepKey)
        .sort((left, right) => right.id - left.id)
    },
    currentStepId() {
      return this.currentStep?.id || null
    }
  }
}
</script>

<style scoped src="./AnalysisDraftsPanel.css"></style>
