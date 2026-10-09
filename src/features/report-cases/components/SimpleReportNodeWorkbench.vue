<template>
  <section
    class="report-node-workbench simple-report-workbench"
    :class="{ 'node-focused': viewStep }"
    aria-label="简化报告流程工作台"
  >
    <ol
      v-if="!viewStep"
      class="workflow-progress-rail simple-progress-rail"
      aria-label="简化流程节点进度"
    >
      <li
        v-for="step in steps"
        :key="step.id"
        class="workflow-progress-step"
        :class="{
          selected: step.step_key === currentStep?.step_key,
          complete: step.status === 'COMPLETED',
        }"
      >
        <button
          type="button"
          class="workflow-step-select"
          :aria-pressed="step.step_key === currentStep?.step_key"
          :aria-current="step.step_key === currentStep?.step_key ? 'step' : undefined"
          @click="$emit('select-step', step.step_key)"
        >
          <span class="progress-marker">{{ versionLabel(step) }}</span>
          <span class="progress-copy">
            <strong>{{ stepLabel(step.step_key) }}</strong>
            <small>{{ statusLabel(step.status) }}</small>
          </span>
        </button>
      </li>
    </ol>

    <template v-if="viewStep">
      <div class="node-toolbar">
        <header class="node-heading">
          <div class="node-identity">
            <h2>{{ stepLabel(viewStep.step_key) }}</h2>
            <span class="node-state">
              {{ statusLabel(viewStep.status) }}{{ viewMode !== 'CURRENT' ? ' · 只读' : '' }}
            </span>
          </div>
          <div class="node-header-actions">
            <span class="simple-version-chip">{{ versionLabel(viewStep) }}</span>
            <VanButton plain native-type="button" @click="$emit('select-step', '')">
              返回流程总览
            </VanButton>
          </div>
        </header>
      </div>

      <div
        class="node-workspace-body"
        role="region"
        :aria-label="`${stepLabel(viewStep.step_key)}工作内容`"
        tabindex="0"
      >
        <div class="simple-round-brief">
          <p class="eyebrow">本节点任务</p>
          <p>{{ stepBrief(viewStep.step_key) }}</p>
        </div>

        <section class="simple-input-panel" aria-label="申请快照与上一版报告">
          <header class="simple-panel-heading">
            <h3>申请快照</h3>
            <span>{{ viewStep.assignee_id ? '已指派咨询师' : '待接单或分配' }}</span>
          </header>
          <p class="simple-panel-note">
            每个节点都以同一份用户资料为输入，并在上一版完整报告的基础上继续修改。
          </p>
          <dl v-if="profileItems.length" class="simple-field-grid" aria-label="申请档案">
            <div
              v-for="(item, index) in profileItems"
              :key="`profile-${index}`"
              :class="{ wide: String(item.body).length > 40 }"
            >
              <dt>{{ item.title }}</dt>
              <dd>{{ item.body }}</dd>
            </div>
          </dl>
          <dl v-if="contextItems.length" class="simple-field-grid" aria-label="申请情境">
            <div
              v-for="item in contextItems"
              :key="item.key"
              :class="{ wide: String(item.body).length > 40 }"
            >
              <dt>{{ item.title }}</dt>
              <dd>{{ item.body }}</dd>
            </div>
          </dl>
          <p v-if="!profileItems.length && !contextItems.length" class="simple-empty">
            申请快照没有可展示的资料，请返回列表刷新后重试。
          </p>
        </section>

        <section v-if="upstreamVersion" class="simple-source-panel" aria-label="上一版完整报告">
          <header class="simple-panel-heading">
            <h3>上一版完整报告</h3>
            <span>{{ upstreamVersion.version_label }}</span>
          </header>
          <p class="simple-panel-note">
            这是本节点的起点，请在下方报告中直接修订，系统会保存为新的完整版本。
          </p>
          <pre class="simple-source-text">{{ upstreamVersion.report_text }}</pre>
          <p v-if="upstreamVersion.review_note" class="simple-review-note">
            上一轮审核备注：{{ upstreamVersion.review_note }}
          </p>
        </section>
        <section v-else-if="isFirstRound" class="simple-source-panel" aria-label="本轮起始输入">
          <header class="simple-panel-heading">
            <h3>本轮起始输入</h3>
            <span>无上一版报告</span>
          </header>
          <p class="simple-panel-note">
            这是第一个节点，请依据上方申请快照写出第一版完整报告。
          </p>
        </section>

        <section
          v-if="isCurrent && viewStep.status === 'READY'"
          class="simple-round-actions"
          role="status"
        >
          <strong>{{ canAct ? '本节点已就绪' : '本节点由接单咨询师处理' }}</strong>
          <p v-if="canAct">点击开始后，填写本轮完整报告并保存。</p>
          <p v-else>接单或由管理员分配后，即可开始本节点。</p>
          <VanButton
            v-if="canAct"
            type="primary"
            class="primary-button"
            native-type="button"
            :loading="loading"
            :disabled="loading || saving"
            @click="$emit('start-step')"
          >
            开始本节点
          </VanButton>
        </section>

        <section
          v-if="isCurrent && viewStep.status === 'IN_REVIEW' && canAct"
          class="simple-editor"
          aria-label="本轮报告编辑"
        >
          <header class="simple-panel-heading">
            <h3>{{ versionLabel(viewStep) }} 完整报告</h3>
            <span>{{ isFinalRound ? '最终审核' : '本轮修订' }}</span>
          </header>
          <label class="simple-field">
            <span>本节点完整报告</span>
            <textarea
              :value="draft?.report_text || ''"
              rows="18"
              maxlength="200000"
              :disabled="saving || waitingForUser"
              placeholder="在这里写出或修订完整报告正文。"
              @input="patchDraft({ report_text: $event.target.value })"
            ></textarea>
          </label>
          <label class="simple-field">
            <span>审核备注<small>仅工作台可见，可留空</small></span>
            <textarea
              :value="draft?.review_note || ''"
              rows="3"
              maxlength="4000"
              :disabled="saving || waitingForUser"
              placeholder="记录本轮修改依据或需要下一轮留意的内容。"
              @input="patchDraft({ review_note: $event.target.value })"
            ></textarea>
          </label>
          <label v-if="isFinalRound" class="simple-final-confirm">
            <input
              type="checkbox"
              :checked="Boolean(draft?.final_gate_confirmed)"
              :disabled="saving || waitingForUser"
              @change="patchDraft({ final_gate_confirmed: $event.target.checked })"
            />
            <span>我已确认完成最终审核，提交后将保存终稿并直接交付给用户。</span>
          </label>
          <div class="simple-editor-actions">
            <VanButton
              type="primary"
              class="primary-button"
              native-type="button"
              :loading="saving"
              :disabled="saving || !canSubmit || waitingForUser"
              @click="$emit('complete-step')"
            >
              {{ isFinalRound ? '确认终稿并交付' : '保存并进入下一节点' }}
            </VanButton>
          </div>
        </section>

        <p
          v-else-if="viewStep.status === 'COMPLETED'"
          class="simple-completed-note"
          role="status"
        >
          本节点已完成，成果已传给下一节点。
        </p>
        <p
          v-else-if="viewStep.status === 'PENDING'"
          class="simple-completed-note"
          role="status"
        >
          需先完成前序节点，本节点才会开放。
        </p>

        <section class="simple-history" aria-label="历史版本">
          <header class="simple-panel-heading">
            <h3>版本记录</h3>
            <span>{{ versions.length }} 个版本</span>
          </header>
          <article
            v-for="version in versions"
            :key="version.id"
            class="simple-version"
            :class="{ current: version.version_no === viewStep.config_snapshot?.output_version }"
          >
            <header>
              <strong>{{ version.version_label }}</strong>
              <span>{{ stepLabel(version.source_step_key) }}{{ version.is_final ? ' · 已交付' : '' }}</span>
            </header>
            <pre class="simple-version-text">{{ version.report_text }}</pre>
            <p v-if="version.review_note" class="simple-review-note">
              审核备注：{{ version.review_note }}
            </p>
          </article>
          <p v-if="!versions.length" class="simple-empty">还没有保存任何版本。</p>
        </section>
      </div>
    </template>

    <div v-else class="workflow-finished-state simple-overview">
      <h2>{{ reportCase.status === 'DELIVERED' ? '报告已交付' : '简化流程' }}</h2>
      <p>
        同一位咨询师依次完成全部 {{ steps.length }} 个节点。每个节点的输入是申请快照
        加当前完整报告文本，确认最终节点后直接交付给用户。
      </p>
      <ol class="simple-overview-list">
        <li v-for="step in steps" :key="step.id">
          <div>
            <strong>{{ versionLabel(step) }} · {{ stepLabel(step.step_key) }}</strong>
            <span>{{ statusLabel(step.status) }}</span>
            <p>{{ stepBrief(step.step_key) }}</p>
          </div>
          <VanButton plain native-type="button" @click="$emit('select-step', step.step_key)">
            查看本节点
          </VanButton>
        </li>
      </ol>
    </div>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import { REPORT_STEP_STATUS_LABELS } from '../stages.js'
import { simpleReportStep, simpleReportStepLabel, simpleReportVersionLabel } from '../simple-stages.js'
import { canHandleStep } from '../professional-ownership.js'
import {
  buildApplicationContextItems,
  buildApplicationProfileItems,
  classifyWorkbenchStepView
} from '../workbench-inputs.js'

export default {
  components: { VanButton },
  props: {
    reportCase: Object,
    actor: Object,
    selectedStepKey: String,
    currentStep: Object,
    versions: { type: Array, default: () => [] },
    draft: { type: Object, default: null },
    loading: Boolean,
    saving: Boolean,
    waitingForUser: Boolean
  },
  emits: ['select-step', 'start-step', 'complete-step', 'update:draft'],
  computed: {
    steps() {
      return this.reportCase?.workflow_instance?.steps || []
    },
    viewStep() {
      return this.steps.find(step => step.step_key === this.selectedStepKey) || null
    },
    viewMode() {
      return classifyWorkbenchStepView(this.viewStep, this.currentStep)
    },
    isCurrent() {
      return this.viewMode === 'CURRENT'
    },
    canAct() {
      return canHandleStep(this.viewStep, this.actor) && !this.waitingForUser
    },
    isFinalRound() {
      return this.viewStep?.config_snapshot?.final_gate === true
    },
    isFirstRound() {
      return this.outputVersion <= 1
    },
    outputVersion() {
      const configured = Number(this.viewStep?.config_snapshot?.output_version)
      return Number.isFinite(configured) && configured > 0
        ? configured
        : Number(this.viewStep?.sequence_no || 0)
    },
    // Round N consumes the full text of round N-1, never an arbitrary latest
    // version, so a reopen can never feed a later draft backwards.
    upstreamVersion() {
      if (this.outputVersion <= 1) return null
      return this.versions.find(version => version.version_no === this.outputVersion - 1) || null
    },
    profileItems() {
      return buildApplicationProfileItems(this.reportCase?.application_snapshot)
    },
    contextItems() {
      return buildApplicationContextItems(this.reportCase?.application_snapshot)
    },
    canSubmit() {
      const text = String(this.draft?.report_text || '').trim()
      if (!text) return false
      return this.isFinalRound ? Boolean(this.draft?.final_gate_confirmed) : true
    }
  },
  methods: {
    patchDraft(patch) {
      this.$emit('update:draft', { ...(this.draft || {}), ...patch })
    },
    stepLabel(stepKey) {
      return simpleReportStepLabel(stepKey)
    },
    versionLabel(step) {
      return simpleReportVersionLabel(step)
    },
    statusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || '待处理'
    },
    stepBrief(stepKey) {
      return simpleReportStep(stepKey)?.task || '按流程完成本节点的完整报告。'
    }
  }
}
</script>

<style scoped src="./SimpleReportNodeWorkbench.css"></style>
