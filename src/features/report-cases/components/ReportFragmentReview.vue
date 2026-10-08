<template>
  <article ref="card" class="report-fragment-review" tabindex="-1">
    <header><h4>{{ draft.title }}</h4><span>{{ batchMode ? (fragment.status === 'STALE' ? '依据有更新，需重新生成' : '列入本次整体验阅') : fragment.status === 'CONFIRMED' ? '已确认' : fragment.status === 'STALE' ? '依据有更新，需重新生成' : '待审稿' }}</span></header>
    <p v-if="error" ref="error" class="review-feedback error" role="alert" tabindex="-1">{{ error }}</p>
    <p v-if="notice" class="review-feedback" role="status">{{ notice }}</p>
    <p v-if="fragment.revision_no !== draft.expected_revision_no" class="review-feedback">正文已有新版本。当前修改仍保留，请核对后取消修改、载入最新版再保存。</p>
    <fieldset v-if="editing" class="fragment-review-form" :disabled="pending || saving">
      <legend>修改本段</legend>
      <label>标题<input v-model.trim="draft.title" maxlength="240" /></label>
      <label>正文<textarea v-model="draft.content" rows="12" maxlength="30000"></textarea></label>
      <label>修改范围<select v-model="draft.edit_kind"><option value="STYLE">只调整表达方式</option><option value="SEMANTIC">调整内容含义</option></select></label>
      <p class="review-hint">调整内容含义后，相关内容及连贯性可能需要复核；最终检查须采用修改后的正文。</p>
    </fieldset>
    <p v-else class="fragment-review-prose">{{ fragment.content }}</p>
    <details class="fragment-review-sources">
      <summary>核对本段依据 · {{ sourceFindings.length }} 条判断、{{ sourceFragments.length }} 项分析、{{ draft.evidence_refs.length }} 项资料</summary>
      <section v-for="item in sourceFindings" :key="item.key"><strong>{{ item.title }}</strong><p>{{ item.record?.claim || '来源判断暂时无法核对，请复核前序节点。' }}</p></section>
      <section v-for="item in sourceFragments" :key="item.key"><strong>{{ item.title }}</strong><p>{{ item.record?.content || '来源分析暂时无法核对，请复核前序节点。' }}</p></section>
      <p v-if="draft.evidence_refs.length">资料依据：{{ draft.evidence_refs.map(evidenceLabel).join('、') }}</p>
      <p v-if="!sourceFindings.length && !sourceFragments.length && !draft.evidence_refs.length">本段没有保存可追溯依据，确认前请核对。</p>
    </details>
    <p v-if="fragment.status === 'STALE'" class="review-feedback">来源依据已变化。请退回写作节点重新生成或复核本段，确认前序成果后再继续。</p>
    <VanButton v-if="fragment.status === 'STALE' && !readOnly" plain native-type="button" :disabled="locked" @click="$emit('repair-source', fragment)">前往修订相关来源</VanButton>
    <div v-if="!readOnly && fragment.status !== 'STALE'" class="fragment-review-actions">
      <VanButton v-if="!editing" plain native-type="button" :disabled="locked" @click="editing = true">修改本段</VanButton>
      <VanButton v-else plain native-type="button" :disabled="locked" @click="reset">取消修改并载入最新版</VanButton>
      <VanButton v-if="batchMode && editing" type="primary" native-type="button" :loading="pending" :disabled="locked" @click="submit('PROPOSED', false)">保存修改</VanButton>
      <template v-else-if="!batchMode">
        <VanButton v-if="fragment.status !== 'CONFIRMED' || editing" type="primary" native-type="button" :loading="pending" :disabled="locked" @click="submit('CONFIRMED', advance)">{{ advance ? '确认本段并继续下一段' : '确认并保存本段' }}</VanButton>
        <VanButton v-else-if="advance" type="primary" native-type="button" :disabled="locked" @click="$emit('continue-next')">继续下一待审段落</VanButton>
        <VanButton v-if="editing" plain native-type="button" :disabled="locked" @click="submit('PROPOSED', false)">保存为待确认</VanButton>
      </template>
    </div>
  </article>
</template>
<script>
import { Button as VanButton } from 'vant'
import { reportFragmentTitle } from '../stages.js'
import { reportFragmentReviewDraft } from '../review-continuation.js'
import { findingReviewTitle } from '../analysis-review-flow.js'
import { reportEvidenceTitle } from '../workbench-inputs.js'

export default {
  components: { VanButton },
  props: { fragment: { type: Object, required: true }, content: { type: Object, required: true }, readOnly: Boolean, saving: Boolean, advance: Boolean, batchMode: Boolean },
  emits: ['save-review', 'continue-next', 'busy', 'saved', 'repair-source'],
  data: () => ({ draft: null, editing: false, pending: false, error: '', notice: '' }),
  computed: {
    locked() { return this.pending || this.saving },
    busy() { return Boolean(this.editing || this.pending) },
    sourceFindings() { return this.draft.finding_refs.map(key => { const record = this.content.findings.find(row => row.finding_key === key); return { key, record, title: findingReviewTitle(record) } }) },
    sourceFragments() { return this.draft.fragment_refs.map(key => { const record = this.content.fragments.find(row => row.fragment_key === key); return { key, record, title: reportFragmentTitle(key, record?.title) } }) }
  },
  watch: {
    'fragment.fragment_key': { immediate: true, handler() { this.reset() } },
    'fragment.revision_no'() { if (!this.editing && !this.pending) this.reset() },
    busy: { immediate: true, handler(value) { this.$emit('busy', value) } }
  },
  beforeUnmount() { this.$emit('busy', false) },
  methods: {
    reset() { this.draft = reportFragmentReviewDraft(this.fragment); this.editing = false; this.error = ''; this.notice = '' },
    evidenceLabel(key) { const row = this.content.evidence.find(item => item.evidence_key === key); return row ? reportEvidenceTitle(row) : '待复核的来源资料' },
    fail(message) { this.error = message; this.$nextTick(() => this.$refs.error?.focus()) },
    submit(status, advance) {
      if (this.readOnly || this.locked || this.fragment.status === 'STALE') return
      if (!this.draft.content.trim()) return this.fail('请填写本段正文。')
      const nextStatus = this.batchMode && this.draft.edit_kind === 'STYLE' && this.fragment.status === 'CONFIRMED' ? 'CONFIRMED' : status
      const review = { ...this.draft, status: nextStatus }
      if (!this.batchMode && status !== this.fragment.status && !(this.fragment.status === 'PROPOSED' && status === 'CONFIRMED')) review.edit_kind = 'SEMANTIC'
      this.pending = true
      this.error = ''
      this.$emit('save-review', { fragment: this.fragment, review, onComplete: result => {
        this.pending = false
        if (!result.success) { if (result.message) this.fail(result.message); return }
        this.reset()
        this.notice = this.batchMode ? '修改已保存；完整报告的整体确认已失效，需要重新审阅。' : status === 'CONFIRMED' ? '本段已确认。' : '修改已保存，本段仍待确认。'
        this.$emit('saved', { status: nextStatus })
        this.$nextTick(() => { if (advance) this.$emit('continue-next'); else this.$refs.card?.focus({ preventScroll: true }) })
      } })
    }
  }
}
</script>
<style scoped src="./ReportFragmentReview.css"></style>
