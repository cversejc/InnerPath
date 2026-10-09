<template>
  <section class="node-checkpoint" :aria-label="title">
    <header class="checkpoint-heading">
      <div>
        <p class="eyebrow">{{ checkpoint === 'node' ? '节点复核' : '阶段确认' }}</p>
        <h3>{{ title }}</h3>
      </div>
      <span class="checkpoint-state" :data-state="stateTone">{{ stateLabel }}</span>
    </header>

    <p v-if="error" class="checkpoint-error" role="alert">{{ error }}</p>
    <p v-if="checkpoint !== 'node'" class="checkpoint-guidance">{{ guidance }}</p>

    <section v-if="review && checkpoint === 'findings' && step.step_key === 'S1'" class="birth-review-block core-judgment-review" aria-label="时柱、格局与喜忌整体核对">
      <h4>核心命理判断</h4>
      <FoundationEvidence v-if="birthFoundation" :value="birthFoundation.value_json" />
      <p>一次整体确认会记录你已核对时柱（或未知时辰的限制），以及格局与喜忌。具体争议仍在判断条目中修订或拒绝。</p>
    </section>

    <template v-if="review && checkpoint === 'birth_data'">
      <section class="birth-review-block" aria-label="申请时留存的用户资料">
        <h4>申请时留存的用户资料</h4>
        <dl v-if="birthProfileItems.length" class="birth-profile-grid">
          <div v-for="item in birthProfileItems" :key="item.title"><dt>{{ item.title }}</dt><dd>{{ item.body }}</dd></div>
        </dl>
        <p v-else>申请快照中没有可显示的用户档案。</p>
      </section>

      <section class="birth-review-block" aria-label="程序时间换算结果">
        <h4>程序时间换算</h4>
        <dl class="birth-calculation-grid">
          <div><dt>识别的公历钟表时间</dt><dd>{{ dateTime(proposal.civil_datetime) }}</dd></div>
          <div><dt>命理采用时间</dt><dd>{{ dateTime(proposal.adopted_datetime) }}<span v-if="proposal.basis"> · {{ basisLabel(proposal.basis) }}</span></dd></div>
          <div><dt>地点匹配</dt><dd>{{ locationLabel }}</dd></div>
          <div><dt>实际出生瞬间（UTC）</dt><dd>{{ utcDateTime(proposal.actual_utc) }}</dd></div>
          <div v-if="proposal.utc_offset_hours != null"><dt>采用的 UTC 时差</dt><dd>UTC{{ proposal.utc_offset_hours >= 0 ? '+' : '' }}{{ proposal.utc_offset_hours }}</dd></div>
          <div v-if="proposal.longitude_correction_minutes != null"><dt>经度修正</dt><dd>{{ minutes(proposal.longitude_correction_minutes) }}</dd></div>
          <div v-if="proposal.equation_of_time_minutes != null"><dt>均时差</dt><dd>{{ minutes(proposal.equation_of_time_minutes) }}</dd></div>
        </dl>
        <ul v-if="proposal.limitations?.length" class="birth-limitations"><li v-for="limit in proposal.limitations" :key="limit">{{ limit }}</li></ul>
        <details class="birth-provenance">
          <summary>地点、换算方法与来源</summary>
          <p v-if="proposal.location?.attribution">地点数据：{{ proposal.location.attribution }}</p>
          <p v-if="proposal.location?.version">地点数据版本：{{ proposal.location.version }}</p>
          <p v-if="proposal.conversion">时间算法：{{ proposal.conversion }}</p>
          <p v-if="proposal.coordinates">采用坐标：{{ proposal.coordinates.name }} · {{ proposal.coordinates.latitude }}, {{ proposal.coordinates.longitude }}</p>
          <p v-else-if="proposal.location?.candidates?.length">候选地点：{{ proposal.location.candidates.map(place => place.name).join('、') }}</p>
        </details>
      </section>

      <div v-if="canWrite" class="birth-confirmation">
        <div>
          <strong>{{ birthDecisionTitle }}</strong>
          <p>{{ birthDecision }}</p>
        </div>
        <VanButton v-if="canQuickConfirm" type="primary" native-type="button" :loading="working" :disabled="busy || working" @click="confirmRegisteredTime">
          {{ stageApproval?.stale ? '重新确认资料与换算结果' : proposal.status === 'UNKNOWN_HOUR' ? '确认时辰未知并继续' : '确认资料与换算结果' }}
        </VanButton>
        <details v-if="proposal.registered" class="birth-correction" :open="correctionOpen || timeNeedsManualReview" @toggle="correctionOpen = $event.target.open">
          <summary>{{ timeNeedsManualReview ? '填写核对信息' : '资料有误或需指定口径？' }}</summary>
          <div class="birth-correction-fields">
            <label>更正后的出生日期与时间<input v-model="timeDraft.civil_datetime" type="datetime-local" /></label>
            <label>更正后的出生地点<input v-model="timeDraft.birth_place" placeholder="省、市、区县；不更正则留空" /></label>
            <label>采用口径<select v-model="timeDraft.basis"><option value="TRUE_SOLAR">按真太阳时换算</option><option value="CIVIL">说明限制，采用民用时间</option></select></label>
            <label v-if="places.length">出生地点代表点<select v-model="timeDraft.place_id"><option :value="null">自动匹配</option><option v-for="place in places" :key="place.id" :value="place.id">{{ place.name }} · {{ place.latitude }}, {{ place.longitude }} · {{ place.admin1 }}/{{ place.admin2 }}</option></select></label>
            <label v-if="needsUtcOffset">当地 UTC 时差<input v-model="timeDraft.utc_offset_hours" type="number" min="-12" max="14" step="0.5" placeholder="例如中国大陆通常为 8" /></label>
            <label v-if="timeCorrectionNeedsReason">核对依据<textarea v-model="timeDraft.reason" rows="2" placeholder="说明更正依据、历史时区或采用民用时间的限制" /></label>
            <p class="birth-correction-hint">更正时间或地点、采用民用时间，以及历史或近似时间的时区核对，需要填写依据。</p>
            <VanButton plain native-type="button" :loading="working" :disabled="busy || working || !canConfirmCorrection" @click="confirmTimeCorrection">确认更正并重新计算</VanButton>
          </div>
        </details>
        <div v-if="!proposal.registered" class="birth-missing">
          <p>申请中缺少必要出生资料，需先向用户补问。</p>
          <VanButton plain native-type="button" :disabled="busy || working" @click="$emit('request-info', step)">向用户补问出生资料</VanButton>
        </div>
      </div>

    </template>

    <template v-if="review && checkpoint === 'node'">
      <ol class="checkpoint-list">
        <li v-for="key in review.required_checkpoints" :key="key" :data-state="review.checkpoints[key]?.current ? 'done' : review.checkpoints[key]?.stale ? 'stale' : 'open'">
          <span>{{ checkpointLabel(key) }}</span><strong>{{ checkpointStateLabel(key) }}</strong>
        </li>
      </ol>
      <p class="checkpoint-guidance">节点签核会检查所有阶段确认、完整版本检查结果和仍未处理的阻断或重要问题。</p>
      <p class="checkpoint-result" role="status">{{ checkStatusLabel }}<span v-if="review.issues?.length && review.check_historical"> · {{ review.issues.length }} 项问题，均有处理记录</span><span v-else-if="review.issues?.length"> · {{ activeIssues.length }} 项待处理，其中 {{ blockingCount }} 项阻断或重要</span><span v-if="withdrawnIssues.length"> · {{ withdrawnIssues.length }} 项 AI 自查撤回，无需处理</span></p>
      <section v-if="checkVisible" class="checkpoint-issues" :aria-label="review.check_historical ? '本节点完成时的检查结果' : '当前版本检查问题'">
        <h4>{{ review.check_historical ? '本节点完成时的检查结果' : '当前版本检查问题' }}</h4>
        <p v-if="review.check_historical" class="checkpoint-guidance">本节点已完成，以下为该版本完成时的检查结果与处理记录，仅供回看。</p>
        <p v-if="!activeIssues.length" class="checkpoint-guidance">当前版本未发现需要处理的问题。</p>
        <section v-if="review.issue_groups?.length" class="checkpoint-issue-groups" aria-label="同类问题整体处理">
          <h5>同类问题可整体处理</h5>
          <p class="checkpoint-guidance">同一类型的问题填写一次依据即可整体处理；每条问题仍单独保留处理记录、处理人与时间。</p>
          <article v-for="group in review.issue_groups" :key="group.group_key" class="checkpoint-issue-group">
            <header class="checkpoint-issue-heading">
              <span class="checkpoint-severity" :data-severity="group.severity">{{ issueSeverityLabel(group.severity) }}</span>
              <strong>{{ group.count }} 项 · {{ group.type }}</strong>
            </header>
            <details class="checkpoint-issue-group-detail">
              <summary>查看这 {{ group.count }} 项问题</summary>
              <ul class="checkpoint-issue-group-list">
                <li v-for="issue in groupIssues(group)" :key="issue.id">
                  <span class="checkpoint-issue-heading">{{ issueStatusLabel(issue.status) }}</span>
                  <p v-if="issue.message && issue.message !== issueHeadline(issue)">{{ issue.message }}</p>
                  <blockquote v-if="issue.quote">{{ issue.quote }}</blockquote>
                </li>
              </ul>
            </details>
            <div v-if="canResolveGroup(group)" class="checkpoint-issue-resolution">
              <label>处理方式<select v-model="groupDrafts[group.group_key].resolution"><option value="RETAINED">有依据地保留</option><option value="FALSE_POSITIVE">误报</option></select></label>
              <label>依据<textarea v-model="groupDrafts[group.group_key].reason" rows="2" placeholder="说明核对范围、保留或判为误报的依据" /></label>
              <VanButton plain native-type="button" :loading="working" :disabled="busy || working || !groupDrafts[group.group_key].reason.trim()" @click="resolveIssueGroup(group)">整体记录处理依据（{{ group.count }} 项）</VanButton>
            </div>
          </article>
        </section>
        <ol v-if="activeIssues.length" class="checkpoint-issue-list">
          <li v-for="issue in activeIssues" :key="issue.id" class="checkpoint-issue">
            <div class="checkpoint-issue-heading">
              <span class="checkpoint-severity" :data-severity="issue.severity">{{ issueSeverityLabel(issue.severity) }}</span>
              <span>{{ issueStatusLabel(issue.status) }}</span>
            </div>
            <strong>{{ issueHeadline(issue) }}</strong>
            <p v-if="issue.message && issue.message !== issueHeadline(issue)">{{ issue.message }}</p>
            <blockquote v-if="issue.quote">{{ issue.quote }}</blockquote>
            <VanButton v-if="issueSection(issue)" plain native-type="button" @click="$emit('to-section', issueSection(issue), issue.target_key)">
              前往{{ issueSection(issue) === 'findings' ? '判断审核' : '分析内容' }}
            </VanButton>
            <details v-if="canResolveIssue(issue)" class="checkpoint-issue-resolution">
              <summary>有依据地保留／标记误报</summary>
              <label>处理方式<select v-model="issueDrafts[issue.id].resolution"><option value="RETAINED">有依据地保留</option><option value="FALSE_POSITIVE">误报</option></select></label>
              <label>依据<textarea v-model="issueDrafts[issue.id].reason" rows="2" placeholder="说明保留或判为误报的依据" /></label>
              <VanButton plain native-type="button" :loading="working" :disabled="busy || working || !issueDrafts[issue.id].reason.trim()" @click="resolveIssue(issue)">记录处理依据</VanButton>
            </details>
          </li>
        </ol>
        <details v-if="withdrawnIssues.length" class="checkpoint-issue-history">
          <summary>AI 自查撤回的 {{ withdrawnIssues.length }} 条记录（保留存档，不计入待办）</summary>
          <ul class="checkpoint-issue-group-list">
            <li v-for="issue in withdrawnIssues" :key="issue.id">
              <span class="checkpoint-issue-heading">{{ issueStatusLabel(issue.status) }}</span>
              <p v-if="issue.message">{{ issue.message }}</p>
              <blockquote v-if="issue.quote">{{ issue.quote }}</blockquote>
            </li>
          </ul>
        </details>
      </section>
    </template>

    <p v-if="review && checkpoint !== 'node' && stageApproval?.current" class="checkpoint-result" role="status">
      已记录操作者 #{{ stageApproval.approved_by }} · {{ stageApproval.approved_at }}
    </p>
    <p v-else-if="review && checkpoint !== 'node' && stageApproval?.stale" class="checkpoint-result checkpoint-stale" role="status">相关内容版本已变化，此阶段需要重新整体确认。</p>

    <footer v-if="review && canWrite" class="checkpoint-actions">
      <template v-if="checkpoint === 'node'">
        <VanButton v-if="step.step_key !== 'S6' && (currentCheck || review.check?.status === 'FAILED' || (allCheckpointsCurrent && !checkPending && !checking && error))" plain native-type="button" :loading="checking" :disabled="busy || working || checking || checkPending" @click="runCheck">{{ currentCheck ? '重新检查完整节点' : '重试完整节点检查' }}</VanButton>
        <VanButton type="primary" native-type="button" :loading="working" :disabled="busy || working || checking || !review.can_approve" @click="approveNode">{{ step.step_key === 'S6' ? '确认终审并交付' : '确认节点并进入下一步' }}</VanButton>
      </template>
      <VanButton v-else-if="checkpoint !== 'birth_data' && !stageApproval?.current" type="primary" native-type="button" :loading="working" :disabled="busy || working || !checkpointReady" @click="approveStage">{{ checkpoint === 'narrative' ? '记录主线确认' : checkpoint === 'findings' && step.step_key === 'S1' ? (stageApproval?.stale ? '重新整体确认核心判断' : '整体确认核心判断') : stageApproval?.stale ? '重新整体确认' : '整体确认本阶段' }}</VanButton>
      <p v-if="checkpoint !== 'node' && !checkpointReady && !stageApproval?.current" class="checkpoint-hint">{{ readinessMessage }}</p>
      <VanButton v-if="checkpoint === 'report' && step.step_key === 'S5' && !checkpointReady" plain native-type="button" :disabled="busy || working" @click="$emit('to-section', 'writing')">返回 AI 写作与编排</VanButton>
    </footer>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import FoundationEvidence from './FoundationEvidence.vue'
import { approveAndDeliver, approveNodeReviewCheckpoint, getNodeReview, nodeReviewCommand, patchNodeReview } from '../api.js'
import { nextCheckpointSection } from '../node-workspace.js'
import { buildApplicationProfileItems, currentReportFoundation } from '../workbench-inputs.js'
import { reviewIssueHeadline, reviewIssueLabel } from '../review-diff.js'

const CHECKPOINT_TITLES = {
  birth_data: '出生资料与程序换算',
  findings: '本步判断与核心结构',
  analysis: '本步完整分析',
  narrative: '报告主线',
  report: '完整报告审阅',
}

export default {
  components: { VanButton, FoundationEvidence },
  props: { caseId: Number, step: Object, checkpoint: String, canWrite: Boolean, busy: Boolean },
  emits: ['changed', 'approved', 'advance', 'busy', 'request-info', 'to-section'],
  data: () => ({ review: null, error: '', working: false, checking: false, timer: null, timeDraft: {}, timeBaseline: {}, correctionOpen: false, autoCheckFingerprint: '', issueDrafts: {}, groupDrafts: {} }),
  computed: {
    title() { return this.checkpoint === 'node' ? `${this.step.step_key} 节点签核` : CHECKPOINT_TITLES[this.checkpoint] || '阶段确认' },
    proposal() { return this.review?.birth_time_proposal || {} },
    places() { return this.proposal.location?.candidates || [] },
    stageApproval() { return this.review?.checkpoints?.[this.checkpoint] || null },
    stateLabel() {
      if (this.checkpoint === 'node') {
        if (this.step.status === 'COMPLETED') return '已完成 · 仅供回看'
        return this.review?.can_approve ? '可签核' : '待完成审核'
      }
      if (this.stageApproval?.current) return '已确认'
      if (this.stageApproval?.stale) return '需要重核'
      return this.checkpointReady ? '待整体确认' : this.readinessMessage
    },
    stateTone() {
      if (this.checkpoint === 'node' && this.step.status === 'COMPLETED') return 'done'
      return this.stageApproval?.current || (this.checkpoint === 'node' && this.review?.can_approve) ? 'done' : this.stageApproval?.stale ? 'stale' : 'open'
    },
    guidance() {
      return {
        birth_data: '用户原始档案、程序换算口径、限制、地点来源与命盘结果在此对照。常规结果一次确认；无法唯一换算时先补问或更正并说明依据。',
        findings: this.step.step_key === 'S1' ? '集中审阅本步判断与程序计算结果；时柱、格局与喜忌作为一组整体确认。争议条目仍可单独修改或拒绝。' : '集中审阅本步全部判断及其来源。普通条目一次确认；争议条目仍可单独修改或拒绝。',
        analysis: '通读完整分析、来源和覆盖信息后一次确认。存在问题时仍可按具体内容修订。',
        narrative: '选择并确认主线后自动记录；主线或来源变化时，此确认会随内容版本失效。',
        report: this.step.step_key === 'S6' ? '完成质量检查和问题处理后，整体确认最终稿。报告修订后需要重新整体审阅。' : '先确认主线，通读完整报告并确保当前全文连贯性检查通过，再一次整体确认；具体问题仍可单独修订。',
      }[this.checkpoint] || ''
    },
    checkpointReady() {
      if (!this.review) return false
      if (this.checkpoint === 'birth_data') return this.canQuickConfirm || this.canConfirmCorrection
      if (this.checkpoint === 'narrative') return this.review.snapshot.narrative_plan_confirmation?.status === 'CONFIRMED'
      if (this.checkpoint === 'findings') return this.review.snapshot.findings.some(item => item.owner_step_task_id === this.step.id && item.status !== 'REJECTED')
      if (this.checkpoint === 'analysis' || this.checkpoint === 'report') {
        const fragmentsReady = this.review.snapshot.fragments.length > 0
          && !this.review.snapshot.fragments.some(item => item.status === 'STALE')
        if (!fragmentsReady) return false
        if (this.checkpoint === 'report' && this.step.step_key === 'S5') {
          return this.review.snapshot.report_generation?.status === 'READY_FOR_REVIEW'
            && this.review.snapshot.report_generation?.coherence?.status === 'PASSED'
        }
        return this.step.step_key !== 'S6' || Boolean(this.review.final_quality?.can_approve)
      }
      return false
    },
    readinessMessage() {
      if (this.checkpoint === 'birth_data') {
        if (!this.proposal.registered) return '出生资料不完整，请先补问用户。'
        if (this.proposal.status === 'NEEDS_CONFIRMATION') return '地点或时间口径需要人工核对；请在上方更正并说明依据。'
      }
      if (this.checkpoint === 'findings' && !this.checkpointReady) return '本步还没有可供整体确认的判断。'
      if ((this.checkpoint === 'analysis' || this.checkpoint === 'report') && !this.review?.snapshot.fragments.length) return '当前还没有完整内容可供审阅。'
      if (this.checkpoint === 'analysis' && this.review?.snapshot.fragments.some(item => item.status === 'STALE')) return '部分内容依据已变化，请先修订相关内容。'
      if (this.checkpoint === 'report' && this.step.step_key === 'S5'
        && (this.review?.snapshot.report_generation?.status !== 'READY_FOR_REVIEW'
          || this.review?.snapshot.report_generation?.coherence?.status !== 'PASSED')) return '请在 AI 写作与编排中完成当前正文的全文连贯性检查。'
      if (this.checkpoint === 'report' && this.step.step_key === 'S6' && !this.review?.final_quality?.can_approve) return '质量检查或问题处理尚未完成。'
      return '完成上方流程后即可确认。'
    },
    birthProfileItems() {
      const profile = {
        ...(this.review?.snapshot?.application_profile || {}),
        ...(this.proposal.registered || {}),
      }
      return buildApplicationProfileItems({ profile })
    },
    birthFoundation() {
      const evidence = (this.review?.snapshot?.evidence || []).map(item => ({ ...item, status: 'ACTIVE', value_json: item.value }))
      return currentReportFoundation(evidence)
    },
    timeConfirmed() { return Boolean(this.review?.snapshot?.metadata?.birth_time_confirmation?.confirmed) },
    timeNeedsManualReview() { return this.proposal.status === 'NEEDS_CONFIRMATION' },
    canQuickConfirm() { return this.canWrite && (!this.timeConfirmed || !this.stageApproval?.current) && ['READY', 'UNKNOWN_HOUR'].includes(this.proposal.status) },
    birthDecisionTitle() {
      if (this.timeConfirmed && this.stageApproval?.current) return '出生资料已确认'
      if (this.timeNeedsManualReview) return '需要进一步核对'
      if (!this.proposal.registered) return '出生资料待补充'
      return '资料可直接确认'
    },
    birthDecision() {
      if (this.stageApproval?.current) return '当前申请资料、时间口径、程序换算和核对记录均已绑定到此版本。'
      if (!this.proposal.registered) return '申请资料缺少必要出生日期或时间，请先向用户补问。'
      if (this.timeNeedsManualReview) return '系统无法唯一确认地点或时间口径。请补充核对信息、说明依据后重新计算。'
      if (this.proposal.status === 'UNKNOWN_HOUR') return '用户未提供出生时辰。确认这一限制后即可继续，系统不会计算时柱、紫微和精确起运。'
      return '程序已完成当前资料的地点和时间换算；核对无误后一次确认即可。'
    },
    locationLabel() {
      const name = this.proposal.coordinates?.name || (this.proposal.location?.status === 'MATCHED' ? this.proposal.location.candidates?.[0]?.name : '')
      const status = { MATCHED: '已匹配', AMBIGUOUS: '有多个候选', UNMATCHED: '未匹配' }[this.proposal.location?.status] || '待核对'
      return name ? `${status} · ${name}` : status
    },
    needsUtcOffset() {
      const profile = this.proposal.registered || {}
      const year = Number(this.timeDraft.civil_datetime?.slice(0, 4) || this.proposal.registered_civil_datetime?.slice(0, 4) || profile.birth_year)
      const historical = year < 1949 || (year >= 1986 && year <= 1991)
      const selectedPlace = this.places.find(place => place.id === this.timeDraft.place_id)
      const xinjiang = [selectedPlace, ...this.places].some(place => String(place?.admin1 || '') === '13')
      const uncertain = historical || xinjiang || profile.birth_time_basis_uncertain || profile.birth_time_precision === 'approximate'
      return this.timeNeedsManualReview && this.timeDraft.basis !== 'CIVIL' && (this.proposal.location?.status === 'MATCHED' || uncertain)
    },
    timeCorrectionNeedsReason() {
      const profile = this.proposal.registered || {}
      const correctedTime = this.timeDraft.civil_datetime && this.timeDraft.civil_datetime.slice(0, 16) !== this.proposal.registered_civil_datetime?.slice(0, 16)
      const correctedPlace = this.timeDraft.birth_place && this.timeDraft.birth_place.trim() !== String(profile.birth_place || '').trim()
      const changedPlaceSelection = String(this.timeDraft.place_id ?? '') !== String(this.timeBaseline.place_id ?? '')
      return Boolean(correctedTime || correctedPlace || changedPlaceSelection || this.timeDraft.basis === 'CIVIL' || this.needsUtcOffset)
    },
    timeDraftDirty() { return JSON.stringify(this.timeDraft) !== JSON.stringify(this.timeBaseline) },
    canConfirmCorrection() {
      if (!this.timeDraftDirty) return false
      if (this.timeCorrectionNeedsReason && !String(this.timeDraft.reason || '').trim()) return false
      if (this.needsUtcOffset && (this.timeDraft.utc_offset_hours === '' || this.timeDraft.utc_offset_hours == null)) return false
      return true
    },
    currentCheck() {
      if (this.step.step_key === 'S6') return Boolean(this.review?.final_quality?.latest_validator_run?.current)
      return Boolean(this.review?.check?.status === 'COMPLETED' && this.review.check.fingerprint === this.review.fingerprint)
    },
    checkVisible() {
      if (this.currentCheck) return true
      return Boolean(this.review?.check_historical && this.review?.check?.status === 'COMPLETED')
    },
    allCheckpointsCurrent() {
      const required = this.review?.required_checkpoints || []
      return required.length > 0 && required.every(key => this.review?.checkpoints?.[key]?.current)
    },
    checkPending() {
      if (this.step.step_key === 'S6') return ['PENDING', 'RUNNING'].includes(this.review?.final_quality?.quality_status)
      return ['PENDING', 'RUNNING'].includes(this.review?.check?.status)
    },
    checkStatusLabel() {
      if (this.step.step_key === 'S6') {
        const quality = this.review?.final_quality
        const run = quality?.latest_validator_run
        if (this.checking || this.checkPending) return '正在检查当前完整报告…'
        if (quality?.quality_status === 'PROGRAMMATIC_BLOCKED') return '程序检查发现必须处理的问题。'
        if (run?.status === 'FAILED') return '最终检查失败，请在质量检查步骤查看错误并重试。'
        if (run?.current) return quality.can_approve ? `当前报告检查通过 · 运行 #${run.id}` : '报告检查已完成，仍有问题或质量条件待处理。'
        return '完整报告尚未检查，或当前内容版本的检查已失效。'
      }
      if (this.checking || this.checkPending) return '正在检查完整节点…'
      if (this.review?.check?.status === 'FAILED') return '自动检查失败。请查看运行记录并重试，持续失败时联系管理员。'
      if (this.review?.check_historical && this.review?.check?.status === 'COMPLETED') {
        return this.blockingCount ? '本节点完成时仍有阻断或重要问题未处理。' : '本节点完成时的完整节点检查已通过。'
      }
      if (!this.currentCheck) return '完整节点尚未检查，或已有内容更新。'
      return this.blockingCount ? '检查完成，仍有阻断或重要问题。' : '完整节点检查已通过。'
    },
    blockingCount() { return (this.review?.issues || []).filter(issue => ['BLOCK', 'MAJOR'].includes(issue.severity) && issue.status === 'OPEN').length },
    activeIssues() { return (this.review?.issues || []).filter(issue => issue.status === 'OPEN') },
    withdrawnIssues() { return (this.review?.issues || []).filter(issue => issue.status === 'WITHDRAWN') },
    checkingLabel() { return this.checking || this.checkPending ? '检查中…' : this.currentCheck ? '重新检查完整节点' : '检查完整节点' },
  },
  watch: {
    'step.id'() { this.refresh() },
    checkpoint() { this.refresh() },
  },
  mounted() { this.refresh() },
  beforeUnmount() { clearTimeout(this.timer); this.$emit('busy', false) },
  methods: {
    checkpointStateLabel(key) {
      const state = this.review?.checkpoints?.[key] || {}
      if (state.current) return '已确认'
      if (this.review?.check_historical) return state.stale ? '已完成时确认（后续内容已更新）' : '当时未记录确认'
      return state.stale ? '内容已更新，需重核' : '待确认'
    },
    reviewIssueLabel,
    issueHeadline: reviewIssueHeadline,
    issueSeverityLabel(value) { return { BLOCK: '阻断', MAJOR: '重要', MINOR: '建议' }[value] || '问题' },
    issueStatusLabel(value) { return { OPEN: '待处理', RESOLVED: '已修复', RETAINED: '有依据保留', FALSE_POSITIVE: '已标记误报', DISMISSED: '已标记误报', WITHDRAWN: 'AI 自查撤回' }[value] || '需复核' },
    issueSection(issue) {
      const key = issue.target_key
      if (!key) return ''
      if (this.review?.snapshot?.findings?.some(item => item.finding_key === key)) return 'findings'
      if (this.review?.snapshot?.fragments?.some(item => item.fragment_key === key)) return 'fragments'
      return ''
    },
    canResolveIssue(issue) {
      return Boolean(this.canWrite && this.step.step_key !== 'S6' && this.currentCheck && this.review?.check?.id && issue.severity !== 'BLOCK' && issue.status === 'OPEN' && this.issueDrafts[issue.id])
    },
    async resolveIssue(issue) {
      await this.action(() => nodeReviewCommand(this.caseId, this.step.step_key, 'issues/resolve', {
        fingerprint: this.review.fingerprint,
        check_id: this.review.check.id,
        issue_id: issue.id,
        ...this.issueDrafts[issue.id],
      }))
    },
    groupIssues(group) {
      const ids = new Set((group.issue_ids || []).map(String))
      return (this.review?.issues || []).filter(issue => ids.has(String(issue.id)))
    },
    canResolveGroup(group) {
      return Boolean(this.canWrite && this.step.step_key !== 'S6' && this.currentCheck && this.review?.check?.id
        && group.issue_ids?.length && this.groupDrafts[group.group_key])
    },
    async resolveIssueGroup(group) {
      const draft = this.groupDrafts[group.group_key]
      if (!draft || !draft.reason.trim()) return
      await this.action(() => nodeReviewCommand(this.caseId, this.step.step_key, 'issues/resolve-group', {
        fingerprint: this.review.fingerprint,
        check_id: this.review.check.id,
        issue_ids: group.issue_ids,
        resolution: draft.resolution,
        reason: draft.reason.trim(),
      }))
    },
    async refresh() {
      clearTimeout(this.timer)
      try {
        const review = await getNodeReview(this.caseId, this.step.step_key)
        this.review = review
        this.issueDrafts = Object.fromEntries((review.issues || []).map(issue => [issue.id, this.issueDrafts[issue.id] || { resolution: 'RETAINED', reason: '' }]))
        this.groupDrafts = Object.fromEntries((review.issue_groups || []).map(group => [group.group_key, this.groupDrafts[group.group_key] || { resolution: 'RETAINED', reason: '' }]))
        if (!this.timeDraftDirty) this.syncTimeDraft(review)
        this.error = ''
      } catch (error) {
        this.error = error.response?.data?.detail || '读取阶段审核状态失败'
      }
      this.timer = setTimeout(() => this.refresh(), this.checkPending ? 2000 : 4000)
      this.maybeStartAutomaticCheck()
    },
    syncTimeDraft(review) {
      const proposal = review.birth_time_proposal || {}
      const confirmation = review.snapshot?.metadata?.birth_time_confirmation || {}
      this.timeDraft = {
        basis: confirmation.basis || (proposal.basis === 'CIVIL' ? 'CIVIL' : 'TRUE_SOLAR'),
        civil_datetime: String(confirmation.civil_datetime || proposal.registered_civil_datetime || proposal.civil_datetime || '').slice(0, 16),
        birth_place: confirmation.birth_place || proposal.registered?.birth_place || '',
        place_id: confirmation.place_id ?? null,
        utc_offset_hours: confirmation.utc_offset_hours ?? '',
        reason: confirmation.reason || '',
      }
      this.timeBaseline = { ...this.timeDraft }
    },
    dateTime(value) { return value ? String(value).replace('T', ' ') : '待核对' },
    utcDateTime(value) { return value ? `${String(value).replace('T', ' ').replace(/Z$/, '')} UTC` : '本次不换算' },
    basisLabel(value) { return { TRUE_SOLAR: '真太阳时', CIVIL: '民用时间', UNKNOWN: '时辰未知' }[value] || '待核对' },
    minutes(value) { return value == null ? '待核对' : `${Number(value).toFixed(2)} 分钟` },
    checkpointLabel(key) {
      const labels = { birth_data: '出生资料与换算', findings: '判断及核心结构', analysis: '完整分析', narrative: '报告主线', report: '完整报告' }
      return labels[key] || key
    },
    async action(operation, approved = false, advance = false) {
      this.working = true
      this.$emit('busy', true)
      this.error = ''
      let completed = false
      let nextSection = ''
      try {
        await operation()
        await this.refresh()
        completed = true
        nextSection = !approved && advance && this.stageApproval?.current
          ? nextCheckpointSection(this.step.step_key, this.checkpoint)
          : ''
      } catch (error) {
        const code = error.response?.data?.detail
        this.error = code === 'node_core_review_required'
          ? '请先整体核对时柱、格局与喜忌后再确认本阶段。'
          : code === 'node_report_coherence_required'
            ? '请先完成当前正文的全文连贯性检查。'
          : code || '操作失败，请重试'
      } finally {
        this.working = false
        this.$emit('busy', false)
      }
      if (!completed) return
      if (approved) this.$emit('approved')
      else {
        this.$emit('changed')
        if (nextSection) this.$emit('advance', nextSection)
      }
    },
    async confirmRegisteredTime() {
      const previous = this.review?.snapshot?.metadata?.birth_time_confirmation || {}
      const confirmation = {
        ...previous,
        basis: previous.basis || this.proposal.basis || 'TRUE_SOLAR',
        confirmed: true,
      }
      await this.action(() => patchNodeReview(this.caseId, this.step.step_key, {
        fingerprint: this.review.fingerprint,
        birth_time_confirmation: confirmation,
      }), false, true)
    },
    async confirmTimeCorrection() {
      const confirmation = { ...this.timeDraft, confirmed: true }
      if (confirmation.utc_offset_hours === '' || confirmation.utc_offset_hours == null) delete confirmation.utc_offset_hours
      else confirmation.utc_offset_hours = Number(confirmation.utc_offset_hours)
      if (!confirmation.civil_datetime) delete confirmation.civil_datetime
      if (!confirmation.birth_place) delete confirmation.birth_place
      if (confirmation.place_id == null) delete confirmation.place_id
      await this.action(() => patchNodeReview(this.caseId, this.step.step_key, {
        fingerprint: this.review.fingerprint,
        birth_time_confirmation: confirmation,
      }), false, true)
    },
    async approveStage() {
      await this.action(async () => {
        let fingerprint = this.review.fingerprint
        if (this.checkpoint === 'findings' && this.step.step_key === 'S1') {
          await patchNodeReview(this.caseId, this.step.step_key, {
            fingerprint,
            core_review: { hour_pillar: true, pattern_and_useful_gods: true },
          })
          this.review = await getNodeReview(this.caseId, this.step.step_key)
          fingerprint = this.review.fingerprint
        }
        await approveNodeReviewCheckpoint(this.caseId, this.step.step_key, {
          fingerprint,
          checkpoint_key: this.checkpoint,
          idempotency_key: `node-checkpoint:${this.caseId}:${this.step.step_key}:${this.checkpoint}:${crypto.randomUUID()}`,
        })
      }, false, true)
    },
    maybeStartAutomaticCheck() {
      if (this.checkpoint !== 'node' || this.step.step_key === 'S6' || !this.canWrite || !this.allCheckpointsCurrent || this.checking || this.working || !this.review?.fingerprint) return
      const fingerprint = this.review.fingerprint
      const existing = (this.review.commands || []).some(command => command.kind === 'CHECK' && command.fingerprint === fingerprint)
      if (existing || this.autoCheckFingerprint === fingerprint) return
      this.autoCheckFingerprint = fingerprint
      this.runCheck(true)
    },
    async runCheck(automatic = false) {
      this.checking = true
      this.$emit('busy', true)
      if (!automatic) this.error = ''
      try {
        await nodeReviewCommand(this.caseId, this.step.step_key, 'check', {
          fingerprint: this.review.fingerprint,
          idempotency_key: `node-check:${this.caseId}:${this.step.step_key}:${crypto.randomUUID()}`,
        })
        await this.refresh()
      } catch (error) {
        this.error = error.response?.data?.detail || '检查完整节点失败'
      } finally {
        this.checking = false
        this.$emit('busy', false)
      }
    },
    async approveNode() {
      await this.action(async () => {
        if (this.step.step_key === 'S6') {
          await approveAndDeliver(this.caseId, { fingerprint: this.review.fingerprint })
        } else {
          await nodeReviewCommand(this.caseId, this.step.step_key, 'approve', {
            fingerprint: this.review.fingerprint,
          })
        }
      }, true)
    },
  },
}
</script>

<style scoped>
.node-checkpoint { display: grid; gap: var(--space-4); margin-top: var(--space-5); padding-top: var(--space-4); border-top: 1px solid var(--line-strong); }
.checkpoint-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }
.checkpoint-heading .eyebrow { margin: 0 0 var(--space-1); color: var(--gold-deep); font-size: var(--text-caption); }
.checkpoint-heading h3, .birth-review-block h4 { margin: 0; font-size: var(--text-h4); font-weight: var(--weight-semibold); }
.checkpoint-state { flex: 0 0 auto; color: var(--ink-soft); font-size: var(--text-body-sm); }
.checkpoint-state[data-state="done"] { color: var(--green-deep); }
.checkpoint-state[data-state="stale"] { color: var(--cinnabar-deep); }
.checkpoint-guidance, .checkpoint-result, .birth-review-block > p { margin: 0; color: var(--ink-soft); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.checkpoint-result { color: var(--ink); }
.checkpoint-stale { color: var(--cinnabar-deep); }
.checkpoint-error { margin: 0; padding: var(--space-3); border-left: 2px solid var(--cinnabar); color: var(--cinnabar-deep); background: var(--paper-soft); font-size: var(--text-body-sm); }
.checkpoint-list { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
.checkpoint-list li { display: flex; justify-content: space-between; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: 1px solid var(--line); font-size: var(--text-body-sm); }
.checkpoint-list li strong { color: var(--ink-soft); font-weight: var(--weight-medium); }
.checkpoint-list li[data-state="done"] strong { color: var(--green-deep); }
.checkpoint-list li[data-state="stale"] strong { color: var(--cinnabar-deep); }
.checkpoint-issues { display: grid; gap: var(--space-3); }
.checkpoint-issues h4 { margin: 0; font-size: var(--text-h4); font-weight: var(--weight-semibold); }
.checkpoint-issue-list { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
.checkpoint-issue { display: grid; gap: var(--space-2); min-width: 0; padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--radius-card); background: var(--surface-strong); }
.checkpoint-issue-heading { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); color: var(--ink-soft); font-size: var(--text-caption); }
.checkpoint-severity { color: var(--ink-soft); font-weight: var(--weight-semibold); }
.checkpoint-severity[data-severity="BLOCK"], .checkpoint-severity[data-severity="MAJOR"] { color: var(--cinnabar-deep); }
.checkpoint-issue > strong { color: var(--ink); font-size: var(--text-body); font-weight: var(--weight-semibold); }
.checkpoint-issue > p, .checkpoint-issue blockquote { margin: 0; color: var(--ink-soft); font-size: var(--text-body-sm); line-height: var(--leading-body); overflow-wrap: anywhere; }
.checkpoint-issue blockquote { padding-left: var(--space-3); border-left: 2px solid var(--gold); }
.checkpoint-issue-resolution { display: grid; gap: var(--space-2); color: var(--ink-soft); font-size: var(--text-body-sm); }
.checkpoint-issue-resolution > label { display: grid; gap: var(--space-1); }
.checkpoint-issue-resolution select, .checkpoint-issue-resolution textarea { width: 100%; min-height: 38px; padding: var(--space-2); border: 1px solid var(--line); border-radius: var(--radius-control); color: var(--ink); background: var(--surface); font-family: var(--font-ui); font-size: var(--text-body-sm); }
.checkpoint-issue-groups { display: grid; gap: var(--space-2); }
.checkpoint-issue-groups h5 { margin: 0; font-size: var(--text-body); font-weight: var(--weight-semibold); }
.checkpoint-issue-group { display: grid; gap: var(--space-2); min-width: 0; padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--radius-card); background: var(--paper-soft); }
.checkpoint-issue-group strong { color: var(--ink); font-size: var(--text-body); font-weight: var(--weight-semibold); }
.checkpoint-issue-group-detail summary { min-height: var(--touch-target); padding: var(--space-2) 0; color: var(--gold-deep); cursor: pointer; font-size: var(--text-body-sm); }
.checkpoint-issue-group-list { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
.checkpoint-issue-group-list > li { display: grid; gap: var(--space-1); min-width: 0; padding: var(--space-2) 0; border-top: 1px solid var(--line); }
.checkpoint-issue-group-list > li > p, .checkpoint-issue-group-list > li blockquote { margin: 0; color: var(--ink-soft); font-size: var(--text-body-sm); line-height: var(--leading-body); overflow-wrap: anywhere; }
.checkpoint-issue-group-list > li blockquote { padding-left: var(--space-3); border-left: 2px solid var(--gold); }
.checkpoint-actions { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); }
.checkpoint-actions > p { flex-basis: 100%; margin: 0; color: var(--ink-soft); font-size: var(--text-body-sm); }
.birth-review-block { display: grid; gap: var(--space-3); }
.birth-profile-grid, .birth-calculation-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2) var(--space-4); margin: 0; }
.birth-profile-grid > div, .birth-calculation-grid > div { min-width: 0; padding: var(--space-2) 0; border-bottom: 1px solid var(--line); }
.birth-profile-grid dt, .birth-calculation-grid dt { margin-bottom: var(--space-1); color: var(--ink-soft); font-size: var(--text-caption); }
.birth-profile-grid dd, .birth-calculation-grid dd { margin: 0; overflow-wrap: anywhere; color: var(--ink); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.birth-limitations { margin: 0; padding-left: 1.25rem; color: var(--cinnabar-deep); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.birth-provenance summary, .birth-correction summary { min-height: var(--touch-target); padding: var(--space-2) 0; color: var(--gold-deep); cursor: pointer; font-size: var(--text-body-sm); }
.birth-provenance p { margin: var(--space-2) 0; overflow-wrap: anywhere; color: var(--ink-soft); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.birth-confirmation { display: grid; gap: var(--space-3); padding: var(--space-3); background: var(--paper-soft); }
.birth-confirmation > div:first-child p { margin: var(--space-1) 0 0; color: var(--ink-soft); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.birth-correction-fields { display: grid; gap: var(--space-3); }
.birth-correction-fields label { display: grid; gap: var(--space-1); font-size: var(--text-body-sm); }
.birth-correction-fields input, .birth-correction-fields select, .birth-correction-fields textarea { width: 100%; min-width: 0; min-height: var(--touch-target); padding: var(--space-2) var(--space-3); border: 1px solid var(--line-strong); border-radius: var(--button-radius); background: var(--surface); color: var(--ink); font: inherit; font-size: var(--text-body); }
.birth-correction-hint, .birth-missing p { margin: 0; color: var(--ink-soft); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.birth-missing { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--space-2); }
@media (max-width: 640px) {
  .checkpoint-heading { flex-direction: column; }
  .birth-profile-grid, .birth-calculation-grid { grid-template-columns: minmax(0, 1fr); }
  .checkpoint-actions { align-items: stretch; flex-direction: column; }
  .checkpoint-actions :deep(.van-button) { width: 100%; }
}
</style>
