<template>
  <section class="quality-issue-review" aria-label="连续处理检查问题">
    <p class="quality-review-guide">核对问题与涉及正文 → 修订正文或说明处理理由 → 保存并继续下一问题 → 重新检查 → 最终人工确认</p>
    <p v-if="quality.advisory_only" class="quality-review-guide">当前流程的检查结果只是参考建议：可以不处理其中任何一条，也可以不运行检查；核对报告后随时由咨询师确认并交付。</p>
    <section v-if="groups.length" class="quality-issue-groups" aria-label="同类问题整体处理">
      <h4>同类问题整体处理</h4>
      <p class="quality-review-guide">同一类型的问题填写一次处理理由即可整体处理；每条问题仍单独保留处理记录、处理人与时间。</p>
      <article v-for="group in groups" :key="group.group_key" class="quality-group-card">
        <header>
          <strong>{{ group.count }} 项 · {{ severityLabel(group.severity) }}</strong>
          <span>{{ issueLabel(group.issue_type) }}</span>
        </header>
        <details>
          <summary>查看涉及的 {{ group.target_keys.length || group.count }} 处正文</summary>
          <ul>
            <li v-for="key in group.target_keys" :key="key">{{ fragmentTitle(key, '') }}<span class="quality-group-target">{{ key }}</span></li>
          </ul>
        </details>
        <div v-if="groupDrafts[group.group_key]" class="quality-review-form">
          <label class="quality-review-field">处理方式<select v-model="groupDrafts[group.group_key].status" :disabled="locked"><option value="RESOLVED">已修复</option><option value="ACCEPTED">保留并说明理由</option><option value="DISMISSED">判断为误报并说明理由</option></select></label>
          <label class="quality-review-field">处理理由<textarea v-model="groupDrafts[group.group_key].resolution" rows="3" maxlength="2000" :disabled="locked" placeholder="说明核对了哪些正文和依据、修改了什么，或为什么保留。"></textarea></label>
          <div class="quality-review-actions"><VanButton type="primary" native-type="button" :loading="groupPending" :disabled="readOnly || locked || !groupDrafts[group.group_key].resolution.trim()" @click="saveGroup(group)">整体记录处理理由（{{ group.count }} 项）</VanButton></div>
        </div>
      </article>
    </section>
    <WorkbenchRecordPicker v-model="selectedKey" :items="items" :label="quality.advisory_only ? '检查建议（仅供参考，可保留）' : '待处理问题（优先处理阻断项）'" :disabled="locked || noteDirty" />
    <p v-if="error" ref="error" class="quality-review-note error" role="alert" tabindex="-1">{{ error }}</p>
    <p v-if="notice" class="quality-review-note" role="status">{{ notice }}</p>
    <article v-if="issue" ref="card" class="quality-review-card" tabindex="-1">
      <header><h4>{{ issueLabel(issue.issue_type) }}</h4><span>{{ severityLabel(issue.severity) }} · {{ statusLabel(issue.status) }}</span></header>
      <p>{{ issueMessage(issue) }}</p>
      <p v-if="issue.suggestion || issue.issue_type === 'FINDING_OVER_REPEATED'">处理建议：{{ issueSuggestion(issue) }}</p>
      <p v-if="outdated" class="quality-review-note">{{ quality.advisory_only ? '正文已更新，此项来自修改前的检查。可保存处理记录供追溯，也可以再跑一次检查作为参考；是否交付由咨询师确认。' : '正文已更新，此项来自修改前的检查。可保存处理记录供追溯，交付前必须重新检查完整报告。' }}</p>
      <template v-if="!target && reportFragments.length">
        <label class="quality-review-field">选择需要核对的正文段落<select v-model="inspectKey" :disabled="locked"><option value="">选择段落</option><option v-for="row in reportFragments" :key="row.fragment_key" :value="row.fragment_key">{{ fragmentTitle(row.fragment_key, row.title) }}</option></select></label>
      </template>
      <VanButton v-if="target || inspectFragment" plain native-type="button" :disabled="saving || pending || fragmentBusy" @click="showBody = !showBody">{{ showBody ? '收起涉及正文' : '查看并修订涉及正文' }}</VanButton>
      <p v-else-if="issue.target_fragment_key" class="quality-review-note">涉及段落暂时无法读取，请核对报告编排或退回上游修订。</p>
      <ReportFragmentReview v-if="showBody && bodyFragment" :key="bodyFragment.fragment_key" :fragment="bodyFragment" :content="content" :read-only="readOnly" :saving="fragmentSaving" @save-review="$emit('save-fragment', $event)" @busy="fragmentBusy = $event" @saved="bodySaved" @repair-source="$emit('repair-source', $event)" />
      <div v-if="issue.status === 'OPEN' && !readOnly" class="quality-review-form">
        <label class="quality-review-field">处理方式<select v-model="draft.status" :disabled="locked"><option value="RESOLVED">已修复</option><option v-if="issue.severity !== 'BLOCK'" value="ACCEPTED">保留并说明理由</option><option v-if="issue.severity !== 'BLOCK'" value="DISMISSED">判断为误报并说明理由</option></select></label>
        <label class="quality-review-field">处理理由<textarea v-model="draft.resolution" rows="3" maxlength="2000" :disabled="locked" placeholder="说明核对了哪些正文和依据、修改了什么，或为什么保留。"></textarea></label>
        <div class="quality-review-actions"><VanButton type="primary" native-type="button" :loading="pending" :disabled="locked || !draft.resolution.trim()" @click="saveIssue">保存处理记录并继续</VanButton><VanButton v-if="noteDirty" plain native-type="button" :disabled="locked" @click="resetDraft">取消本条处理说明</VanButton></div>
      </div>
      <p v-else-if="issue.resolution">处理记录：{{ issue.resolution }}</p>
      <VanButton plain native-type="button" :disabled="locked || noteDirty" @click="nextIssue">{{ issue.status === 'OPEN' ? '暂缓此问题，继续下一待办' : '继续下一待办问题' }}</VanButton>
    </article>
    <div v-if="!openIssues.length && !pending" class="quality-review-note" role="status">
      {{ checking ? '正在检查完整报告，请等待本次结果。' : needsRecheck ? '当前问题已处理或正文已有更新。请重新检查完整报告；检查通过后才能最终确认。' : quality.can_approve ? '当前检查问题已处理，检查条件已满足。请通读报告并完成最终人工确认。' : '当前没有待处理问题。请核对检查状态，补全检查后再进行最终人工确认。' }}
      <VanButton v-if="!readOnly && needsRecheck" plain native-type="button" :disabled="locked || noteDirty || checking" @click="$emit('rerun')">重新检查完整报告</VanButton>
    </div>
  </section>
</template>
<script>
import { Button as VanButton } from 'vant'
import WorkbenchRecordPicker from './WorkbenchRecordPicker.vue'
import ReportFragmentReview from './ReportFragmentReview.vue'
import { orderedQualityIssues, nextPendingRecord } from '../review-continuation.js'
import { reportFragmentTitle } from '../stages.js'

export default {
  components: { VanButton, WorkbenchRecordPicker, ReportFragmentReview },
  props: {
    quality: { type: Object, required: true }, content: { type: Object, required: true }, readOnly: Boolean, saving: Boolean, fragmentSaving: Boolean,
    issueLabel: { type: Function, required: true }, issueMessage: { type: Function, required: true }, issueSuggestion: { type: Function, required: true },
    severityLabel: { type: Function, required: true }, statusLabel: { type: Function, required: true }, selectedIssueKey: { type: String, default: '' }
  },
  emits: ['save-issue', 'save-issue-group', 'save-fragment', 'busy', 'rerun', 'update:selectedIssueKey', 'repair-source'],
  data() { return { selectedKey: this.selectedIssueKey, retainedIssue: null, draft: { status: 'RESOLVED', resolution: '' }, inspectKey: '', showBody: false,
    pending: false, fragmentBusy: false, groupPending: false, groupDrafts: {}, error: '', notice: '', editedBody: false } },
  computed: {
    orderedIssues() { return orderedQualityIssues(this.quality.issues || []) },
    groups() { return this.quality.issue_groups || [] },
    issue() { return this.orderedIssues.find(row => String(row.id) === this.selectedKey) || this.retainedIssue },
    items() {
      const rows = [...this.orderedIssues]
      if (this.retainedIssue && !rows.some(item => item.id === this.retainedIssue.id)) rows.push(this.retainedIssue)
      return rows.map(row => ({ key: String(row.id), title: `${this.severityLabel(row.severity)} · ${this.statusLabel(row.status)} · ${this.issueLabel(row.issue_type)}` }))
    },
    openIssues() { return this.orderedIssues.filter(row => row.status === 'OPEN') },
    reportFragments() { return this.content.fragments.filter(row => row.fragment_type === 'REPORT') },
    target() { return this.reportFragments.find(row => row.fragment_key === this.issue?.target_fragment_key) },
    inspectFragment() { return this.reportFragments.find(row => row.fragment_key === this.inspectKey) },
    bodyFragment() { return this.target || this.inspectFragment },
    noteDirty() { return Boolean(this.issue && (this.draft.resolution.trim() || this.draft.status !== (this.issue.severity === 'BLOCK' ? 'RESOLVED' : 'ACCEPTED'))) },
    locked() { return Boolean(this.pending || this.saving || this.fragmentBusy) },
    busy() { return Boolean(this.locked || this.groupPending || (this.issue?.status === 'OPEN' && this.noteDirty)) },
    outdated() { return Boolean(this.issue && !this.orderedIssues.some(row => row.id === this.issue.id)) },
    checking() { return ['PENDING', 'RUNNING'].includes(this.quality.latest_validator_run?.status) },
    needsRecheck() { return Boolean(this.editedBody || this.outdated || this.quality.latest_validator_run?.current === false || !this.quality.latest_validator_run) }
  },
  watch: {
    selectedKey(value) { this.selectIssue(); this.$emit('update:selectedIssueKey', value) },
    selectedIssueKey(value) { if (value !== this.selectedKey && !this.busy) this.selectedKey = value },
    orderedIssues: { immediate: true, handler(rows) {
      const current = rows.find(row => String(row.id) === this.selectedKey)
      if (current) { const initial = !this.retainedIssue; this.retainedIssue = { ...current }; if (initial) this.resetDraft() }
      else if (!this.retainedIssue) this.selectedKey = String(rows.find(row => row.status === 'OPEN')?.id || rows[0]?.id || '')
    } },
    'quality.issue_groups': { immediate: true, handler(rows) {
      const next = {}
      for (const group of rows || []) next[group.group_key] = this.groupDrafts[group.group_key] || { status: 'RESOLVED', resolution: '' }
      this.groupDrafts = next
    } },
    'quality.latest_validator_run.id'(value, prior) {
      if (value && value !== prior && !this.noteDirty && !this.fragmentBusy && !this.pending) {
        this.retainedIssue = null; this.selectedKey = ''; this.editedBody = false; this.notice = '已开始重新检查，请等待本次结果。'
      }
    },
    busy: { immediate: true, handler(value) { this.$emit('busy', value) } }
  },
  beforeUnmount() { this.$emit('busy', false) },
  methods: {
    fragmentTitle: reportFragmentTitle,
    resetDraft() { this.draft = { status: this.issue?.severity === 'BLOCK' ? 'RESOLVED' : 'ACCEPTED', resolution: '' }; this.error = '' },
    selectIssue() {
      const row = this.orderedIssues.find(item => String(item.id) === this.selectedKey)
      this.retainedIssue = row ? { ...row } : null
      this.resetDraft(); this.inspectKey = ''; this.showBody = false
    },
    nextIssue() {
      const next = nextPendingRecord(this.orderedIssues, this.issue?.id, 'id', row => row.status === 'OPEN')
      if (next) { this.selectedKey = String(next.id); this.$nextTick(() => this.$refs.card?.focus({ preventScroll: true })) }
      else if (this.openIssues.length) this.notice = '当前问题仍未处理，请继续核对或填写处理理由。'
      else if (this.needsRecheck && this.quality.advisory_only) this.notice = '可重新检查修改后的完整报告作为参考；未处理的建议会记录在最终确认中，不阻断交付。'
      else if (this.needsRecheck) this.notice = '请重新检查修改后的完整报告，再进行最终确认。'
      else this.notice = '当前问题已处理，请通读报告并完成最终人工确认。'
    },
    bodySaved() { this.editedBody = true; this.notice = this.quality.advisory_only ? '正文已保存。可记录处理理由或直接继续；检查结果不阻断交付。' : '正文已保存。请记录本条处理理由；交付前须重新检查完整报告。' },
    saveGroup(group) {
      const draft = this.groupDrafts[group.group_key]
      if (this.readOnly || this.locked || !draft || !draft.resolution.trim()) return
      if (draft.resolution.trim().length < 3) { this.error = '请填写至少 3 个字的处理理由。'; this.$nextTick(() => this.$refs.error?.focus()); return }
      this.groupPending = true; this.error = ''
      this.$emit('save-issue-group', { group, review: { issue_ids: group.issue_ids, status: draft.status, resolution: draft.resolution.trim() }, onComplete: result => {
        this.groupPending = false
        if (!result.success) { this.error = result.message; this.$nextTick(() => this.$refs.error?.focus()); return }
        this.notice = `已记录 ${group.count} 项同类问题的处理理由。`
        this.groupDrafts = { ...this.groupDrafts, [group.group_key]: { status: draft.status, resolution: '' } }
      } })
    },
    saveIssue() {
      if (this.readOnly || this.locked || !this.draft.resolution.trim()) return
      if (this.draft.resolution.trim().length < 3) { this.error = '请填写至少 3 个字的处理理由。'; this.$nextTick(() => this.$refs.error?.focus()); return }
      const issue = this.issue
      this.pending = true; this.error = ''
      this.$emit('save-issue', { issue, review: { status: this.draft.status, resolution: this.draft.resolution.trim() }, onComplete: result => {
        this.pending = false
        if (!result.success) { this.error = result.message; this.$nextTick(() => this.$refs.error?.focus()); return }
        this.retainedIssue = { ...issue, ...this.draft }
        this.resetDraft()
        this.$nextTick(this.nextIssue)
      } })
    }
  }
}
</script>
<style scoped src="./QualityIssueReview.css"></style>
