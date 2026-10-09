<template>
  <section class="direction-review" aria-label="AI 分析候选整体纳入">
    <header class="direction-review-heading">
      <div>
        <h4>本次 AI 候选</h4>
        <p>完整查看判断、分析和来源后，可一次加入本节点待审内容。纳入不会自动确认；之后分别在判断和分析阶段整体审阅。</p>
      </div>
      <span role="status">{{ findingCandidates.length }} 条判断 · {{ fragmentCandidates.length }} 段分析</span>
    </header>

    <p v-if="error" ref="error" class="review-error" role="alert" tabindex="-1">{{ error }}</p>
    <p v-if="notice" class="review-note" role="status" aria-live="polite">{{ notice }}</p>

    <section v-if="findingCandidates.length" class="review-candidate-group" aria-labelledby="candidate-findings-title">
      <header class="review-candidate-heading">
        <h5 id="candidate-findings-title">候选判断</h5>
        <span>{{ pendingFindingCount }} 条待纳入</span>
      </header>
      <article v-for="candidate in findingCandidates" :key="candidate.finding_key" class="review-candidate-row">
        <div class="review-candidate-title">
          <h6>{{ findingReviewTitle(candidate) }}</h6>
          <span>{{ candidateState(candidate, 'finding') }}</span>
        </div>
        <p class="review-prose">{{ candidate.claim }}</p>
        <p class="review-note">
          {{ displayText(candidate.kind) }} · {{ displayText(candidate.semantic_role, 'semantic_role') }} ·
          {{ displayText(candidate.confidence) }}把握 · 重要度 {{ displayText(candidate.importance) }} ·
          {{ displayText(candidate.reportability) }}
        </p>
        <details v-if="evidenceRecords(candidate.evidence_refs).length || candidate.relation_refs?.length" class="review-source-details">
          <summary>查看判断来源</summary>
          <div v-for="item in evidenceRecords(candidate.evidence_refs)" :key="item.evidence_key" class="review-source-item">
            <strong>{{ evidenceLabel(item.evidence_key) }}</strong>
            <p>{{ evidenceSummary(item) }}</p>
            <small v-if="item.status !== 'ACTIVE'" class="review-source-stale">来源已更新、撤回或无法找到。</small>
          </div>
          <div v-for="ref in candidate.relation_refs || []" :key="relationKey(ref)" class="review-source-item">
            <strong>关联判断 · {{ findingLabel(relationKey(ref)) }}</strong>
          </div>
        </details>
        <p v-else class="review-warning">此判断没有可核对的来源，将无法加入待审内容。</p>
      </article>
    </section>

    <section v-if="fragmentCandidates.length" class="review-candidate-group" aria-labelledby="candidate-analysis-title">
      <header class="review-candidate-heading">
        <h5 id="candidate-analysis-title">候选分析内容</h5>
        <span>{{ pendingFragmentCount }} 段待纳入</span>
      </header>
      <article v-for="candidate in fragmentCandidates" :key="candidate.fragment_key" class="review-candidate-row">
        <div class="review-candidate-title">
          <h6>{{ candidate.title || candidate.fragment_key }}</h6>
          <span>{{ candidateState(candidate, 'fragment') }}</span>
        </div>
        <p class="review-prose">{{ candidate.content }}</p>
        <p class="review-note">
          关联判断：{{ (candidate.finding_refs || []).map(findingLabel).join('、') || '直接依据原始资料分析' }}
        </p>
        <details class="review-source-details">
          <summary>查看原始资料依据、覆盖说明与推导记录</summary>
          <div v-for="item in evidenceRecords(candidate.evidence_refs)" :key="item.evidence_key" class="review-source-item">
            <strong>{{ evidenceLabel(item.evidence_key) }}</strong>
            <p>{{ evidenceSummary(item) }}</p>
            <small v-if="item.status !== 'ACTIVE'" class="review-source-stale">来源已更新、撤回或无法找到。</small>
          </div>
          <div v-if="candidate.framework_coverage" class="review-source-item">
            <strong>框架覆盖说明</strong>
            <pre>{{ formatJson(candidate.framework_coverage) }}</pre>
          </div>
          <div v-if="candidate.structured_analysis" class="review-source-item">
            <strong>结构化推导记录</strong>
            <pre>{{ formatJson(candidate.structured_analysis) }}</pre>
          </div>
        </details>
      </article>
    </section>

    <p v-if="!findingCandidates.length && !fragmentCandidates.length" class="review-note">本次运行没有可纳入的判断或分析内容。</p>
    <p v-if="staleCandidateCount" class="review-warning" role="status">有 {{ staleCandidateCount }} 项候选使用的资料版本已变化。请重新运行分析后再纳入。</p>

    <footer v-if="!readOnly && (findingCandidates.length || fragmentCandidates.length)" class="review-actions">
      <VanButton
        type="primary"
        native-type="button"
        :loading="pending"
        :disabled="saving || pending || !hasUnadoptedCandidates || staleCandidateCount > 0"
        @click="applyAll"
      >{{ pending ? '正在加入待审内容' : hasUnadoptedCandidates ? '加入本节点待审内容' : '本次候选已加入待审内容' }}</VanButton>
      <span class="review-note">加入后请分别整体审阅判断和分析；未纳入的候选不会进入本节点成果。</span>
    </footer>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import { displayText } from '../../skills/presentation.js'
import { formatConsultantEvidenceValue, reportEvidenceTitle } from '../workbench-inputs.js'
import { findingReviewTitle } from '../analysis-review-flow.js'

export default {
  components: { VanButton },
  props: {
    run: { type: Object, required: true },
    content: { type: Object, required: true },
    readOnly: Boolean,
    saving: Boolean,
    sourcesCurrent: { type: Function, required: true },
  },
  emits: ['apply-candidates', 'busy'],
  data: () => ({ pending: false, error: '', notice: '' }),
  computed: {
    findingCandidates() { return this.run.output_parsed?.findings || [] },
    fragmentCandidates() { return this.run.output_parsed?.analysis_fragments || [] },
    pendingFindingCount() { return this.findingCandidates.filter(item => !this.alreadyApplied(item.finding_key, 'finding')).length },
    pendingFragmentCount() { return this.fragmentCandidates.filter(item => !this.alreadyApplied(item.fragment_key, 'fragment')).length },
    hasUnadoptedCandidates() { return Boolean(this.pendingFindingCount || this.pendingFragmentCount) },
    staleCandidateCount() {
      const candidates = [...this.findingCandidates, ...this.fragmentCandidates]
      return candidates.filter(item => !this.sourcesCurrent(this.run, item)).length
    },
  },
  methods: {
    displayText,
    findingReviewTitle,
    normalizedRefs(refs, key) {
      return [...new Set((refs || []).map(ref => typeof ref === 'string' ? ref : ref?.[key]).filter(Boolean))]
    },
    alreadyApplied(key, type) {
      const rows = type === 'finding' ? this.content.findings || [] : this.content.fragments || []
      const field = type === 'finding' ? 'finding_key' : 'fragment_key'
      return rows.some(item => item[field] === key && item.source_skill_run_id === this.run.id)
    },
    candidateState(candidate, type) {
      const key = type === 'finding' ? candidate.finding_key : candidate.fragment_key
      if (this.alreadyApplied(key, type)) return '已加入待审'
      const rows = type === 'finding' ? this.content.findings || [] : this.content.fragments || []
      const field = type === 'finding' ? 'finding_key' : 'fragment_key'
      return rows.some(item => item[field] === key && item.status === 'CONFIRMED') ? '将建立待审新版本' : '待纳入'
    },
    relationKey(ref) { return typeof ref === 'string' ? ref : ref?.finding_key || '' },
    findingLabel(key) {
      const candidate = this.findingCandidates.find(item => item.finding_key === key)
      const current = (this.content.findings || []).find(item => item.finding_key === key)
      return findingReviewTitle(candidate || current || { claim: key })
    },
    evidenceRecords(refs) {
      return this.normalizedRefs(refs, 'evidence_key').map(key =>
        (this.content.evidence || []).find(item => item.evidence_key === key) || { evidence_key: key, status: 'MISSING' }
      )
    },
    evidenceLabel(key) {
      const row = (this.content.evidence || []).find(item => item.evidence_key === key)
      return row ? reportEvidenceTitle(row) : '已更新或待核对的资料'
    },
    evidenceSummary(item) {
      if (item.status === 'MISSING') return item.evidence_key
      const value = formatConsultantEvidenceValue(item.value_json, item.source_type)
      const text = String(value || '').replace(/\s+/g, ' ').trim()
      return text.length > 300 ? `${text.slice(0, 300)}…` : text || '没有可显示的资料摘要。'
    },
    formatJson(value) { return JSON.stringify(value, null, 2) },
    fail(message) {
      this.error = message
      this.$nextTick(() => this.$refs.error?.focus())
    },
    applyAll() {
      if (this.readOnly || this.saving || this.pending || !this.hasUnadoptedCandidates) return
      if (this.staleCandidateCount) return this.fail('候选依据已变化，请重新运行 AI 分析后再纳入。')
      this.error = ''
      this.pending = true
      this.$emit('busy', true)
      this.$emit('apply-candidates', {
        run: this.run,
        onComplete: result => {
          this.pending = false
          this.$emit('busy', false)
          if (!result?.success) {
            if (result?.message) this.fail(result.message)
            return
          }
          this.notice = '候选已加入待审内容。请到判断审核和分析内容阶段分别整体确认。'
        },
      })
    },
  },
}
</script>
<style scoped src="./AnalysisDirectionReview.css"></style>
