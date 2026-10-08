<template>
  <section class="whole-node-review" aria-label="节点整体审核工作区">
    <header class="whole-review-heading">
      <div><p class="eyebrow">{{ step.step_key }} · {{ ownerLabel }}</p><h2>{{ stage.shortName }}</h2><p>{{ task }}</p></div>
      <span class="review-state">{{ stateLabel }}</span>
    </header>
    <p v-if="error" class="review-message" role="alert">{{ error }}</p>
    <slot />
    <div v-if="!review" class="review-message" role="status">正在读取完整成果…</div>
    <template v-else>
      <nav class="review-mobile-tabs" aria-label="审核视图"><button type="button" :aria-pressed="mobileView === 'full'" @click="mobileView = 'full'">全文</button><button type="button" :aria-pressed="mobileView === 'todo'" @click="mobileView = 'todo'">待办 {{ blockingIssues.length }}</button></nav>
      <div class="whole-review-layout" :class="{ 'todos-collapsed': collapsed }">
        <main class="review-fulltext" :class="{ 'mobile-hidden': mobileView !== 'full' }">
          <section v-if="step.step_key === 'S1'" class="review-time-panel" aria-label="出生时间口径">
            <header class="birth-time-heading">
              <div><h3>出生时间核对</h3><p>先对照用户申请资料和系统换算结果；资料无误可直接确认。</p></div>
              <span class="birth-time-status" :data-state="birthTimeState">{{ birthTimeStatus }}</span>
            </header>

            <section class="birth-time-information" aria-label="申请时留存的用户资料">
              <h4>申请时留存的用户资料</h4>
              <dl v-if="birthProfileItems.length" class="birth-profile-grid">
                <div v-for="item in birthProfileItems" :key="item.title"><dt>{{ item.title }}</dt><dd>{{ item.body }}</dd></div>
              </dl>
              <p v-else class="birth-time-empty">申请快照中没有可显示的用户档案。</p>
            </section>

            <section class="birth-time-information" aria-label="程序时间换算结果">
              <h4>程序时间换算</h4>
              <dl class="birth-calculation-grid">
                <div><dt>识别的公历钟表时间</dt><dd>{{ birthDateTime(review.birth_time_proposal?.civil_datetime) }}</dd></div>
                <div><dt>命理采用时间</dt><dd>{{ birthDateTime(review.birth_time_proposal?.adopted_datetime) }}<span v-if="review.birth_time_proposal?.basis"> · {{ birthBasisLabel(review.birth_time_proposal.basis) }}</span></dd></div>
                <div><dt>地点匹配</dt><dd>{{ birthLocationLabel }}</dd></div>
                <div><dt>实际出生瞬间（UTC）</dt><dd>{{ review.birth_time_proposal?.actual_utc || '本次不换算' }}</dd></div>
                <div v-if="review.birth_time_proposal?.utc_offset_hours != null"><dt>采用的 UTC 时差</dt><dd>UTC{{ review.birth_time_proposal.utc_offset_hours >= 0 ? '+' : '' }}{{ review.birth_time_proposal.utc_offset_hours }}</dd></div>
                <div v-if="review.birth_time_proposal?.longitude_correction_minutes != null"><dt>经度修正</dt><dd>{{ minutes(review.birth_time_proposal.longitude_correction_minutes) }}</dd></div>
                <div v-if="review.birth_time_proposal?.equation_of_time_minutes != null"><dt>均时差</dt><dd>{{ minutes(review.birth_time_proposal.equation_of_time_minutes) }}</dd></div>
              </dl>
              <ul v-if="review.birth_time_proposal?.limitations?.length" class="birth-time-limitations"><li v-for="limit in review.birth_time_proposal.limitations" :key="limit">{{ limit }}</li></ul>
              <details class="birth-time-provenance"><summary>地点、换算方法与来源</summary>
                <p v-if="review.birth_time_proposal?.location?.attribution">地点数据：{{ review.birth_time_proposal.location.attribution }}</p>
                <p v-if="review.birth_time_proposal?.location?.version">地点数据版本：{{ review.birth_time_proposal.location.version }}</p>
                <p v-if="review.birth_time_proposal?.conversion">时间算法：{{ review.birth_time_proposal.conversion }}</p>
                <p v-if="review.birth_time_proposal?.coordinates">采用坐标：{{ review.birth_time_proposal.coordinates.name }} · {{ review.birth_time_proposal.coordinates.latitude }}, {{ review.birth_time_proposal.coordinates.longitude }}</p>
                <p v-else-if="review.birth_time_proposal?.location?.candidates?.length">候选地点：{{ review.birth_time_proposal.location.candidates.map(place => place.name).join('、') }}</p>
              </details>
            </section>

            <div v-if="writable" class="time-confirmation-form">
              <div class="birth-time-decision">
                <div><strong>{{ timeConfirmed ? '出生资料已确认' : timeNeedsManualReview ? '需要进一步核对' : '资料可直接确认' }}</strong><p>{{ birthTimeDecision }}</p></div>
                <VanButton v-if="canQuickConfirm" type="primary" native-type="button" :disabled="busy || dirty || timeDraftDirty" @click="confirmRegisteredTime">{{ review.birth_time_proposal?.status === 'UNKNOWN_HOUR' ? '确认时辰未知并继续' : '按登记资料确认并计算' }}</VanButton>
              </div>
              <details v-if="review.birth_time_proposal?.registered" :open="birthCorrectionOpen" class="birth-time-correction" @toggle="birthCorrectionOpen = $event.target.open">
                <summary>{{ timeConfirmed ? '出生资料有误？更正并重新计算' : timeNeedsManualReview ? '填写核对信息' : '资料有误或需要人工指定口径？' }}</summary>
                <div class="birth-time-correction-fields">
                  <label>更正后的出生日期与时间<input v-model="timeDraft.civil_datetime" type="datetime-local" /></label>
                  <label>更正后的出生地点<input v-model="timeDraft.birth_place" placeholder="填写省、市、区县；不更正则留空" /></label>
                  <label>采用口径<select v-model="timeDraft.basis"><option value="TRUE_SOLAR">按真太阳时换算</option><option value="CIVIL">说明限制，采用民用时间</option></select></label>
                  <label v-if="places.length">出生地点代表点<select v-model="timeDraft.place_id"><option :value="null">自动匹配</option><option v-for="p in places" :key="p.id" :value="p.id">{{ p.name }} · {{ p.latitude }}, {{ p.longitude }} · {{ p.admin1 }}/{{ p.admin2 }}</option></select></label>
                  <label v-if="needsUtcOffset">当地 UTC 时差<input v-model="timeDraft.utc_offset_hours" type="number" min="-12" max="14" step="0.5" placeholder="例如中国大陆通常为 8" /></label>
                  <label v-if="timeCorrectionNeedsReason">核对依据<textarea v-model="timeDraft.reason" rows="2" placeholder="说明更正依据、历史时区或采用民用时间的限制" /></label>
                  <p class="birth-time-form-hint">更正时间或地点、采用民用时间，以及历史或近似时间的时区核对，需要填写依据。</p>
                  <VanButton plain native-type="button" :disabled="busy || dirty || !canConfirmTimeCorrection" @click="confirmTime">确认更正并重新计算</VanButton>
                </div>
              </details>
              <div v-else class="birth-time-missing"><p>申请中缺少必要出生日期，需先向用户补问。</p><VanButton plain native-type="button" :disabled="busy" @click="$emit('request-info', step)">向用户补问出生资料</VanButton></div>
            </div>
            <section class="birth-time-information" aria-label="系统命盘测算结果">
              <h4>系统命盘测算结果</h4>
              <FoundationEvidence v-if="birthFoundation" :value="birthFoundation.value_json" />
              <p v-else class="birth-time-empty">确认出生资料后，系统会自动生成四柱及相关测算结果。</p>
            </section>
          </section>
          <section v-if="review.snapshot.narrative_plan" :id="anchor('narrative_plan')" class="review-narrative" tabindex="-1"><h3>报告主线与编排</h3><template v-if="writable && step.step_key === 'S5'"><label>报告主线<textarea v-model="narrativeDraft.core_theme" rows="3" @input="narrativeDirty = true" /></label><label>叙事安排（每行一项）<textarea v-model="arcText" rows="4" @input="narrativeDirty = true" /></label><ol class="review-plan-order"><li v-for="(key, index) in narrativeDraft.fragment_order" :key="key"><span>{{ allocationTitle(key) }}</span><button type="button" :disabled="index === 0" :aria-label="`上移${allocationTitle(key)}`" @click="moveAllocation(index, -1)">上移</button><button type="button" :disabled="index === narrativeDraft.fragment_order.length - 1" :aria-label="`下移${allocationTitle(key)}`" @click="moveAllocation(index, 1)">下移</button></li></ol></template><template v-else><WorkbenchProse :text="review.snapshot.narrative_plan.core_theme" /><details><summary>查看编排与依据</summary><pre>{{ review.snapshot.narrative_plan.narrative_arc }}</pre><p v-for="item in review.snapshot.narrative_plan.content_plan?.fragments || []" :key="item.fragment_key">{{ item.title || item.fragment_key }}</p></details></template></section>
          <section v-if="actions.length" class="review-time-panel" aria-label="成长实验"><h3>卡点与成长实验</h3><p>集中核对行动的对应关系、适用条件与停止规则。修改后统一保存和重检。</p><details v-for="a in actions" :id="anchor(a.finding_key)" :key="a.finding_key"><summary>{{ a.claim }}</summary><template v-if="writable && actionDrafts[a.finding_key]"><label>行动说明<textarea v-model="findingDrafts[a.finding_key]" rows="3" /></label><label>对应卡点<select v-model="actionDrafts[a.finding_key].block_refs" multiple><option v-for="b in blocks" :key="b.finding_key" :value="b.finding_key">{{ b.claim }}</option></select></label><label>方法<textarea v-model="actionDrafts[a.finding_key].method" rows="2" /></label><label>执行步骤（每行一步）<textarea v-model="actionDrafts[a.finding_key].stepsText" rows="4" /></label><label>频率<select v-model="actionDrafts[a.finding_key].frequency"><option value="daily">每天</option><option value="weekly">每周</option><option value="monthly">每月</option><option value="quarterly">每季度</option></select></label><label>每次时长（分钟）<input v-model.number="actionDrafts[a.finding_key].duration_minutes" type="number" min="1" max="60" /></label><label>观察指标<textarea v-model="actionDrafts[a.finding_key].observation" rows="2" /></label><label>停止规则<textarea v-model="actionDrafts[a.finding_key].stop_rule" rows="2" /></label></template><pre v-else>{{ a.structured_data }}</pre></details></section>
          <div v-if="!fragments.length" class="review-message" role="status">{{ review.preparation_error ? '准备遇到问题，请核对资料后继续或重试。' : step.assignee_id ? '正在准备完整成果，完成后会显示在这里。' : '等待分配本节点负责人。' }}<p v-if="review.preparation_error">{{ review.preparation_error }}</p></div>
          <article v-for="f in fragments" :id="anchor(f.fragment_key)" :key="f.fragment_key" tabindex="-1" class="review-fragment" :class="{ 'review-focused': focusKey === f.fragment_key }">
            <header><h3>{{ f.title || f.fragment_key }}</h3><button v-if="writable" type="button" @click="toggleEdit(f.fragment_key)">{{ editing[f.fragment_key] ? '阅读正文' : '直接编辑' }}</button></header>
            <textarea v-if="editing[f.fragment_key]" v-model="drafts[f.fragment_key]" class="review-text-editor" :aria-label="`编辑${f.title || '正文'}`" rows="12" @input="markDirty" />
            <WorkbenchProse v-else :text="drafts[f.fragment_key] ?? f.content" :label="f.title" />
            <details><summary>来源与关联判断</summary><div v-for="ref in f.source_snapshot?.findings || []" :key="ref.finding_key" class="review-source-finding"><p>{{ finding(ref.finding_key)?.claim || ref.finding_key }}</p><details v-if="writable && finding(ref.finding_key)?.owner_step_task_id === step.id"><summary>修订关联判断</summary><textarea v-model="findingDrafts[ref.finding_key]" rows="3" :aria-label="`修订判断${ref.finding_key}`" @input="markDirty" /></details></div><details v-for="ref in f.source_snapshot?.evidence || []" :key="ref.evidence_key"><summary>{{ ref.evidence_key }}</summary><pre>{{ evidence(ref.evidence_key)?.value }}</pre></details><p v-if="f.source_snapshot?.framework_coverage">覆盖：{{ f.source_snapshot.framework_coverage.status }} · {{ f.source_snapshot.framework_coverage.reason }}</p></details>
          </article>
          <section v-if="writable && fragments.length" class="review-revision-form"><h3>按修改意见让 AI 局部修订</h3><label>修改范围<select v-model="revisionTarget"><option v-for="f in fragments" :key="f.fragment_key" :value="f.fragment_key">{{ f.title || f.fragment_key }}</option></select></label><label>修改意见<textarea v-model="revisionInstruction" rows="3" placeholder="指出要调整的内容、依据和表达边界" /></label><VanButton plain native-type="button" :disabled="busy || dirty || timeDraftDirty || !revisionInstruction.trim()" @click="requestRevision">生成修订建议</VanButton><small v-if="dirty || timeDraftDirty">先保存当前修改，再请求 AI 修订。</small></section>
          <section v-for="run in proposals" :key="run.id" class="review-revision-diff"><h3>AI 修订建议 · 等待采用</h3><div v-for="change in run.output.changes" :key="change.key"><p>{{ change.reason }}</p><p class="review-diff-text">{{ diff(change).prefix }}<del>{{ diff(change).removed }}</del><ins>{{ diff(change).added }}</ins>{{ diff(change).suffix }}</p></div><VanButton plain native-type="button" :disabled="busy || dirty || timeDraftDirty || run.fingerprint !== review.fingerprint" @click="applyProposal(run)">采用这些修订</VanButton><p v-if="run.fingerprint !== review.fingerprint">正文已修改，这份建议已过期。请重新请求。</p></section>
        </main>
        <aside class="review-todos" :class="{ 'mobile-hidden': mobileView !== 'todo' }" aria-label="当前版本待办">
          <button type="button" class="review-collapse" @click="collapsed = !collapsed">{{ collapsed ? '展开待办' : '收起待办' }} · {{ blockingIssues.length }}</button>
          <div v-if="!collapsed || mobileView === 'todo'" class="review-todo-content"><h3>当前版本待办</h3><p>{{ checkLabel }}</p><p v-if="review.final_quality?.latest_validator_run?.scorecard">终审评分：{{ review.final_quality.latest_validator_run.scorecard.total }}/100</p><p v-if="!activeIssues.length">当前没有需要处理的问题。</p><p v-if="withdrawnIssues.length">另有 {{ withdrawnIssues.length }} 项 AI 自查撤回，已保留记录，无需处理。</p>
            <article v-for="issue in activeIssues" :key="issue.id" class="review-issue"><span>{{ severityLabel(issue.severity) }} · {{ issue.status === 'OPEN' ? '待处理' : issue.status === 'WITHDRAWN' ? 'AI 自查撤回' : '已记录依据' }}</span><button type="button" @click="jump(issue)">{{ issueLabel(issue) }}</button><blockquote v-if="issue.quote">{{ issue.quote }}</blockquote><p v-if="issue.resolution">{{ issue.resolution }}</p><details v-if="writable && review.check?.status === 'COMPLETED' && issue.severity !== 'BLOCK' && issue.status === 'OPEN'"><summary>有依据地保留／标记误报</summary><label>处理方式<select v-model="issueDrafts[issue.id].resolution"><option value="RETAINED">有依据地保留</option><option value="FALSE_POSITIVE">误报</option></select></label><label>依据<textarea v-model="issueDrafts[issue.id].reason" rows="2" /></label><VanButton plain native-type="button" :disabled="busy || dirty || timeDraftDirty || !issueDrafts[issue.id].reason.trim()" @click="resolveIssue(issue)">记录处理依据</VanButton></details></article>
          </div>
        </aside>
      </div>
      <footer class="whole-review-actions"><span role="status">{{ hasUnsavedChanges ? '有未保存修改' : checkLabel }}</span><div><VanButton v-if="writable" plain native-type="button" :disabled="busy || !dirty" @click="save">保存草稿</VanButton><VanButton v-if="writable" plain native-type="button" :disabled="busy || dirty || timeDraftDirty || !fragments.length" @click="check">检查当前版本</VanButton><VanButton v-if="canPrepare" plain native-type="button" :disabled="busy || dirty || timeDraftDirty" @click="prepare">{{ review.preparation_error ? '重试准备' : '继续准备' }}</VanButton><VanButton v-if="writable" type="primary" native-type="button" :disabled="busy || dirty || timeDraftDirty || !review.can_approve" :loading="busy" @click="approve">{{ step.step_key === 'S6' ? '确认终审并交付' : '确认本节点' }}</VanButton><VanButton v-if="writable" plain native-type="button" :disabled="busy || dirty || timeDraftDirty" @click="$emit('request-info', step)">向用户补问</VanButton><VanButton v-if="writable && step.step_key !== 'S1'" plain native-type="button" :disabled="busy || dirty || timeDraftDirty" @click="$emit('toggle-return')">退回上游</VanButton><VanButton v-if="step.status === 'COMPLETED' && canReopen" plain native-type="button" :disabled="busy" @click="$emit('reopen', step)">修订本节点</VanButton></div></footer>
    </template>
  </section>
</template>
<script>
import { Button as VanButton } from 'vant'
import WorkbenchProse from './WorkbenchProse.vue'
import { getNodeReview, patchNodeReview, nodeReviewCommand, approveAndDeliver } from '../api.js'
import { canHandleStep, specialtyLabels } from '../professional-ownership.js'
import { reportStage } from '../stages.js'
import { textDifference, reviewIssueLabel } from '../review-diff.js'
import { buildApplicationProfileItems, currentReportFoundation } from '../workbench-inputs.js'
import FoundationEvidence from './FoundationEvidence.vue'
export default {
  components: { VanButton, WorkbenchProse, FoundationEvidence },
  props: { caseId: Number, step: Object, actor: Object, waitingForUser: Boolean, canReopen: Boolean },
  emits: ['changed', 'approved', 'busy', 'request-info', 'toggle-return', 'reopen'],
  data: () => ({ review: null, error: '', busy: false, mobileView: 'full', collapsed: false, focusKey: '', editing: {}, drafts: {}, findingDrafts: {}, actionDrafts: {}, narrativeDraft: {}, narrativeDirty: false, arcText: '', timeDraft: {}, timeBaseline: {}, birthCorrectionOpen: false, revisionInstruction: '', revisionTarget: '', issueDrafts: {}, timer: null }),
  computed: {
    stage() { return reportStage(this.step.step_key) },
    task() { return { S1: '集中核对出生时间、时柱、格局与喜忌，通读完整基础分析，修订后统一重检。', S2: '连续阅读完整心理映射，核对依据、假设与矛盾，修订后整体确认。', S3: '核对新形成的核心张力、整合方向与前序冲突，确认跨专业交接成果。', S4: '集中核对卡点与行动的对应关系、适用性及停止规则，完整实验由 AI 先填写。', S5: '一起审阅推荐主线、编排与完整正文，集中修改并检查当前版本。', S6: '处理实质问题，复核当前完整版本，确认终审并交付。' }[this.step.step_key] },
    ownerLabel() { return specialtyLabels[this.step.required_capability] || '咨询师' },
    writable() { return this.review?.can_write && !this.waitingForUser },
    canPrepare() { return canHandleStep(this.step, this.actor) && !this.waitingForUser && ['READY', 'IN_REVIEW'].includes(this.step.status) && (!this.fragments.length || this.review?.preparation_error) },
    actions() { return (this.review?.snapshot.findings || []).filter(f => f.semantic_role === 'ACTION' && f.owner_step_task_id === this.step.id) },
    blocks() { return (this.review?.snapshot.findings || []).filter(f => f.semantic_role === 'BLOCK') },
    fragments() { const list = [...(this.review?.snapshot.fragments || [])]; const order = this.review?.snapshot.narrative_plan?.content_plan?.fragments || []; return list.sort((a,b) => (order.find(x => x.fragment_key === a.fragment_key)?.sequence_no ?? 0) - (order.find(x => x.fragment_key === b.fragment_key)?.sequence_no ?? 0)) },
    places() { return this.review?.birth_time_proposal?.location?.candidates || [] },
    birthProfileItems() {
      const profile = this.review?.birth_time_proposal?.registered || {}
      const items = buildApplicationProfileItems({ profile })
      if (profile.birth_time_precision === 'unknown') return items.map(item => item.title === '出生时间' ? { ...item, body: '未知（用户标记时辰未知）' } : item)
      return items
    },
    birthFoundation() {
      const evidence = (this.review?.snapshot?.evidence || []).map(item => ({ ...item, status: 'ACTIVE', value_json: item.value }))
      return currentReportFoundation(evidence)
    },
    timeConfirmed() { return Boolean(this.review?.snapshot?.metadata?.birth_time_confirmation?.confirmed) },
    timeNeedsManualReview() { return this.review?.birth_time_proposal?.status === 'NEEDS_CONFIRMATION' },
    canQuickConfirm() { return this.writable && !this.timeConfirmed && ['READY', 'UNKNOWN_HOUR'].includes(this.review?.birth_time_proposal?.status) },
    birthTimeState() { return this.timeConfirmed ? 'confirmed' : this.timeNeedsManualReview || !this.review?.birth_time_proposal?.registered ? 'needs-review' : this.review.birth_time_proposal.status === 'UNKNOWN_HOUR' ? 'limited' : 'ready' },
    birthTimeStatus() { return this.timeConfirmed ? '已确认' : this.timeNeedsManualReview ? '需补充核对' : this.review?.birth_time_proposal?.status === 'UNKNOWN_HOUR' ? '时辰未知' : this.review?.birth_time_proposal?.status === 'READY' ? '可直接确认' : '待补充资料' },
    birthTimeDecision() {
      if (this.timeConfirmed) return '当前申请资料和计算口径已记录。请继续核对命盘及 S1 核心内容。'
      if (!this.review?.birth_time_proposal?.registered) return '申请中的出生资料不完整，请先向用户补问缺失日期或时间，再进行核对。'
      if (this.timeNeedsManualReview) return '系统无法唯一确认地点或时间口径，请选择代表地点、补充时区依据，或说明限制后采用民用时间。'
      if (this.review?.birth_time_proposal?.status === 'UNKNOWN_HOUR') return '用户未提供出生时辰。确认这一限制后即可继续，系统不会计算时柱、紫微和精确起运。'
      return '当前资料已能完成地点和时间换算；确认无误后，系统会自动生成命盘供你核对。'
    },
    birthLocationLabel() {
      const proposal = this.review?.birth_time_proposal
      const name = proposal?.coordinates?.name || (proposal?.location?.status === 'MATCHED' ? proposal.location.candidates?.[0]?.name : '')
      const status = { MATCHED: '已匹配', AMBIGUOUS: '有多个候选', UNMATCHED: '未匹配' }[proposal?.location?.status] || '待核对'
      return name ? `${status} · ${name}` : status
    },
    needsUtcOffset() {
      const proposal = this.review?.birth_time_proposal || {}
      const profile = proposal.registered || {}
      const year = Number(this.timeDraft.civil_datetime?.slice(0, 4) || proposal.registered_civil_datetime?.slice(0, 4) || profile.birth_year)
      const historical = year < 1949 || (year >= 1986 && year <= 1991)
      const selectedPlace = this.places.find(place => place.id === this.timeDraft.place_id)
      const xinjiang = [selectedPlace, ...this.places].some(place => String(place?.admin1 || '') === '13')
      const uncertain = historical || xinjiang || profile.birth_time_basis_uncertain || profile.birth_time_precision === 'approximate'
      return this.timeNeedsManualReview && this.timeDraft.basis !== 'CIVIL' && (proposal.location?.status === 'MATCHED' || uncertain)
    },
    timeCorrectionNeedsReason() {
      const proposal = this.review?.birth_time_proposal || {}
      const profile = proposal.registered || {}
      const correctedTime = this.timeDraft.civil_datetime && this.timeDraft.civil_datetime.slice(0, 16) !== proposal.registered_civil_datetime?.slice(0, 16)
      const correctedPlace = this.timeDraft.birth_place && this.timeDraft.birth_place.trim() !== String(profile.birth_place || '').trim()
      return Boolean(correctedTime || correctedPlace || this.timeDraft.basis === 'CIVIL' || this.needsUtcOffset)
    },
    canConfirmTimeCorrection() {
      if (!this.timeDraftDirty) return false
      if (this.timeCorrectionNeedsReason && !String(this.timeDraft.reason || '').trim()) return false
      if (this.needsUtcOffset && (this.timeDraft.utc_offset_hours === '' || this.timeDraft.utc_offset_hours == null)) return false
      return true
    },
    proposals() { return (this.review?.commands || []).filter(r => r.kind === 'REVISION' && r.status === 'COMPLETED') },
    blockingIssues() { return (this.review?.issues || []).filter(i => ['BLOCK', 'MAJOR'].includes(i.severity) && i.status === 'OPEN') },
    activeIssues() { return (this.review?.issues || []).filter(i => i.status === 'OPEN') },
    withdrawnIssues() { return (this.review?.issues || []).filter(i => i.status === 'WITHDRAWN') },
    timeDraftDirty() { return JSON.stringify(this.timeDraft) !== JSON.stringify(this.timeBaseline) },
    dirty() { return this.narrativeDirty || this.actions.some(a => this.actionChanged(a)) || this.fragments.some(f => this.drafts[f.fragment_key] !== undefined && this.drafts[f.fragment_key] !== f.content) || (this.review?.snapshot.findings || []).some(f => this.findingDrafts[f.finding_key] !== undefined && this.findingDrafts[f.finding_key] !== f.claim) },
    hasUnsavedChanges() { return this.dirty || this.timeDraftDirty },
    stateLabel() { return this.step.status === 'COMPLETED' ? '已确认' : this.writable ? '整体审阅' : this.step.assignee_id ? '供你查看' : '待分配负责人' },
    checkLabel() { return this.review?.check?.status === 'COMPLETED' ? this.blockingIssues.length ? '当前版本仍有实质问题' : '当前版本已检查' : this.review?.check?.status === 'RUNNING' || this.review?.check?.status === 'PENDING' ? '正在检查当前版本…' : '当前版本尚未检查／旧检查已失效' },
  },
  watch: { hasUnsavedChanges(value) { this.$emit('busy', value) } },
  mounted() { this.refresh() },
  beforeUnmount() { clearTimeout(this.timer); this.$emit('busy', false) },
  methods: {
    issueLabel: reviewIssueLabel,
    severityLabel(value) { return { BLOCK: '阻断', MAJOR: '重要', MINOR: '建议' }[value] || value },
    anchor(key) { return `review-${encodeURIComponent(key)}` },
    minutes(value) { return value == null ? '待核对' : `${value.toFixed(2)} 分钟` },
    finding(key) { return this.review.snapshot.findings.find(f => f.finding_key === key) },
    evidence(key) { return this.review.snapshot.evidence.find(e => e.evidence_key === key) },
    diff(change) { return textDifference(change.before, change.content) },
    markDirty() { this.$emit('busy', true) },
    allocationTitle(key) { return this.review.snapshot.narrative_plan.content_plan.fragments.find(a => a.fragment_key === key)?.title || this.fragments.find(f => f.fragment_key === key)?.title || key },
    moveAllocation(index, delta) { const order = this.narrativeDraft.fragment_order; [order[index], order[index + delta]] = [order[index + delta], order[index]]; this.narrativeDirty = true },
    actionData(a) { const data = { ...this.actionDrafts[a.finding_key] }; data.steps = data.stepsText?.split('\n').map(s => s.trim()).filter(Boolean) || []; delete data.stepsText; return data },
    actionChanged(a) { return this.actionDrafts[a.finding_key] && JSON.stringify(this.actionData(a)) !== JSON.stringify(a.structured_data) },
    toggleEdit(key) { this.editing[key] = !this.editing[key] },
    async refresh() {
      clearTimeout(this.timer)
      try {
        const review = await getNodeReview(this.caseId, this.step.step_key)
        if (!this.hasUnsavedChanges) {
          const firstLoad = !this.review
          this.review = review
          if (firstLoad) this.birthCorrectionOpen = review.birth_time_proposal?.status === 'NEEDS_CONFIRMATION'
          this.drafts = Object.fromEntries(review.snapshot.fragments.map(f => [f.fragment_key, f.content]))
          this.findingDrafts = Object.fromEntries(review.snapshot.findings.map(f => [f.finding_key, f.claim]))
          this.actionDrafts = Object.fromEntries(review.snapshot.findings.filter(f => f.semantic_role === 'ACTION' && f.owner_step_task_id === this.step.id).map(a => [a.finding_key, { ...a.structured_data, stepsText: (a.structured_data.steps || []).join('\n') }]))
          const plan = review.snapshot.narrative_plan
          this.narrativeDraft = plan ? { core_theme: plan.core_theme, fragment_order: (plan.content_plan?.fragments || []).map(a => a.fragment_key) } : {}
          this.arcText = (plan?.narrative_arc || []).map(a => typeof a === 'string' ? a : a.title || a.description || a.purpose || '').join('\n')
          this.timeDraft = { basis: 'TRUE_SOLAR', place_id: null, utc_offset_hours: '', reason: '', ...review.snapshot.metadata.birth_time_confirmation }
          this.timeBaseline = { ...this.timeDraft }
          this.revisionTarget ||= review.snapshot.fragments[0]?.fragment_key || ''
          this.issueDrafts = Object.fromEntries(review.issues.map(i => [i.id, this.issueDrafts[i.id] || { resolution: 'RETAINED', reason: '' }]))
        }
      } catch (error) { this.error = error.response?.data?.detail || '读取审核工作区失败' }
      this.timer = setTimeout(() => this.refresh(), 5000)
    },
    async action(operation) { this.busy = true; this.error = ''; try { await operation(); await this.refresh() } catch (error) { this.error = error.response?.data?.detail || '操作失败，请重试' } finally { this.busy = false } },
    async save() { await this.action(async () => { const changes = [...this.fragments.filter(f => this.drafts[f.fragment_key] !== f.content).map(f => ({ kind: 'fragment', key: f.fragment_key, content: this.drafts[f.fragment_key] })), ...this.review.snapshot.findings.filter(f => f.owner_step_task_id === this.step.id && (this.findingDrafts[f.finding_key] !== f.claim || this.actionChanged(f))).map(f => ({ kind: 'finding', key: f.finding_key, content: this.findingDrafts[f.finding_key], ...(this.actionDrafts[f.finding_key] ? { structured_data: this.actionData(f) } : {}) }))]; this.review = await patchNodeReview(this.caseId, this.step.step_key, { fingerprint: this.review.fingerprint, changes, ...(this.narrativeDirty ? { narrative: { ...this.narrativeDraft, narrative_arc: this.arcText.split('\n').map(s => s.trim()).filter(Boolean) } } : {}) }); this.narrativeDirty = false; this.$emit('busy', false) }) },
    birthDateTime(value) { return value ? String(value).replace('T', ' ') : '待核对' },
    birthBasisLabel(value) { return { TRUE_SOLAR: '真太阳时', CIVIL: '民用时间', UNKNOWN: '时辰未知' }[value] || '待核对' },
    async confirmRegisteredTime() { await this.action(async () => { const proposal = this.review.birth_time_proposal; const value = { basis: proposal?.basis === 'CIVIL' ? 'CIVIL' : 'TRUE_SOLAR', confirmed: true }; this.review = await patchNodeReview(this.caseId, this.step.step_key, { fingerprint: this.review.fingerprint, birth_time_confirmation: value }); this.timeDraft = { ...this.timeDraft, ...value }; this.timeBaseline = { ...this.timeDraft } }) },
    async confirmTime() { await this.action(async () => { const value = { ...this.timeDraft, confirmed: true }; if (value.utc_offset_hours === '' || value.utc_offset_hours == null) delete value.utc_offset_hours; else value.utc_offset_hours = Number(value.utc_offset_hours); for (const key of ['civil_datetime', 'birth_place']) if (!value[key]) delete value[key]; this.review = await patchNodeReview(this.caseId, this.step.step_key, { fingerprint: this.review.fingerprint, birth_time_confirmation: value }); this.timeBaseline = { ...this.timeDraft } }) },
    async command(path, extra = {}) { return nodeReviewCommand(this.caseId, this.step.step_key, path, { fingerprint: this.review.fingerprint, idempotency_key: `review:${this.caseId}:${this.step.step_key}:${crypto.randomUUID()}`, ...extra }) },
    async check() { await this.action(() => this.command('check')) },
    async prepare() { await this.action(() => this.command('prepare')) },
    async requestRevision() { await this.action(() => this.command('revisions', { targets: [this.revisionTarget], instruction: this.revisionInstruction })) },
    async applyProposal(run) { await this.action(() => this.command(`revisions/${run.id}/apply`)) },
    async resolveIssue(issue) { await this.action(() => this.command('issues/resolve', { check_id: this.review.check.id, issue_id: issue.id, ...this.issueDrafts[issue.id] })) },
    jump(issue) { if (!issue.target_key) return; this.focusKey = issue.target_key; this.mobileView = 'full'; this.$nextTick(() => { const element = document.getElementById(this.anchor(issue.target_key)); element?.scrollIntoView({ block: 'start', behavior: 'smooth' }); element?.focus({ preventScroll: true }) }) },
    async approve() { await this.action(async () => { if (this.step.step_key === 'S6') await approveAndDeliver(this.caseId, { fingerprint: this.review.fingerprint }); else await this.command('approve'); this.$emit('approved') }) },
  },
}
</script>
<style scoped src="./NodeReviewWorkspace.css"></style>
