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
<script src="../features/assessment/page.js"></script>


<style scoped src="../features/assessment/assessment.css"></style>
