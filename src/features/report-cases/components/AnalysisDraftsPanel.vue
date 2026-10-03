<template>
  <section class="analysis-drafts-panel" aria-label="AI 分析草稿与候选审核">
    <div class="analysis-drafts-heading">
      <div>
        <p class="eyebrow">AI ANALYSIS / HUMAN REVIEW</p>
        <h4>分析草稿与候选判断</h4>
      </div>
      <span>{{ stageRuns.length }} 次运行</span>
    </div>
    <p class="analysis-drafts-notice">AI 输出只作为内部候选。应用后仍是待审核版本，不会自动成为已确认语义或报告内容。</p>

    <div v-if="!stageRuns.length" class="analysis-drafts-empty">
      尚无此节点的分析运行。开始审核后，可生成一份基于当前情境和上游确认材料的草稿。
    </div>

    <article v-for="run in stageRuns" :key="run.id" class="analysis-run">
      <header class="analysis-run-header">
        <div>
          <strong>运行 #{{ run.id }}</strong>
          <span class="analysis-run-state" :class="`run-${String(run.status).toLowerCase()}`">{{ runStatusLabel(run.status) }}</span>
        </div>
        <small>{{ run.model_trace?.model || run.model_trace?.provider || 'DeepSeek' }}<template v-if="run.created_at"> · {{ formatDate(run.created_at) }}</template></small>
      </header>

      <p v-if="run.status === 'FAILED'" class="analysis-run-error" role="alert">运行失败：{{ run.error || '请检查模型配置后重试。' }}</p>
      <div v-else-if="['PENDING', 'RUNNING'].includes(run.status)" class="analysis-run-pending" role="status">
        {{ run.status === 'PENDING' ? '等待模型处理…' : '模型正在生成分析候选…' }}
      </div>
      <template v-else-if="run.status === 'COMPLETED' && run.output_parsed">
        <p class="analysis-run-summary">{{ run.output_parsed.summary }}</p>
        <div v-if="run.output_parsed.risk_flags?.length" class="analysis-risk-list">
          <strong>需要留意</strong>
          <p v-for="(flag, index) in run.output_parsed.risk_flags" :key="`${run.id}-risk-${index}`">
            {{ flag.message }}<small v-if="flag.references?.length">依据：{{ flag.references.join('、') }}</small>
          </p>
        </div>

        <div v-if="run.output_parsed.findings?.length" class="analysis-candidate-group">
          <h5>候选专业判断 · {{ run.output_parsed.findings.length }}</h5>
          <article v-for="candidate in run.output_parsed.findings" :key="candidate.finding_key" class="analysis-candidate">
            <div class="analysis-candidate-title">
              <strong>{{ candidate.finding_key }}</strong>
              <span>{{ candidate.kind === 'SIGNAL' ? '待验证 Signal' : 'Finding 候选' }}</span>
            </div>
            <p>{{ candidate.claim }}</p>
            <div class="analysis-candidate-meta">
              <span>{{ candidate.semantic_role }}</span>
              <span>置信度 {{ candidate.confidence }}</span>
              <span>重要度 {{ candidate.importance }}</span>
            </div>
            <small class="analysis-candidate-source">Evidence：{{ candidate.evidence_refs?.join('、') || '无' }}</small>
            <small v-if="candidate.relation_refs?.length" class="analysis-candidate-source">
              上游判断：{{ candidate.relation_refs.map(item => typeof item === 'string' ? item : `${item.finding_key} · ${item.relation || 'RELATED'}`).join('、') }}
            </small>
            <details v-if="Object.keys(candidate.structured_data || {}).length" class="analysis-candidate-details">
              <summary>查看结构化分析</summary>
              <pre>{{ pretty(candidate.structured_data) }}</pre>
            </details>
            <div class="analysis-candidate-action">
              <span v-if="isAppliedFinding(run, candidate)" class="analysis-applied-state">已加入待审核 Finding</span>
              <span v-else-if="hasForeignFindingOwner(candidate)" class="analysis-blocked-state">同标识内容属于上游节点，请修改候选标识后再新增</span>
              <VanButton
                v-else
                class="secondary-button compact-button"
                type="default"
                plain
                native-type="button"
                :disabled="saving"
                :loading="savingFindingKey === `${run.id}:${candidate.finding_key}`"
                @click="$emit('apply-finding', { run, candidate, expectedRevisionNo: currentFinding(candidate.finding_key)?.revision_no ?? null })"
              >
                {{ currentFinding(candidate.finding_key) ? '应用为新待审核版本' : '加入待审核 Finding' }}
              </VanButton>
            </div>
          </article>
        </div>

        <div v-if="run.output_parsed.analysis_fragments?.length" class="analysis-candidate-group">
          <h5>候选分析片段 · {{ run.output_parsed.analysis_fragments.length }}</h5>
          <article v-for="candidate in run.output_parsed.analysis_fragments" :key="candidate.fragment_key" class="analysis-candidate analysis-fragment-candidate">
            <div class="analysis-candidate-title"><strong>{{ candidate.title || candidate.fragment_key }}</strong><span>{{ candidate.fragment_key }}</span></div>
            <p>{{ candidate.content }}</p>
            <small class="analysis-candidate-source">Finding：{{ candidate.finding_refs?.join('、') || '无' }} · Evidence：{{ candidate.evidence_refs?.join('、') || '无' }}</small>
            <div class="analysis-candidate-action">
              <span v-if="isAppliedFragment(run, candidate)" class="analysis-applied-state">已加入待审核片段</span>
              <span v-else-if="missingFragmentFindings(candidate).length" class="analysis-blocked-state">先应用关联 Finding：{{ missingFragmentFindings(candidate).join('、') }}</span>
              <span v-else-if="hasForeignFragmentOwner(candidate)" class="analysis-blocked-state">同标识片段属于上游节点，请修改候选标识后再新增</span>
              <VanButton
                v-else
                class="secondary-button compact-button"
                type="default"
                plain
                native-type="button"
                :disabled="saving"
                :loading="savingFragmentKey === `${run.id}:${candidate.fragment_key}`"
                @click="$emit('apply-fragment', { run, candidate, expectedRevisionNo: currentFragment(candidate.fragment_key)?.revision_no ?? null })"
              >
                {{ currentFragment(candidate.fragment_key) ? '应用为新待审核版本' : '加入待审核片段' }}
              </VanButton>
            </div>
          </article>
        </div>

        <p v-if="!run.output_parsed.findings?.length && !run.output_parsed.analysis_fragments?.length" class="analysis-drafts-empty">
          运行未返回可应用的判断或分析片段。请查看风险提示，或调整本次运行要求后重试。
        </p>
      </template>
    </article>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import { prettyJson, formatDate } from '../../service-requests/formatters.js'

export default {
  name: 'AnalysisDraftsPanel',
  components: { VanButton },
  props: {
    runs: { type: Array, default: () => [] },
    content: { type: Object, required: true },
    stepKey: { type: String, default: '' },
    currentStep: { type: Object, default: null },
    saving: { type: Boolean, default: false },
    savingFindingKey: { type: String, default: '' },
    savingFragmentKey: { type: String, default: '' }
  },
  emits: ['apply-finding', 'apply-fragment'],
  methods: {
    pretty: prettyJson,
    formatDate,
    runStatusLabel(status) {
      return { PENDING: '排队中', RUNNING: '生成中', COMPLETED: '已完成', FAILED: '失败' }[status] || status
    },
    currentFinding(key) {
      return (this.content.findings || []).find(item => item.finding_key === key) || null
    },
    currentFragment(key) {
      return (this.content.fragments || []).find(item => item.fragment_key === key) || null
    },
    isAppliedFinding(run, candidate) {
      return this.currentFinding(candidate.finding_key)?.source_skill_run_id === run.id
    },
    isAppliedFragment(run, candidate) {
      return this.currentFragment(candidate.fragment_key)?.source_skill_run_id === run.id
    },
    hasForeignFindingOwner(candidate) {
      const current = this.currentFinding(candidate.finding_key)
      return Boolean(current?.owner_step_task_id && current.owner_step_task_id !== this.currentStepId)
    },
    hasForeignFragmentOwner(candidate) {
      const current = this.currentFragment(candidate.fragment_key)
      return Boolean(current?.owner_step_task_id && current.owner_step_task_id !== this.currentStepId)
    },
    missingFragmentFindings(candidate) {
      return (candidate.finding_refs || []).filter(key => !this.currentFinding(key))
    }
  },
  computed: {
    stageRuns() {
      return this.runs
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
