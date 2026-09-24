<template>
  <div class="page-shell assessment-page">
    <BrandNav />

    <section class="page-header">
      <div class="container header-inner">
        <p class="section-kicker">FI / YOUR LIFE MANUAL</p>
        <h1>生成你的人生说明书</h1>
        <p>先建立一份可复用的个人档案，再把这一次真正想看的问题交给说明书。</p>
      </div>
    </section>

    <section class="section-band assessment-section">
      <div class="container assessment-container">
        <div class="progress-card paper-card" aria-label="申请进度">
          <div class="progress-current" aria-live="polite">
            <span>申请进度</span>
            <strong>第 {{ currentStep }} 步 · {{ currentStepLabel }}</strong>
            <span>{{ stepProgress }}%</span>
          </div>
          <div class="progress-step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
            <span>1</span><p>个人档案</p>
          </div>
          <div class="progress-line" :class="{ active: currentStep > 1 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
            <span>2</span><p>本次问题</p>
          </div>
          <div class="progress-line" :class="{ active: currentStep > 2 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 3 }">
            <span>3</span><p>生成说明书</p>
          </div>
        </div>

        <div v-if="loadingProfile" class="step-content form-panel loading-panel" aria-live="polite">
          <div class="loading-compass" aria-hidden="true"></div>
          <h2>正在读取你的个人档案</h2>
          <p>只需要等待片刻，已有资料不会要求你重新填写。</p>
        </div>

        <div v-else-if="currentStep === 1" class="step-content form-panel">
          <div class="step-heading">
            <p class="section-kicker">STEP 01</p>
            <h2 ref="stepHeading" tabindex="-1">{{ hasExistingProfile ? '确认你的个人档案' : '建立你的个人档案' }}</h2>
            <p>{{ hasExistingProfile ? '档案会用于后续报告与日历申请。你可以只修改发生变化的内容。' : '核心资料用于建立命理基础，画像信息先填你愿意分享的部分。' }}</p>
            <div v-if="draftRestored || draftStatus" class="draft-status" role="status" aria-live="polite">
              <span class="draft-status-dot" aria-hidden="true"></span>
              <span>{{ draftRestored ? '已恢复上次未完成的草稿，你可以继续编辑。' : draftStatus }}</span>
            </div>
          </div>

          <form class="assessment-form" novalidate @submit.prevent="saveProfileAndContinue">
            <ProfileFields
              v-model="profileDraft"
              id-prefix="assessment-profile"
              :show-optional="showOptionalProfile"
              :errors="profileErrors"
            />

            <button type="button" class="fold-toggle" :aria-expanded="showOptionalProfile" @click="showOptionalProfile = !showOptionalProfile">
              <span>{{ showOptionalProfile ? '收起个人画像选填项' : '完善个人画像（选填，之后可修改）' }}</span>
              <span aria-hidden="true">{{ showOptionalProfile ? '−' : '+' }}</span>
            </button>

            <div class="privacy-note">
              <span class="privacy-mark" aria-hidden="true">私</span>
              <p>姓名和出生资料只用于你的账户服务。当前困惑、关系和身心状态不会自动写入长期档案。</p>
            </div>

            <div v-if="profileErrorSummary.length" class="error-summary" role="alert" aria-live="assertive">
              <strong>请先检查以下内容</strong>
              <ul><li v-for="error in profileErrorSummary" :key="error">{{ error }}</li></ul>
            </div>
            <p v-if="formMessage" class="form-message" role="alert" aria-live="assertive">{{ formMessage }}</p>
            <div class="form-submit-bar">
              <button type="submit" class="primary-button full-width" :disabled="savingProfile" :aria-busy="savingProfile">
                {{ savingProfile ? '保存中…' : '保存档案并继续' }}
              </button>
            </div>
          </form>
        </div>

        <div v-else-if="currentStep === 2" class="step-content form-panel">
          <div class="step-heading">
            <p class="section-kicker">STEP 02</p>
            <h2 ref="stepHeading" tabindex="-1">这一次，你想看什么</h2>
            <p>当前问题只属于本次报告。每次申请都可以换一个问题，不会覆盖你的个人档案。</p>
            <div v-if="draftRestored || draftStatus" class="draft-status" role="status" aria-live="polite">
              <span class="draft-status-dot" aria-hidden="true"></span>
              <span>{{ draftRestored ? '已恢复上次未完成的草稿，你可以继续编辑。' : draftStatus }}</span>
            </div>
          </div>

          <ProfileSummary :profile="profileDraft" :profile-version="profileVersion" :last-confirmed-at="profileLastConfirmedAt" @edit="editProfile" />

          <div v-if="lastContext" class="reuse-context-card">
            <div>
              <span class="mini-label">上次申请背景</span>
              <p>{{ truncate(lastContext.current_challenge, 96) || '已保存上次报告的情境' }}</p>
            </div>
            <button type="button" class="secondary-button small-button" @click="reusePreviousContext">沿用上次背景并编辑</button>
          </div>
          <p v-if="contextMessage" class="context-message" role="status">{{ contextMessage }}</p>
          <p class="context-scope-note">本次困惑、关系和身心状态只用于这份申请，默认不会写入长期档案。</p>

          <form class="assessment-form context-form" novalidate @submit.prevent="submitAssessment">
            <fieldset class="form-group choice-fieldset" :aria-describedby="contextErrors.focus_topics ? 'assessment-focus-topics-error' : undefined">
              <legend class="form-label">当前最关注的生活领域 <span class="required">*</span> <span class="form-hint">最多选择 3 项</span> <span class="selection-count">{{ contextDraft.focus_topics.length }}/3</span></legend>
              <div class="topics-grid">
                <button
                  v-for="topic in topics"
                  :key="topic.id"
                  type="button"
                  class="topic-card"
                  :class="{ selected: contextDraft.focus_topics.includes(topic.id) }"
                  :aria-pressed="contextDraft.focus_topics.includes(topic.id)"
                  @click="toggleTopic(topic.id)"
                >
                  <strong>{{ topic.title }}</strong>
                  <small>{{ topic.desc }}</small>
                </button>
              </div>
              <p v-if="contextErrors.focus_topics" id="assessment-focus-topics-error" class="field-error" role="alert">{{ contextErrors.focus_topics }}</p>
            </fieldset>

            <div class="form-group">
              <label class="form-label" for="assessment-current-challenge">现在面临的最大困惑或挑战 <span class="required">*</span></label>
              <textarea id="assessment-current-challenge" v-model="contextDraft.current_challenge" rows="5" maxlength="2000" placeholder="请尽可能具体地描述：发生了什么，你卡在哪里？" :aria-invalid="Boolean(contextErrors.current_challenge)" :aria-describedby="contextErrors.current_challenge ? 'assessment-current-challenge-error' : 'assessment-current-challenge-hint'" @blur="validateContextField('current_challenge')"></textarea>
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
                  <input type="checkbox" :checked="contextDraft.expected_outcomes.includes(outcome.value)" @change="toggleExpectedOutcome(outcome.value)">
                  <span>{{ outcome.label }}</span>
                </label>
              </div>
              <p v-if="contextErrors.expected_outcomes" id="assessment-expected-outcomes-error" class="field-error" role="alert">{{ contextErrors.expected_outcomes }}</p>
            </fieldset>

            <details class="context-details" :open="showAdvancedContext">
              <summary @click.prevent="showAdvancedContext = !showAdvancedContext">
                <span>补充背景（选填，能让建议更贴近你）</span><span aria-hidden="true">{{ showAdvancedContext ? '−' : '+' }}</span>
              </summary>
              <div v-if="showAdvancedContext" class="advanced-context-grid">
                <div class="form-group">
                  <label class="form-label" for="assessment-issue-duration">这个困惑持续多久了</label>
                  <select id="assessment-issue-duration" v-model="contextDraft.issue_duration">
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
                  <select id="assessment-impact-level" v-model="contextDraft.impact_level">
                    <option value="">暂不填写</option>
                    <option value="none">几乎不影响</option>
                    <option value="some">有些影响</option>
                    <option value="serious">严重影响日常生活</option>
                    <option value="暂无">暂无</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label" for="assessment-decision-status">最近是否面临重要决策</label>
                  <select id="assessment-decision-status" v-model="contextDraft.decision_status">
                    <option value="">暂不填写</option>
                    <option value="yes">是</option>
                    <option value="no">否</option>
                    <option value="uncertain">不确定，正在犹豫中</option>
                  </select>
                </div>
                <div v-if="contextDraft.decision_status === 'yes' || contextDraft.decision_status === 'uncertain'" class="form-group">
                  <label class="form-label" for="assessment-decision-description">重要决策描述</label>
                  <input id="assessment-decision-description" v-model="contextDraft.decision_description" type="text" maxlength="1000" placeholder="例如：是否接受一份新的工作机会">
                </div>
                <fieldset class="form-group choice-fieldset field-wide">
                  <legend class="form-label">做重要决定时，通常会怎么做 <span class="form-hint">最多选择 6 项</span></legend>
                  <div class="expected-grid decision-grid">
                    <label v-for="style in decisionStyleOptions" :key="style.value" class="expected-card">
                      <input type="checkbox" :checked="contextDraft.decision_style.includes(style.value)" @change="toggleDecisionStyle(style.value)">
                      <span>{{ style.label }}</span>
                    </label>
                  </div>
                </fieldset>
                <div class="form-group field-wide">
                  <label class="form-label" for="assessment-additional-info">还想告诉我们的事</label>
                  <textarea id="assessment-additional-info" v-model="contextDraft.additional_info" rows="4" maxlength="2000" placeholder="任何你觉得与这一次问题有关的背景信息或期待"></textarea>
                  <div class="field-meta">
                    <span></span>
                    <span class="char-count" aria-live="polite">{{ String(contextDraft.additional_info || '').length }}/2000</span>
                  </div>
                </div>
              </div>
            </details>

            <div v-if="contextErrorSummary.length" class="error-summary" role="alert" aria-live="assertive">
              <strong>请先补充本次申请信息</strong>
              <ul><li v-for="error in contextErrorSummary" :key="error">{{ error }}</li></ul>
            </div>
            <p v-if="formMessage" class="form-message" role="alert" aria-live="assertive">{{ formMessage }}</p>
            <div class="button-row form-submit-bar">
              <button type="button" class="secondary-button" @click="editProfile">修改档案</button>
              <button type="submit" class="primary-button" :disabled="submitting" :aria-busy="submitting">{{ submitting ? '提交中…' : '生成我的说明书' }}</button>
            </div>
          </form>
        </div>

        <div v-else class="step-content form-panel">
          <div v-if="isGenerating" class="generating">
            <div class="loading-compass" aria-hidden="true"></div>
            <h2 ref="stepHeading" tabindex="-1">正在为你生成专属报告</h2>
            <p>你的个人特质、当下处境与关注的议题，正在汇成一张更清晰的自我地图。</p>
            <div class="generating-steps">
              <div class="gen-step" :class="{ active: genStep >= 1 }">认识你的起点</div>
              <div class="gen-step" :class="{ active: genStep >= 2 }">看见你的特质</div>
              <div class="gen-step" :class="{ active: genStep >= 3 }">找到重复模式</div>
              <div class="gen-step" :class="{ active: genStep >= 4 }">获得下一步提示</div>
            </div>
          </div>

          <div v-else class="result-success">
            <span class="seal-badge">已生成</span>
            <h2 ref="stepHeading" tabindex="-1">你的人生说明书已经完成</h2>
            <p>这份报告保留了提交时的资料快照。之后更新档案，不会改变这份历史报告。</p>
            <div class="result-preview paper-card">
              <div><span>个人属性</span><strong>{{ reportPreview.energyType }}</strong></div>
              <div><span>核心特质</span><strong>{{ reportPreview.coreTraits }}</strong></div>
              <div><span>行动提示</span><strong>{{ reportPreview.talents }}</strong></div>
            </div>
            <div class="button-row">
              <button type="button" class="primary-button" @click="viewFullReport">查看报告</button>
              <button type="button" class="secondary-button" @click="goToCalendar">打开决策日历</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { generateReportWithAI, getLatestReportContext } from '../utils/aiService.js'
import { getCurrentUser, updateUserProfile } from '../utils/authService.js'
import { setAuthenticatedUser } from '../stores/auth.js'
import ProfileFields from '../components/ProfileFields.vue'
import ProfileSummary from '../components/ProfileSummary.vue'

const STORAGE_KEY = 'assessment-intake-draft'

function emptyProfile() {
  return {
    name: '', gender: '', calendar_type: 'solar', birth_year: null, birth_month: null, birth_day: null,
    birth_hour: null, birth_minute: null, birth_place: '', birth_time_precision: 'unknown',
    current_residence: '', marital_status: '', occupation_status: '', highest_education: '', mbti: '',
    personality_keywords: [], strengths: '', limitations: '', mingli_experience: [], mingli_attitude: '',
    preferred_content_depth: '', default_usage_scenarios: []
  }
}

function emptyContext() {
  return {
    focus_topics: [], current_challenge: '', expected_outcomes: [], issue_duration: '', impact_level: '',
    decision_status: '', decision_description: '', decision_style: [], additional_info: ''
  }
}

function profileFromUser(user) {
  const base = emptyProfile()
  Object.keys(base).forEach(field => {
    if (user[field] !== undefined && user[field] !== null) base[field] = Array.isArray(user[field]) ? [...user[field]] : user[field]
  })
  return base
}

export default {
  name: 'Assessment',
  components: { ProfileFields, ProfileSummary },
  data() {
    return {
      currentStep: 1,
      loadingProfile: true,
      savingProfile: false,
      submitting: false,
      isGenerating: false,
      genStep: 0,
      formMessage: '',
      contextMessage: '',
      showOptionalProfile: false,
      showAdvancedContext: false,
      hasExistingProfile: false,
      profileDraft: emptyProfile(),
      profileVersion: 1,
      profileLastConfirmedAt: null,
      profileErrors: {},
      contextDraft: emptyContext(),
      contextErrors: {},
      draftStatus: '',
      draftRestored: false,
      draftSavedAt: null,
      lastContext: null,
      lastContextReportId: null,
      reportPreview: { energyType: '综合型', coreTraits: '独特的个人特质', talents: '多元发展' },
      generatedReport: null,
      currentReportId: null,
      topics: [
        { id: 'career', title: '事业发展', desc: '职业选择、转型与瓶颈突破' },
        { id: 'relationship', title: '感情关系', desc: '恋爱、婚姻与关系模式' },
        { id: 'family', title: '家庭议题', desc: '原生家庭、亲子与家庭沟通' },
        { id: 'finance', title: '财务规划', desc: '经济安排与资源分配' },
        { id: 'health', title: '身心健康', desc: '压力、情绪与身心节奏' },
        { id: 'social', title: '人际关系', desc: '社交圈、朋友与边界' },
        { id: 'self', title: '个人成长', desc: '自我实现与认知提升' },
        { id: 'children', title: '子女教育', desc: '陪伴、沟通与成长支持' },
        { id: 'other', title: '其他', desc: '你想带入说明书的主题' }
      ],
      expectedOutcomeOptions: [
        { value: '认识自己', label: '更清晰地认识自己' },
        { value: '解决方案', label: '找到当前问题的解决方案' },
        { value: '方向指引', label: '获得对未来方向的指引' },
        { value: '验证判断', label: '验证自己已有的判断' },
        { value: '心理支持', label: '获得心理上的安慰与支持' },
        { value: '节奏参考', label: '了解自己的命理 / 运势节奏' },
        { value: '其他', label: '其他' }
      ],
      decisionStyleOptions: [
        { value: 'intuition', label: '凭直觉判断' },
        { value: 'rational', label: '理性分析利弊' },
        { value: 'family_friends', label: '咨询家人 / 朋友意见' },
        { value: 'professional', label: '寻求专业人士建议' },
        { value: 'wait', label: '顺其自然，等时间给答案' },
        { value: 'other', label: '其他' }
      ]
    }
  },
  computed: {
    profileErrorSummary() {
      return Object.values(this.profileErrors)
    },
    contextErrorSummary() {
      return Object.values(this.contextErrors)
    },
    currentStepLabel() {
      return ['个人档案', '本次问题', '生成说明书'][this.currentStep - 1] || '申请'
    },
    stepProgress() {
      return Math.round((this.currentStep / 3) * 100)
    }
  },
  watch: {
    profileDraft: { deep: true, handler: 'saveDraft' },
    contextDraft: { deep: true, handler: 'saveDraft' }
  },
  async mounted() {
    try {
      const user = await getCurrentUser()
      this.profileDraft = profileFromUser(user)
      this.profileVersion = user.profile_version || 1
      this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
      this.hasExistingProfile = Number(user.profile_completion || 0) >= 100
      this.restoreDraft()
    } catch (error) {
      this.formMessage = error.response?.data?.detail || '暂时无法读取个人档案，请刷新后重试。'
    }
    try {
      const latest = await getLatestReportContext()
      if (latest?.context) {
        this.lastContext = latest.context
        this.lastContextReportId = latest.report_id
      }
    } catch (error) {
      // The report form remains usable if a legacy deployment has no context endpoint yet.
      console.warn('读取上次申请背景失败', error)
    } finally {
      this.loadingProfile = false
    }
  },
  methods: {
    saveDraft() {
      if (this.loadingProfile) return
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ profileVersion: this.profileVersion, profile: this.profileDraft, context: this.contextDraft }))
        this.draftSavedAt = new Date()
        this.draftStatus = '草稿已自动保存 · 刚刚'
      } catch {
        // Draft recovery is a convenience; it should never block form input.
      }
    },
    restoreDraft() {
      try {
        const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null')
        if (!stored) return
        if (stored.profileVersion === this.profileVersion && stored.profile) {
          this.profileDraft = { ...this.profileDraft, ...stored.profile }
          this.draftRestored = true
        }
        if (stored.context) {
          this.contextDraft = { ...emptyContext(), ...stored.context }
          this.draftRestored = true
        }
      } catch {
        sessionStorage.removeItem(STORAGE_KEY)
      }
    },
    validateProfile() {
      const profile = this.profileDraft
      const errors = {}
      if (!String(profile.name || '').trim()) errors.name = '请填写称呼。'
      if (!profile.gender) errors.gender = '请选择性别。'
      if (!profile.calendar_type) errors.calendar_type = '请选择历法类型。'
      const year = Number(profile.birth_year)
      const month = Number(profile.birth_month)
      const day = Number(profile.birth_day)
      if (!year || year < 1900 || year > new Date().getFullYear()) errors.birth_date = '请填写有效的出生日期。'
      else if (!month || month < 1 || month > 12 || !day || day < 1 || day > 31) errors.birth_date = '请填写完整的出生日期。'
      else if (profile.calendar_type === 'solar') {
        const date = new Date(year, month - 1, day)
        if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) errors.birth_date = '公历出生日期不存在，请检查日期。'
      } else if (day > 30) errors.birth_date = '农历日期的日期不能超过 30。'
      if (!['unknown', 'approximate', 'exact'].includes(profile.birth_time_precision)) errors.birth_time_precision = '请选择出生时间准确度。'
      if (profile.birth_time_precision !== 'unknown') {
        if (profile.birth_hour === null || profile.birth_hour === '' || profile.birth_hour === undefined || profile.birth_minute === null || profile.birth_minute === '' || profile.birth_minute === undefined) errors.birth_time = '请选择完整的出生小时和分钟。'
        else if (Number(profile.birth_hour) > 23 || Number(profile.birth_minute) > 59) errors.birth_time = '出生时间范围不正确。'
      }
      this.profileErrors = errors
      return Object.keys(errors).length === 0
    },
    profilePayload() {
      const profile = { ...this.profileDraft }
      profile.name = String(profile.name || '').trim()
      profile.birth_place = String(profile.birth_place || '').trim() || null
      profile.current_residence = String(profile.current_residence || '').trim() || null
      profile.mbti = String(profile.mbti || '').trim().toUpperCase() || null
      ;['strengths', 'limitations', 'marital_status', 'occupation_status', 'highest_education', 'mingli_attitude', 'preferred_content_depth'].forEach(field => {
        profile[field] = String(profile[field] || '').trim() || null
      })
      profile.personality_keywords = Array.isArray(profile.personality_keywords) ? profile.personality_keywords : []
      profile.mingli_experience = Array.isArray(profile.mingli_experience) ? profile.mingli_experience : []
      profile.default_usage_scenarios = Array.isArray(profile.default_usage_scenarios) ? profile.default_usage_scenarios : []
      profile.birth_year = profile.birth_year ? Number(profile.birth_year) : null
      profile.birth_month = profile.birth_month ? Number(profile.birth_month) : null
      profile.birth_day = profile.birth_day ? Number(profile.birth_day) : null
      profile.birth_hour = profile.birth_time_precision === 'unknown' || profile.birth_hour === '' ? null : Number(profile.birth_hour)
      profile.birth_minute = profile.birth_time_precision === 'unknown' || profile.birth_minute === '' ? null : Number(profile.birth_minute)
      return profile
    },
    async saveProfileAndContinue() {
      this.formMessage = ''
      if (!this.validateProfile()) {
        this.formMessage = '请先补充个人档案中的必填项。'
        this.focusStepHeading()
        return
      }
      this.savingProfile = true
      try {
        const user = await updateUserProfile(this.profilePayload())
        setAuthenticatedUser(user)
        this.profileDraft = profileFromUser(user)
        this.profileVersion = user.profile_version || this.profileVersion
        this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
        this.hasExistingProfile = true
        this.draftStatus = `档案已确认 · 版本 v${this.profileVersion}`
        this.currentStep = 2
        this.focusStepHeading()
      } catch (error) {
        this.formMessage = error.response?.data?.detail || '档案保存失败，请检查网络后重试。'
      } finally {
        this.savingProfile = false
      }
    },
    editProfile() {
      this.formMessage = ''
      this.currentStep = 1
      this.focusStepHeading()
    },
    toggleTopic(topicId) {
      const topics = [...this.contextDraft.focus_topics]
      const index = topics.indexOf(topicId)
      if (index >= 0) topics.splice(index, 1)
      else if (topics.length < 3) topics.push(topicId)
      this.contextDraft.focus_topics = topics
      if (topics.length) delete this.contextErrors.focus_topics
    },
    toggleExpectedOutcome(value) {
      const outcomes = [...this.contextDraft.expected_outcomes]
      const index = outcomes.indexOf(value)
      if (index >= 0) outcomes.splice(index, 1)
      else if (outcomes.length < 7) outcomes.push(value)
      this.contextDraft.expected_outcomes = outcomes
      if (outcomes.length) delete this.contextErrors.expected_outcomes
    },
    toggleDecisionStyle(value) {
      const styles = [...this.contextDraft.decision_style]
      const index = styles.indexOf(value)
      if (index >= 0) styles.splice(index, 1)
      else if (styles.length < 6) styles.push(value)
      this.contextDraft.decision_style = styles
    },
    validateContextField(field) {
      if (field === 'current_challenge' && String(this.contextDraft.current_challenge || '').trim()) delete this.contextErrors.current_challenge
    },
    validateContext() {
      const errors = {}
      if (!this.contextDraft.focus_topics.length) errors.focus_topics = '至少选择一个关注领域。'
      if (!String(this.contextDraft.current_challenge || '').trim()) errors.current_challenge = '请描述当前困惑或挑战。'
      if (!this.contextDraft.expected_outcomes.length) errors.expected_outcomes = '至少选择一个期望获得的结果。'
      this.contextErrors = errors
      return Object.keys(errors).length === 0
    },
    reusePreviousContext() {
      this.contextDraft = { ...emptyContext(), ...(this.lastContext || {}), focus_topics: [...(this.lastContext?.focus_topics || [])], expected_outcomes: [...(this.lastContext?.expected_outcomes || [])], decision_style: [...(this.lastContext?.decision_style || [])] }
      this.contextMessage = this.lastContextReportId ? `已带入报告 #${this.lastContextReportId} 的背景，请按这一次的情况编辑。` : '已带入上次背景，请按这一次的情况编辑。'
      this.$nextTick(() => document.getElementById('assessment-current-challenge')?.focus())
    },
    async submitAssessment() {
      if (this.submitting) return
      this.formMessage = ''
      if (!this.validateContext()) {
        this.formMessage = '请先补充本次申请的必填信息。'
        this.showAdvancedContext = true
        this.focusStepHeading()
        return
      }
      this.submitting = true
      this.currentStep = 3
      this.isGenerating = true
      this.focusStepHeading()
      try {
        this.genStep = 1
        await new Promise(resolve => setTimeout(resolve, 350))
        this.genStep = 2
        this.generatedReport = await generateReportWithAI({ profile_version: this.profileVersion, context: this.contextDraft })
        this.genStep = 3
        await new Promise(resolve => setTimeout(resolve, 350))
        this.genStep = 4
        this.reportPreview = {
          energyType: this.generatedReport.energyProfile?.type || '综合型',
          coreTraits: this.generatedReport.energyProfile?.coreTraits || '独特的个人特质',
          talents: Array.isArray(this.generatedReport.careerGuidance?.suitablePaths) ? this.generatedReport.careerGuidance.suitablePaths.join('、') : '多元发展'
        }
        await new Promise(resolve => setTimeout(resolve, 350))
        this.currentReportId = this.generatedReport.id
        this.isGenerating = false
        sessionStorage.removeItem(STORAGE_KEY)
        this.draftStatus = ''
        this.draftRestored = false
      } catch (error) {
        console.error('报告生成失败:', error)
        this.formMessage = error.response?.data?.detail || error.message || '报告生成失败，请检查网络后重试。'
        this.currentStep = 2
        this.isGenerating = false
        this.focusStepHeading()
      } finally {
        this.submitting = false
      }
    },
    focusStepHeading() {
      this.$nextTick(() => {
        const heading = Array.isArray(this.$refs.stepHeading) ? this.$refs.stepHeading[0] : this.$refs.stepHeading
        if (!heading) return
        window.scrollTo({ top: 0, behavior: 'auto' })
        heading.focus({ preventScroll: true })
      })
    },
    truncate(value, length) {
      const text = String(value || '')
      return text.length > length ? `${text.slice(0, length)}…` : text
    },
    viewFullReport() {
      if (this.currentReportId) this.$router.push(`/pages/report/detail?id=${this.currentReportId}`)
    },
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    }
  }
}
</script>

<style scoped>
.page-header {
  padding: 82px 0 58px;
  text-align: center;
}

.header-inner { max-width: 760px; }

.page-header h1 { font-size: clamp(40px, 8vw, 72px); line-height: 1.08; }

.page-header p:not(.section-kicker) {
  margin-top: 18px;
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1.75;
}

.assessment-section { padding-bottom: 84px; }
.assessment-container { max-width: 900px; }

.progress-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
  padding: 14px;
}

.progress-current {
  display: none;
}

.progress-step { display: grid; justify-items: center; gap: 7px; width: 80px; color: var(--muted); }
.progress-step span { display: grid; width: 34px; height: 34px; place-items: center; border: 1px solid var(--line); border-radius: 50%; background: rgba(255,250,240,.72); font-weight: 900; }
.progress-step p { font-size: 12px; font-weight: 800; white-space: nowrap; }
.progress-step.active, .progress-step.completed { color: var(--cinnabar-deep); }
.progress-step.active span, .progress-step.completed span { border-color: rgba(184,92,80,.34); background: rgba(184,92,80,.1); }
.progress-line { height: 1px; background: var(--line); }
.progress-line.active { background: linear-gradient(90deg, var(--cinnabar), var(--gold)); }

.step-content { padding: clamp(20px, 4vw, 38px); }
.step-heading { margin-bottom: 26px; text-align: center; }
.step-heading h2 { font-size: clamp(26px, 5vw, 40px); line-height: 1.2; }
.step-heading p:not(.section-kicker) { margin-top: 10px; color: var(--ink-soft); line-height: 1.65; }
.draft-status { display: inline-flex; align-items: center; justify-content: center; gap: 7px; margin-top: 12px; color: var(--jade); font-size: 12px; line-height: 1.5; }
.draft-status-dot { width: 7px; height: 7px; flex: 0 0 auto; border-radius: 50%; background: var(--jade); box-shadow: 0 0 0 4px rgba(111,159,147,.1); }
.assessment-form { display: grid; gap: 22px; }
.context-form { margin-top: 24px; }
.form-group { display: grid; gap: 10px; }
.form-label { color: var(--ink); font-weight: 800; }
.required { color: var(--cinnabar-deep); }
.form-hint { color: var(--muted); font-size: 12px; font-weight: 500; }
.field-meta { display: flex; align-items: start; justify-content: space-between; gap: 12px; }
.char-count { flex: 0 0 auto; color: var(--muted); font-size: 11px; line-height: 1.6; }
.field-error { color: var(--cinnabar-deep); font-size: 12px; line-height: 1.5; }
.selection-count { color: var(--cinnabar-deep); font-size: 11px; font-weight: 800; white-space: nowrap; }
.choice-fieldset { min-width: 0; border: 0; padding: 0; }

textarea, select, .context-form input[type="text"] {
  width: 100%;
  min-height: 48px;
  border: 1px solid rgba(139,90,20,.2);
  border-radius: 12px;
  padding: 11px 13px;
  background: rgba(255,255,255,.78);
  color: var(--ink);
  font-size: 16px;
  line-height: 1.5;
}

textarea { min-height: 110px; resize: vertical; }
textarea:focus, select:focus, .context-form input[type="text"]:focus { border-color: var(--cinnabar); outline: 0; box-shadow: 0 0 0 3px rgba(184,92,80,.12); }

.fold-toggle {
  display: flex;
  min-height: 48px;
  align-items: center;
  justify-content: space-between;
  border: 1px dashed rgba(139,90,20,.3);
  border-radius: 13px;
  padding: 0 14px;
  color: var(--cinnabar-deep);
  font-size: 14px;
  font-weight: 800;
  text-align: left;
}
.fold-toggle:hover { background: rgba(184,92,80,.06); }

.privacy-note, .reuse-context-card {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 14px;
  padding: 13px 15px;
  background: rgba(111,159,147,.09);
}
.privacy-mark { display: grid; width: 28px; height: 28px; flex: 0 0 auto; place-items: center; border: 1px solid rgba(111,159,147,.4); border-radius: 50%; color: var(--jade); font-size: 12px; font-weight: 900; }
.privacy-note p { color: var(--ink-soft); font-size: 12px; line-height: 1.6; }

.reuse-context-card { justify-content: space-between; background: rgba(217,186,98,.1); }
.reuse-context-card > div { min-width: 0; }
.reuse-context-card p { margin-top: 3px; overflow: hidden; color: var(--ink-soft); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.mini-label { color: var(--gold-deep); font-size: 11px; font-weight: 900; letter-spacing: .08em; }
.context-message { color: var(--jade); font-size: 13px; }
.context-scope-note { margin-top: 12px; color: var(--muted); font-size: 12px; line-height: 1.6; }

.topics-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
.topic-card {
  display: grid;
  min-height: 86px;
  align-content: center;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 15px;
  padding: 12px;
  background: rgba(255,250,240,.64);
  color: var(--ink);
  text-align: left;
  transition: border-color .2s ease, background .2s ease, transform .2s ease;
}
.topic-card:hover { border-color: rgba(184,92,80,.45); transform: translateY(-1px); }
.topic-card.selected { border-color: var(--cinnabar); background: rgba(184,92,80,.1); color: var(--cinnabar-deep); }
.topic-card strong { font-size: 14px; }
.topic-card small { color: var(--muted); font-size: 11px; line-height: 1.45; }

.expected-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 8px; }
.expected-card { display: flex; min-height: 46px; align-items: center; gap: 9px; border: 1px solid var(--line); border-radius: 11px; padding: 8px 10px; background: rgba(255,255,255,.52); color: var(--ink-soft); font-size: 13px; line-height: 1.35; }
.expected-card input { width: 17px; height: 17px; flex: 0 0 auto; accent-color: var(--cinnabar); }
.context-details { border-top: 1px solid var(--line); padding-top: 6px; }
.context-details summary { display: flex; min-height: 48px; align-items: center; justify-content: space-between; color: var(--cinnabar-deep); cursor: pointer; font-size: 14px; font-weight: 800; list-style: none; }
.context-details summary::-webkit-details-marker { display: none; }
.advanced-context-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 18px; padding: 12px 0 4px; }
.field-wide { grid-column: 1 / -1; }

.error-summary { border: 1px solid rgba(158,63,53,.25); border-radius: 12px; padding: 12px 14px; background: rgba(184,92,80,.07); color: var(--cinnabar-deep); font-size: 13px; }
.error-summary ul { margin: 5px 0 0 18px; list-style: disc; }
.error-summary li { list-style: disc; }
.form-message { color: var(--cinnabar-deep); font-size: 14px; line-height: 1.6; }
.button-row { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }
.form-submit-bar { position: relative; }
.primary-button, .secondary-button { display: inline-flex; min-height: var(--button-height); align-items: center; justify-content: center; border-radius: var(--button-radius); padding: 0 22px; font-size: 14px; font-weight: 800; }
.primary-button { background: var(--cinnabar); color: #fff; }
.primary-button:hover { background: var(--cinnabar-deep); }
.primary-button:disabled, .secondary-button:disabled { cursor: wait; opacity: .62; }
.secondary-button { border: 1px solid rgba(139,90,20,.22); background: rgba(255,255,255,.62); color: var(--ink-soft); }
.secondary-button:hover { border-color: var(--cinnabar); color: var(--cinnabar-deep); }
.small-button { min-height: 42px; padding: 0 14px; font-size: 12px; white-space: nowrap; }
.full-width { width: 100%; }

.loading-panel, .generating, .result-success { min-height: 360px; display: grid; place-items: center; align-content: center; gap: 15px; text-align: center; }
.loading-panel h2, .generating h2, .result-success h2 { font-size: clamp(26px, 5vw, 38px); }
.loading-panel p, .generating p, .result-success > p { max-width: 560px; color: var(--ink-soft); line-height: 1.7; }
.loading-compass { width: 58px; height: 58px; border: 1px solid rgba(184,92,80,.26); border-top-color: var(--cinnabar); border-radius: 50%; animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.generating-steps { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); width: min(620px, 100%); gap: 8px; margin-top: 15px; }
.gen-step { border-top: 2px solid var(--line); padding-top: 8px; color: var(--muted); font-size: 12px; }
.gen-step.active { border-color: var(--cinnabar); color: var(--cinnabar-deep); }
.seal-badge { display: inline-flex; min-height: 30px; align-items: center; border: 1px solid rgba(184,92,80,.26); border-radius: 999px; padding: 0 12px; color: var(--cinnabar-deep); font-size: 12px; font-weight: 900; }
.result-preview { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); width: 100%; gap: 12px; margin: 10px 0; padding: 18px; text-align: left; }
.result-preview div { display: grid; gap: 4px; min-width: 0; }
.result-preview span { color: var(--muted); font-size: 11px; }
.result-preview strong { color: var(--ink); font-size: 13px; line-height: 1.5; }

@media (max-width: 700px) {
  .page-header { padding: 60px 0 38px; }
  .progress-card { grid-template-columns: auto minmax(0, 1fr) auto minmax(0, 1fr) auto; gap: 4px; padding: 10px 7px; }
  .progress-current { display: flex; grid-column: 1 / -1; align-items: center; justify-content: space-between; gap: 8px; padding: 1px 3px 7px; color: var(--muted); font-size: 11px; }
  .progress-current strong { color: var(--ink-soft); font-size: 12px; }
  .progress-current span:last-child { color: var(--cinnabar-deep); font-weight: 900; }
  .progress-step { width: 64px; }
  .progress-step p { font-size: 10px; }
  .topics-grid, .advanced-context-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .reuse-context-card { align-items: start; flex-direction: column; }
  .result-preview { grid-template-columns: 1fr; }
  .form-submit-bar {
    position: sticky;
    bottom: calc(68px + var(--safe-bottom, 0px));
    z-index: 6;
    margin: 0 -4px;
    padding: 10px 4px;
    border-top: 1px solid rgba(139,90,20,.12);
    background: linear-gradient(180deg, rgba(255,250,240,.62), rgba(255,250,240,.97) 26%);
    box-shadow: 0 -10px 20px -18px rgba(47,36,27,.78);
  }
}

@media (max-width: 430px) {
  .assessment-section { padding-bottom: 78px; }
  .step-content { padding: 16px 12px; }
  .topics-grid, .expected-grid, .advanced-context-grid { grid-template-columns: 1fr; }
  .button-row > button { width: 100%; }
  .progress-current { padding-right: 1px; padding-left: 1px; }
  .progress-current span:first-child { display: none; }
  .generating-steps { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
</style>
