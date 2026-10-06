<script setup>
import { ref } from 'vue'
import { Button as VanButton } from 'vant'
import IconMark from '../../../components/IconMark.vue'
import ProfileSummary from '../../../components/ProfileSummary.vue'
import AssessmentDisclosureToggle from './AssessmentDisclosureToggle.vue'

const props = defineProps({
  contextDraft: { type: Object, required: true },
  contextErrorSummary: { type: Array, default: () => [] },
  contextErrors: { type: Object, default: () => ({}) },
  contextMessage: { type: String, default: '' },
  decisionStyleOptions: { type: Array, default: () => [] },
  draftRestored: { type: Boolean, default: false },
  draftStatus: { type: String, default: '' },
  expectedOutcomeOptions: { type: Array, default: () => [] },
  formMessage: { type: String, default: '' },
  lastContext: { type: Object, default: null },
  latestReportStatus: { type: String, default: 'none' },
  profile: { type: Object, required: true },
  profileLastConfirmedAt: { type: String, default: null },
  profileVersion: { type: Number, default: 1 },
  showAdvancedContext: { type: Boolean, default: false },
  submitting: { type: Boolean, default: false },
  isEditingRequest: { type: Boolean, default: false },
  topics: { type: Array, default: () => [] }
})

const emit = defineEmits([
  'edit-profile',
  'open-latest-report',
  'reuse-context',
  'submit-assessment',
  'toggle-advanced-context',
  'toggle-decision-style',
  'toggle-expected-outcome',
  'toggle-topic',
  'update:context-draft',
  'validate-context-field'
])

const stepHeading = ref(null)

function updateField(field, value) {
  emit('update:context-draft', { ...props.contextDraft, [field]: value })
}

function truncate(value, length) {
  const text = String(value || '')
  return text.length > length ? `${text.slice(0, length)}…` : text
}

function focusStepHeading() {
  stepHeading.value?.focus({ preventScroll: true })
}

defineExpose({ focusStepHeading })
</script>

<template>
  <div class="step-content form-panel">
    <div class="step-heading">
      <p class="section-kicker">STEP 02</p>
      <h2 ref="stepHeading" tabindex="-1">这一次，你想看什么</h2>
      <p>当前页面收集的信息只用于生成本次说明书，不会写入个人档案。</p>
      <div v-if="draftRestored || draftStatus" class="draft-status" role="status" aria-live="polite">
        <span class="draft-status-dot" aria-hidden="true"></span>
        <span>{{ draftRestored ? '已恢复上次未完成的草稿，你可以继续编辑。' : draftStatus }}</span>
      </div>
    </div>

    <ProfileSummary :profile="profile" :profile-version="profileVersion" :last-confirmed-at="profileLastConfirmedAt" @edit="emit('edit-profile')" />

    <section
      v-if="latestReportStatus !== 'none'"
      class="latest-report-status"
      :class="`latest-report-status--${latestReportStatus}`"
      aria-labelledby="latest-report-status-title"
    >
      <div class="latest-report-status-copy">
        <span class="mini-label">人生说明书进度</span>
        <h3 id="latest-report-status-title">
          {{ latestReportStatus === 'processing' ? '已提交申请' : latestReportStatus === 'completed' ? '说明书已生成' : '上次申请未完成' }}
        </h3>
        <p role="status" aria-live="polite">
          {{ latestReportStatus === 'processing'
            ? '正在等待生成你的专属人生说明书。'
            : latestReportStatus === 'completed'
              ? '最近一份人生说明书已准备好，可以打开查看。'
              : '上次生成没有完成。你可以重新填写本次问题并再次提交。' }}
        </p>
      </div>
      <VanButton
        v-if="latestReportStatus === 'processing' || latestReportStatus === 'completed'"
        type="primary"
        native-type="button"
        class="primary-button latest-report-status-action"
        :aria-busy="latestReportStatus === 'processing'"
        @click="emit('open-latest-report')"
      >
        <template #icon><IconMark :name="latestReportStatus === 'processing' ? 'hourglass' : 'document'" /></template>
        {{ latestReportStatus === 'processing' ? '生成中' : '查看报告' }}
      </VanButton>
    </section>

    <div v-if="lastContext" class="reuse-context-card">
      <div>
        <span class="mini-label">上次申请背景</span>
        <p>{{ truncate(lastContext.current_challenge, 96) || '已保存上次报告的情境' }}</p>
      </div>
      <VanButton type="default" native-type="button" class="secondary-button small-button" @click="emit('reuse-context')">沿用上次背景并编辑</VanButton>
    </div>
    <p v-if="contextMessage" class="context-message" role="status">{{ contextMessage }}</p>
    <form class="assessment-form context-form" novalidate @submit.prevent="emit('submit-assessment')">
      <fieldset class="form-group choice-fieldset" :aria-describedby="contextErrors.focus_topics ? 'assessment-focus-topics-error' : undefined">
        <legend class="form-label">当前最关注的生活领域 <span class="required">*</span> <span class="form-hint">最多选择 3 项</span> <span class="selection-count">{{ contextDraft.focus_topics.length }}/3</span></legend>
        <div class="topics-grid">
          <VanButton
            v-for="topic in topics"
            :key="topic.id"
            type="default"
            native-type="button"
            plain
            class="topic-card"
            :class="{ selected: contextDraft.focus_topics.includes(topic.id) }"
            :aria-pressed="contextDraft.focus_topics.includes(topic.id)"
            @click="emit('toggle-topic', topic.id)"
          >
            <strong>{{ topic.title }}</strong>
            <small>{{ topic.desc }}</small>
          </VanButton>
        </div>
        <div v-if="contextDraft.focus_topics.includes('other')" class="form-group other-detail-field">
          <label class="form-label" for="assessment-focus-topics-other">补充其他关注领域（选填）</label>
          <textarea id="assessment-focus-topics-other" :value="contextDraft.focus_topics_other" rows="2" maxlength="500" placeholder="写下你想关注的其他领域" @input="updateField('focus_topics_other', $event.target.value)"></textarea>
        </div>
        <p v-if="contextErrors.focus_topics" id="assessment-focus-topics-error" class="field-error" role="alert">{{ contextErrors.focus_topics }}</p>
      </fieldset>

      <div class="form-group">
        <label class="form-label" for="assessment-current-challenge">现在面临的最大困惑或挑战 <span class="required">*</span></label>
        <textarea id="assessment-current-challenge" :value="contextDraft.current_challenge" rows="5" maxlength="2000" placeholder="请尽可能具体地描述：发生了什么，你卡在哪里？" :aria-invalid="Boolean(contextErrors.current_challenge)" :aria-describedby="contextErrors.current_challenge ? 'assessment-current-challenge-error' : 'assessment-current-challenge-hint'" @input="updateField('current_challenge', $event.target.value)" @blur="emit('validate-context-field', 'current_challenge')"></textarea>
        <div class="field-meta">
          <p id="assessment-current-challenge-hint" class="form-hint">例如：想转行但不确定方向，已经反复犹豫半年。</p>
          <span class="char-count" aria-live="polite">{{ String(contextDraft.current_challenge || '').length }}/2000</span>
        </div>
        <p v-if="contextErrors.current_challenge" id="assessment-current-challenge-error" class="field-error" role="alert">{{ contextErrors.current_challenge }}</p>
      </div>

      <fieldset class="form-group choice-fieldset" :aria-describedby="contextErrors.expected_outcomes ? 'assessment-expected-outcomes-error' : undefined">
        <legend class="form-label">希望通过说明书获得什么 <span class="required">*</span> <span class="form-hint">至少选择 1 项</span> <span class="selection-count">{{ contextDraft.expected_outcomes.length }} 项</span></legend>
        <div class="expected-grid">
          <label v-for="outcome in expectedOutcomeOptions" :key="outcome.value" class="expected-card">
            <input type="checkbox" :checked="contextDraft.expected_outcomes.includes(outcome.value)" @change="emit('toggle-expected-outcome', outcome.value)">
            <span>{{ outcome.label }}</span>
          </label>
        </div>
        <div v-if="contextDraft.expected_outcomes.includes('其他')" class="form-group other-detail-field">
          <label class="form-label" for="assessment-expected-outcomes-other">补充其他期待（选填）</label>
          <textarea id="assessment-expected-outcomes-other" :value="contextDraft.expected_outcomes_other" rows="2" maxlength="500" placeholder="写下你希望从说明书中获得的其他帮助" @input="updateField('expected_outcomes_other', $event.target.value)"></textarea>
        </div>
        <p v-if="contextErrors.expected_outcomes" id="assessment-expected-outcomes-error" class="field-error" role="alert">{{ contextErrors.expected_outcomes }}</p>
      </fieldset>

      <div class="context-details">
        <AssessmentDisclosureToggle
          title="补充背景"
          description="选填，能让建议更贴近你"
          :expanded="showAdvancedContext"
          controls="assessment-advanced-context"
          @toggle="emit('toggle-advanced-context')"
        />
        <div id="assessment-advanced-context" v-show="showAdvancedContext" class="advanced-context-grid">
          <div class="form-group">
            <label class="form-label" for="assessment-issue-duration">这个困惑持续多久了</label>
            <select id="assessment-issue-duration" :value="contextDraft.issue_duration" @change="updateField('issue_duration', $event.target.value)">
              <option value="">暂不填写</option>
              <option value="近1周内">近 1 周内</option>
              <option value="近1个月内">近 1 个月内</option>
              <option value="近半年">近半年</option>
              <option value="一直存在">说不清楚，感觉一直存在</option>
              <option value="暂无">暂无</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="assessment-impact-level">对生活的影响程度</label>
            <select id="assessment-impact-level" :value="contextDraft.impact_level" @change="updateField('impact_level', $event.target.value)">
              <option value="">暂不填写</option>
              <option value="none">几乎不影响</option>
              <option value="some">有些影响</option>
              <option value="serious">严重影响日常生活</option>
              <option value="暂无">暂无</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="assessment-decision-status">最近是否面临重要决策</label>
            <select id="assessment-decision-status" :value="contextDraft.decision_status" @change="updateField('decision_status', $event.target.value)">
              <option value="">暂不填写</option>
              <option value="yes">是</option>
              <option value="no">否</option>
              <option value="uncertain">不确定，正在犹豫中</option>
            </select>
          </div>
          <div v-if="contextDraft.decision_status === 'yes' || contextDraft.decision_status === 'uncertain'" class="form-group">
            <label class="form-label" for="assessment-decision-description">重要决策描述</label>
            <input id="assessment-decision-description" :value="contextDraft.decision_description" type="text" maxlength="1000" placeholder="例如：是否接受一份新的工作机会" @input="updateField('decision_description', $event.target.value)">
          </div>
          <fieldset class="form-group choice-fieldset field-wide">
            <legend class="form-label">做重要决定时，通常会怎么做 <span class="form-hint">最多选择 6 项</span></legend>
            <div class="expected-grid decision-grid">
              <label v-for="style in decisionStyleOptions" :key="style.value" class="expected-card">
                <input type="checkbox" :checked="contextDraft.decision_style.includes(style.value)" @change="emit('toggle-decision-style', style.value)">
                <span>{{ style.label }}</span>
              </label>
            </div>
            <div v-if="contextDraft.decision_style.includes('other')" class="form-group other-detail-field">
              <label class="form-label" for="assessment-decision-style-other">补充其他决策方式（选填）</label>
              <textarea id="assessment-decision-style-other" :value="contextDraft.decision_style_other" rows="2" maxlength="500" placeholder="写下你通常会采用的其他方式" @input="updateField('decision_style_other', $event.target.value)"></textarea>
            </div>
          </fieldset>
          <div class="form-group field-wide">
            <label class="form-label" for="assessment-additional-info">还想告诉我们的事</label>
            <textarea id="assessment-additional-info" :value="contextDraft.additional_info" rows="4" maxlength="2000" placeholder="任何你觉得与这一次问题有关的背景信息或期待" @input="updateField('additional_info', $event.target.value)"></textarea>
            <div class="field-meta">
              <span></span>
              <span class="char-count" aria-live="polite">{{ String(contextDraft.additional_info || '').length }}/2000</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="contextErrorSummary.length" class="error-summary" role="alert" aria-live="assertive">
        <strong>请先补充本次申请信息</strong>
        <ul><li v-for="error in contextErrorSummary" :key="error">{{ error }}</li></ul>
      </div>
      <p v-if="formMessage" class="form-message" role="alert" aria-live="assertive">{{ formMessage }}</p>
      <div class="button-row form-submit-bar">
        <VanButton type="default" native-type="button" class="secondary-button" @click="emit('edit-profile')">修改档案</VanButton>
        <VanButton type="primary" native-type="submit" class="primary-button" :disabled="submitting" :aria-busy="submitting">{{ submitting ? '提交中…' : isEditingRequest ? '更新并重新提交' : '提交报告申请' }}</VanButton>
      </div>
    </form>
  </div>
</template>
