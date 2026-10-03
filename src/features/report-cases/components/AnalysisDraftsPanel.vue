<template>
  <section class="analysis-drafts-panel" aria-label="分析建议与审核">
    <div class="analysis-drafts-heading">
      <div>
        <p class="eyebrow">本步骤的辅助建议</p>
        <h4>建议内容与人工审核</h4>
      </div>
      <span>{{ stageRuns.length }} 份建议记录</span>
    </div>
    <p class="analysis-drafts-notice">以下内容仅供参考。只有经过你审核并确认后，才会用于后续报告。</p>

    <div v-if="!stageRuns.length" class="analysis-drafts-empty">
      还没有本步骤的建议。开始处理后，可以生成一份基于用户情境和前序已确认内容的参考意见。
    </div>

    <article v-for="run in stageRuns" :key="run.id" class="analysis-run">
      <header class="analysis-run-header">
        <div>
          <strong>分析建议</strong>
          <span class="analysis-run-state" :class="`run-${String(run.status).toLowerCase()}`">{{ runStatusLabel(run.status) }}</span>
        </div>
        <small v-if="run.created_at">生成于 {{ formatDate(run.created_at) }}</small>
      </header>

      <p v-if="run.status === 'FAILED'" class="analysis-run-error" role="alert">建议暂时无法生成，请稍后重试。{{ friendlyError(run.error) }}</p>
      <div v-else-if="['PENDING', 'RUNNING'].includes(run.status)" class="analysis-run-pending" role="status">
        {{ run.status === 'PENDING' ? '正在准备分析建议…' : '正在生成分析建议…' }}
      </div>
      <template v-else-if="run.status === 'COMPLETED' && run.output_parsed">
        <p class="analysis-run-summary">{{ consultantText(run.output_parsed.summary, '分析建议已生成，请查看下方内容并结合资料审核。') }}</p>
        <div v-if="run.output_parsed.risk_flags?.length" class="analysis-risk-list">
          <strong>需要留意</strong>
          <p v-for="(flag, index) in run.output_parsed.risk_flags" :key="`${run.id}-risk-${index}`">
            {{ consultantText(flag.message, '这项建议需要结合资料进一步核对。') }}<small v-if="flag.references?.length">依据：{{ referenceLabels(flag.references) }}</small>
          </p>
        </div>

        <div v-if="run.output_parsed.findings?.length" class="analysis-candidate-group">
          <h5>候选专业判断 · {{ run.output_parsed.findings.length }}</h5>
          <article v-for="candidate in run.output_parsed.findings" :key="candidate.finding_key" class="analysis-candidate">
            <div class="analysis-candidate-title">
              <strong>{{ candidate.kind === 'SIGNAL' ? '待验证线索' : '专业判断建议' }}</strong>
              <span>{{ candidate.kind === 'SIGNAL' ? '需要更多资料验证' : '需要咨询师审核' }}</span>
            </div>
            <p>{{ consultantText(candidate.claim, '这条建议暂时无法用中文展示，请重新生成后再审核。') }}</p>
            <div class="analysis-candidate-meta">
              <span>{{ semanticRoleLabel(candidate.semantic_role) }}</span>
              <span>把握程度：{{ confidenceLabel(candidate.confidence) }}</span>
              <span>参考优先级：{{ importanceLabel(candidate.importance) }}</span>
            </div>
            <small class="analysis-candidate-source">参考了 {{ candidate.evidence_refs?.length || 0 }} 项资料依据<template v-if="candidate.relation_refs?.length">，并结合 {{ candidate.relation_refs.length }} 条前序判断</template></small>
            <details v-if="candidate.evidence_refs?.length" class="analysis-candidate-details">
              <summary>查看参考资料</summary>
              <ul><li v-for="key in candidate.evidence_refs" :key="key">{{ evidenceLabel(key) }}</li></ul>
            </details>
            <div class="analysis-candidate-action">
              <span v-if="isAppliedFinding(run, candidate)" class="analysis-applied-state">已加入待审核判断</span>
              <span v-else-if="hasForeignFindingOwner(candidate)" class="analysis-blocked-state">前序步骤已有相同判断，请查看已确认内容，避免重复添加。</span>
              <span v-else-if="!consultantText(candidate.claim, '')" class="analysis-blocked-state">这条建议暂时无法用中文展示，请重新生成后再审核。</span>
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
                {{ currentFinding(candidate.finding_key) ? '更新为待审核版本' : '加入待审核判断' }}
              </VanButton>
            </div>
          </article>
        </div>

        <div v-if="run.output_parsed.analysis_fragments?.length" class="analysis-candidate-group">
          <h5>候选分析片段 · {{ run.output_parsed.analysis_fragments.length }}</h5>
          <article v-for="candidate in run.output_parsed.analysis_fragments" :key="candidate.fragment_key" class="analysis-candidate analysis-fragment-candidate">
            <div class="analysis-candidate-title"><strong>{{ consultantText(candidate.title, '分析内容建议') }}</strong><span>报告内容</span></div>
            <p>{{ consultantText(candidate.content, '这段建议暂时无法用中文展示，请重新生成后再审核。') }}</p>
            <small class="analysis-candidate-source">关联 {{ candidate.finding_refs?.length || 0 }} 条已确认判断和 {{ candidate.evidence_refs?.length || 0 }} 项资料依据</small>
            <div class="analysis-candidate-action">
              <span v-if="isAppliedFragment(run, candidate)" class="analysis-applied-state">已加入待审核内容</span>
              <span v-else-if="missingFragmentFindings(candidate).length" class="analysis-blocked-state">需先审核相关专业判断，再加入这段内容。</span>
              <span v-else-if="hasForeignFragmentOwner(candidate)" class="analysis-blocked-state">前序步骤已有相同内容，请查看原有内容，避免重复添加。</span>
              <span v-else-if="!consultantText(candidate.content, '')" class="analysis-blocked-state">这段建议暂时无法用中文展示，请重新生成后再审核。</span>
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
                {{ currentFragment(candidate.fragment_key) ? '更新待审核内容' : '加入待审核内容' }}
              </VanButton>
            </div>
          </article>
        </div>

        <p v-if="!run.output_parsed.findings?.length && !run.output_parsed.analysis_fragments?.length" class="analysis-drafts-empty">
          暂无可供审核的判断或报告内容。请查看提示，或调整处理要求后重试。
        </p>
      </template>
    </article>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import { reportEvidenceTitle } from '../workbench-inputs.js'
import { formatDate } from '../../service-requests/formatters.js'

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
    formatDate,
    runStatusLabel(status) {
      return { PENDING: '正在准备', RUNNING: '正在生成', COMPLETED: '已生成', FAILED: '暂时失败' }[status] || '处理中'
    },
    friendlyError(error) {
      if (!error || !/^[a-z][a-z0-9_]+$/.test(String(error))) return ''
      return ' 请刷新页面后重试；如仍无法完成，请联系管理员。'
    },
    consultantText(value, fallback = '请结合相关资料进一步核对。') {
      const text = String(value || '').trim()
      return text && !/[A-Za-z]{2,}/.test(text) ? text : fallback
    },
    semanticRoleLabel(role) {
      return {
        STRENGTH: '优势', CHALLENGE: '需要留意', CONFLICT: '内在矛盾', PATTERN: '行为模式',
        OBSERVATION: '观察', SIGNAL: '待验证线索', THEME: '核心主题', ACTION: '行动方向'
      }[role] || '综合观察'
    },
    confidenceLabel(value) {
      return { LOW: '较低', MEDIUM: '一般', HIGH: '较高' }[value] || '一般'
    },
    importanceLabel(value) {
      return { LOW: '普通', MEDIUM: '关注', HIGH: '重要', CRITICAL: '优先处理' }[value] || '普通'
    },
    evidenceLabel(key) {
      const evidence = (this.content.evidence || []).find(item => item.evidence_key === key)
      if (!evidence) return '相关资料依据'
      return reportEvidenceTitle(evidence)
    },
    referenceLabels(keys) {
      return [...new Set((keys || []).map(key => this.evidenceLabel(key)))].join('、')
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
