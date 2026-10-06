<template>
  <section class="direction-review" aria-label="按分析方向连续审核">
    <header class="direction-review-heading">
      <div><h4>按方向连续审核</h4><p>审核关联判断 → 确认分析内容 → 下一方向。共用判断只需审核一次；暂缓的方向仍留在待办中。</p></div>
      <span role="status">已完成 {{ completed }} / {{ directions.length }} 个方向</span>
    </header>
    <WorkbenchRecordPicker v-model="directionKey" :items="directionItems" label="分析方向" :disabled="locked" />
    <p v-if="locked && editingKind" class="review-note">请先保存或取消当前修改，再切换方向或分析记录。</p>
    <p v-if="error" ref="error" class="review-error" role="alert" tabindex="-1">{{ error }}</p>
    <p v-if="notice" class="review-note" role="status" aria-live="polite">{{ notice }}</p>
    <template v-if="direction">
      <nav class="review-phases" aria-label="当前方向的审核步骤">
        <VanButton plain native-type="button" :aria-pressed="phase === 'findings'" :disabled="locked" @click="phase = 'findings'">1. 关联判断 · {{ direction.findings.filter(item => item.done).length }}/{{ direction.findings.length }}</VanButton>
        <span aria-hidden="true">→</span>
        <VanButton v-if="direction.fragment" plain native-type="button" :aria-pressed="phase === 'fragment'" :disabled="locked" @click="phase = 'fragment'">2. 分析内容</VanButton>
      </nav>
      <template v-if="phase === 'findings'">
        <WorkbenchRecordPicker v-if="direction.findings.length" v-model="findingKey" :items="findingItems" label="关联判断（先处理依赖来源）" :disabled="locked" />
        <article v-if="finding" ref="reviewCard" class="review-card" tabindex="-1">
          <header><h5>{{ finding.title }}</h5><span>{{ statusLabel(finding.status) }}{{ finding.foreign ? ' · 前序来源' : '' }}</span></header>
          <template v-if="finding.record">
            <p class="review-prose">{{ finding.record.claim }}</p>
            <p class="review-note">{{ displayText(finding.record.kind) }} · {{ displayText(finding.record.semantic_role, 'semantic_role') }} · {{ displayText(finding.record.confidence) }}把握 · {{ displayText(finding.record.reportability) }}</p>
            <details v-if="finding.record.evidence_refs?.length" class="review-source-details">
              <summary>查看 {{ finding.record.evidence_refs.length }} 项原始资料依据</summary>
              <div v-for="item in evidenceRecords(finding.record.evidence_refs)" :key="item.evidence_key" class="review-source-item">
                <strong>{{ evidenceLabel(item.evidence_key) }}</strong>
                <p>{{ evidenceSummary(item) }}</p>
                <small v-if="item.status !== 'ACTIVE'" class="review-source-stale">来源已更新、撤回或无法找到。</small>
              </div>
            </details>
            <p v-else class="review-note">资料依据：{{ finding.record.relation_refs?.length ? '采用关联判断作为依据' : '暂未关联资料' }}</p>
            <p v-if="finding.done" class="review-note">这条判断的审核结果会用于所有引用它的分析方向。</p>
            <div v-if="editingKind === 'finding'" class="review-form">
              <label>判断内容<textarea v-model.trim="findingDraft.claim" rows="4" maxlength="5000"></textarea></label>
              <div class="review-field-grid">
                <label>把握程度<select v-model="findingDraft.confidence"><option value="LOW">较低</option><option value="MEDIUM">一般</option><option value="HIGH">较高</option></select></label>
                <label>参考优先级<select v-model="findingDraft.importance"><option value="LOW">普通</option><option value="MEDIUM">关注</option><option value="HIGH">重要</option><option value="CRITICAL">优先处理</option></select></label>
                <label>报告中的呈现程度<select v-model="findingDraft.reportability"><option value="INTERNAL_ONLY">仅供内部参考</option><option value="OPTIONAL">可酌情呈现</option><option value="RECOMMENDED">建议呈现</option><option value="MUST_INCLUDE">报告需要包含</option></select></label>
              </div>
              <EvidenceReferencePicker v-model="findingDraft.evidence_refs" :items="evidenceItems" :preferred-keys="preferredEvidenceKeys" label="判断依据" />
            </div>
            <div v-if="!readOnly && finding.editable" class="review-actions">
              <VanButton v-if="!editingKind" plain native-type="button" :disabled="locked" @click="editFinding">修改判断</VanButton>
              <VanButton v-else plain native-type="button" :disabled="savingNow" @click="cancelEdit">取消修改</VanButton>
              <VanButton v-if="!finding.done || editingKind === 'finding'" type="primary" native-type="button" :disabled="savingNow" :loading="pending === 'finding'" @click="saveFinding('CONFIRMED')">{{ editingKind ? '保存并确认，继续' : '确认判断并继续' }}</VanButton>
              <VanButton v-if="!finding.done || editingKind === 'finding'" plain type="danger" native-type="button" :disabled="savingNow" @click="saveFinding('REJECTED')">拒绝判断并继续</VanButton>
              <VanButton v-else plain native-type="button" :disabled="locked" @click="continueFindings">继续当前方向</VanButton>
            </div>
            <p v-else-if="!finding.done" class="review-note">这条判断属于前序节点，请先复核来源，或修改分析正文与引用后再确认。</p>
          </template>
          <p v-else class="review-error">这条关联判断尚无可审核内容。请重新运行分析，或修订分析正文并移除无法核实的引用。</p>
        </article>
        <p v-else class="review-note">该方向直接引用资料依据，可以继续审阅分析内容。</p>
        <VanButton v-if="direction.fragment" plain native-type="button" :disabled="locked" @click="phase = 'fragment'">{{ unresolved.length ? '查看分析内容与待处理引用' : '继续审阅分析内容' }}</VanButton>
      </template>
      <article v-else-if="direction.fragment" ref="reviewCard" class="review-card" tabindex="-1">
        <header><h5>{{ direction.title }}</h5><span>{{ direction.complete ? '已确认' : '待确认分析' }}</span></header>
        <p v-if="direction.findings.some(item => item.status === 'REJECTED')" class="review-warning">本方向有被拒绝的判断。请修改分析正文，并明确移除不采用的引用；原文不会自动通过。</p>
        <p v-if="unresolved.length" class="review-warning">还有 {{ unresolved.length }} 条关联判断未处理。可先审核判断，也可修改分析并移除不采用的引用。</p>
        <template v-if="editingKind === 'fragment'">
          <div class="review-form">
            <label>分析标题<input v-model.trim="fragmentDraft.title" maxlength="240" /></label>
            <label>分析正文<textarea v-model="fragmentDraft.content" rows="9" maxlength="30000"></textarea></label>
            <fieldset class="review-references"><legend>引用判断（可多选；正文与引用须一致）</legend><label v-for="item in referenceFindings" :key="item.key"><input v-model="fragmentDraft.finding_refs" type="checkbox" :value="item.key" :disabled="item.status !== 'CONFIRMED' && !fragmentDraft.finding_refs.includes(item.key)" />{{ item.title }} · {{ statusLabel(item.status) }}</label></fieldset>
            <EvidenceReferencePicker v-model="fragmentDraft.evidence_refs" :items="evidenceItems" :preferred-keys="preferredEvidenceKeys" label="分析直接依据" />
            <details v-if="fragmentDraft.framework_coverage || fragmentDraft.structured_analysis" class="review-detail-fields">
              <summary>覆盖说明与推导记录（修改正文后请同步核对）</summary>
              <AnalysisCoverageEditor v-model="fragmentDraft.framework_coverage" label="本方向覆盖说明" />
              <AnalysisCoverageEditor v-model="fragmentDraft.structured_analysis" label="推导记录" :fields="structureFields" :source-periods="sourcePeriods" />
            </details>
          </div>
        </template>
        <template v-else>
          <p class="review-prose">{{ direction.record.content }}</p>
          <p class="review-note">关联判断：{{ direction.findings.map(item => item.title).join('、') || '直接依据原始资料分析' }}</p>
          <details v-if="fragmentEvidenceKeys.length" class="review-source-details">
            <summary>查看 {{ fragmentEvidenceKeys.length }} 项原始资料依据</summary>
            <div v-for="item in evidenceRecords(fragmentEvidenceKeys)" :key="item.evidence_key" class="review-source-item">
              <strong>{{ evidenceLabel(item.evidence_key) }}</strong>
              <p>{{ evidenceSummary(item) }}</p>
              <small v-if="item.status !== 'ACTIVE'" class="review-source-stale">来源已更新、撤回或无法找到。</small>
            </div>
          </details>
          <p v-else class="review-note">资料依据：采用已确认的关联判断</p>
        </template>
        <div v-if="!readOnly" class="review-actions">
          <VanButton v-if="!editingKind" plain native-type="button" :disabled="locked" @click="editFragment">修改内容与引用</VanButton>
          <VanButton v-else plain native-type="button" :disabled="savingNow" @click="cancelEdit">取消修改</VanButton>
          <VanButton v-if="!direction.complete || editingKind" type="primary" native-type="button" :disabled="savingNow" :loading="pending === 'fragment'" @click="saveFragment('CONFIRMED')">确认分析并进入下一方向</VanButton>
          <VanButton v-else plain native-type="button" :disabled="locked" @click="nextDirection">继续下一方向</VanButton>
          <VanButton v-if="editingKind === 'fragment'" plain native-type="button" :disabled="savingNow" @click="saveFragment('PROPOSED')">保存为待确认</VanButton>
        </div>
      </article>
      <footer class="review-actions review-direction-footer">
        <VanButton plain native-type="button" :disabled="locked" @click="nextDirection">{{ direction.complete ? '下一方向' : '暂缓此方向，继续下一待办' }}</VanButton>
        <span class="review-note">暂缓只切换待办，审核进度不会增加。</span>
      </footer>
    </template>
    <div v-if="directions.length && completed === directions.length" class="review-finished" role="status">
      <p>本次建议的方向审核已完成。请回到节点总览，核对完整性与其他待办后完成本节点。</p>
      <VanButton plain native-type="button" :disabled="locked" @click="$emit('go-overview')">前往节点总览</VanButton>
    </div>
  </section>
</template>
<script>
import { Button as VanButton } from 'vant'
import WorkbenchRecordPicker from './WorkbenchRecordPicker.vue'
import AnalysisCoverageEditor from './AnalysisCoverageEditor.vue'
import EvidenceReferencePicker from './EvidenceReferencePicker.vue'
import { displayText } from '../../skills/presentation.js'
import { formatConsultantEvidenceValue, reportEvidenceTitle } from '../workbench-inputs.js'
import { buildAnalysisDirections, createFindingReview, createFragmentReview, findingReviewTitle, fragmentReviewProblem } from '../analysis-review-flow.js'

export default {
  components: { VanButton, WorkbenchRecordPicker, AnalysisCoverageEditor, EvidenceReferencePicker },
  props: { run: { type: Object, required: true }, content: { type: Object, required: true }, stepId: Number,
    readOnly: Boolean, saving: Boolean, sourcesCurrent: { type: Function, required: true } },
  emits: ['review-candidate', 'go-overview', 'busy'],
  data: () => ({ directionKey: '', findingKey: '', phase: 'findings', editingKind: '', findingDraft: null, fragmentDraft: null, pending: '', error: '', notice: '' }),
  computed: {
    directions() { return buildAnalysisDirections(this.run, this.content, this.stepId) },
    direction() { return this.directions.find(item => item.key === this.directionKey) || this.directions.find(item => !item.complete) || this.directions[0] },
    directionItems() { return this.directions.map(item => ({ ...item, title: `${item.title} · ${item.complete ? '已完成' : '待处理'}` })) },
    findingItems() { return (this.direction?.findings || []).map(item => ({ ...item, title: `${item.title} · ${this.statusLabel(item.status)}` })) },
    finding() { return this.direction?.findings.find(item => item.key === this.findingKey) || this.unresolved[0] || this.direction?.findings[0] },
    unresolved() { return (this.direction?.findings || []).filter(item => !item.done) },
    completed() { return this.directions.filter(item => item.complete).length },
    locked() { return Boolean(this.saving || this.pending || this.editingKind) },
    savingNow() { return Boolean(this.pending || this.saving) },
    evidenceItems() { return this.content.evidence || [] },
    fragmentEvidenceKeys() {
      const findingRefs = (this.direction?.findings || []).flatMap(item => item.record?.evidence_refs || [])
      return [...new Set([...(this.fragmentReview?.evidence_refs || []), ...findingRefs])]
    },
    preferredEvidenceKeys() { return this.fragmentEvidenceKeys },
    fragmentReview() { return this.direction?.fragment ? createFragmentReview(this.direction, this.run.id) : null },
    referenceFindings() {
      const context = this.run.input_snapshot?.analysis_context || {}
      const candidates = this.run.output_parsed?.findings || []
      const allowedKeys = new Set([
        ...(this.direction?.findings || []).map(item => item.key),
        ...candidates.map(item => item.finding_key),
        ...(context.upstream_confirmed_findings || []).map(item => item.finding_key),
        ...(this.content.findings || []).filter(item => item.owner_step_task_id === this.stepId && item.status === 'CONFIRMED').map(item => item.finding_key)
      ])
      const choices = new Map((this.direction?.findings || []).map(item => [item.key, item]))
      for (const row of this.content.findings || []) {
        if (allowedKeys.has(row.finding_key) && row.status === 'CONFIRMED' && !choices.has(row.finding_key)) choices.set(row.finding_key, { key: row.finding_key, title: findingReviewTitle(row), status: row.status })
      }
      for (const candidate of candidates) {
        if (allowedKeys.has(candidate.finding_key) && !choices.has(candidate.finding_key)) {
          const current = (this.content.findings || []).find(item => item.finding_key === candidate.finding_key)
          choices.set(candidate.finding_key, { key: candidate.finding_key, title: findingReviewTitle(candidate), status: current?.status || 'PROPOSED' })
        }
      }
      return [...choices.values()]
    },
    structureFields() { return this.run.input_snapshot?.analysis_context?.reasoning_contract?.analysis_structures?.[this.direction?.key] || {} },
    sourcePeriods() { return (this.run.input_snapshot?.analysis_context?.evidence || []).flatMap(item => item.value?.bazi_facts?.dayun || []) }
  },
  watch: {
    'direction.key': { immediate: true, handler() { this.resetDirection() } },
    locked: { immediate: true, handler(value) { this.$emit('busy', value) } }
  },
  beforeUnmount() { this.$emit('busy', false) },
  methods: {
    displayText,
    statusLabel(value) { return { CONFIRMED: '已确认', REJECTED: '已拒绝', STALE: '需复核', PROPOSED: '待审核' }[value] || '待审核' },
    evidenceLabel(key) { const row = (this.content.evidence || []).find(item => item.evidence_key === key); return row ? reportEvidenceTitle(row) : '已更新或待核对的资料' },
    evidenceRecords(keys) { return (keys || []).map(key => (this.content.evidence || []).find(item => item.evidence_key === key) || { evidence_key: key, status: 'MISSING' }) },
    evidenceSummary(item) {
      if (item.status === 'MISSING') return item.evidence_key
      const value = formatConsultantEvidenceValue(item.value_json, item.source_type)
      const text = String(value || '').replace(/\s+/g, ' ').trim()
      return text.length > 300 ? `${text.slice(0, 300)}…` : text || '没有可显示的资料摘要。'
    },
    fail(message) { this.error = message; this.$nextTick(() => this.$refs.error?.focus()) },
    focusCurrent() { this.$refs.reviewCard?.scrollIntoView({ block: 'nearest' }); this.$refs.reviewCard?.focus({ preventScroll: true }) },
    resetDirection() {
      this.directionKey = this.direction?.key || ''
      this.findingKey = this.unresolved[0]?.key || this.direction?.findings[0]?.key || ''
      this.phase = this.unresolved.length || !this.direction?.fragment ? 'findings' : 'fragment'
      this.cancelEdit()
      this.notice = ''
    },
    cancelEdit() { this.editingKind = ''; this.findingDraft = null; this.fragmentDraft = null; this.error = '' },
    editFinding() { this.findingDraft = createFindingReview(this.finding); this.editingKind = 'finding'; this.error = '' },
    editFragment() { this.fragmentDraft = this.fragmentReview; this.editingKind = 'fragment'; this.error = '' },
    continueFindings() {
      const next = this.unresolved.find(item => item.key !== this.findingKey)
      if (next) this.findingKey = next.key
      else if (this.direction?.fragment) this.phase = 'fragment'
      else this.nextDirection()
    },
    nextDirection() {
      const index = this.directions.findIndex(item => item.key === this.direction?.key)
      const later = this.directions.slice(index + 1).find(item => !item.complete)
      const earlier = this.directions.slice(0, index).find(item => !item.complete)
      const next = later || earlier
      if (next) this.directionKey = next.key
      else this.notice = this.completed === this.directions.length ? '本次建议已处理完，请到节点总览核对其他待办。' : '当前方向仍有未完成事项，请继续审核或修订。'
    },
    saveFinding(status) {
      const entry = this.finding
      const draft = this.findingDraft || createFindingReview(entry)
      if (!draft.claim?.trim()) return this.fail('请填写判断内容。')
      if (!draft.evidence_refs.length && !draft.relation_refs.length) return this.fail('至少选择一项资料依据或保留关联判断。')
      this.submit('finding', entry.candidate || entry.current, { ...draft, status }, () => {
        this.notice = status === 'REJECTED' ? '已拒绝这条判断。关联分析需要由你修订后再确认。' : '已确认这条判断，继续当前方向。'
        this.continueFindings()
      })
    },
    saveFragment(status) {
      const draft = this.fragmentDraft || this.fragmentReview
      const problem = fragmentReviewProblem(draft, this.content)
      if (problem) return this.fail(problem)
      const original = this.direction.fragment
      if (original.finding_refs?.some(key => !draft.finding_refs.includes(key)) && draft.content.trim() === original.content.trim()) {
        return this.fail('移除判断引用时，请同时修订分析正文，明确不采用该判断后的解释与边界。')
      }
      this.submit('fragment', original, { ...draft, status }, () => {
        this.notice = status === 'CONFIRMED' ? '本方向分析已确认。' : '修改已保存，分析仍待确认。'
        if (status === 'CONFIRMED') this.nextDirection()
      })
    },
    submit(kind, candidate, review, afterSave) {
      if (this.readOnly || this.pending || this.saving) return
      if (!this.sourcesCurrent(this.run, candidate)) return this.fail('本次建议的资料版本已更新，请重新运行 AI 分析。')
      this.error = ''
      this.pending = kind
      this.$emit('review-candidate', { run: this.run, kind, candidate, review,
        expectedRevisionNo: review.expected_revision_no,
        onComplete: result => {
          this.pending = ''
          if (!result.success) { if (result.message) this.fail(result.message); return }
          this.cancelEdit()
          this.$nextTick(() => { afterSave(); this.$nextTick(this.focusCurrent) })
        } })
    }
  }
}
</script>
<style scoped src="./AnalysisDirectionReview.css"></style>
