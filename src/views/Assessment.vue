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

        <AssessmentProfileStep
          v-else-if="currentStep === 1"
          ref="stepContent"
          :draft-restored="draftRestored"
          :draft-status="draftStatus"
          :form-message="formMessage"
          :has-existing-profile="hasExistingProfile"
          :profile-draft="profileDraft"
          :profile-error-summary="profileErrorSummary"
          :profile-errors="profileErrors"
          :saving-profile="savingProfile"
          :show-optional-profile="showOptionalProfile"
          @save-profile="saveProfileAndContinue"
          @update:profile-draft="profileDraft = $event"
          @update:show-optional-profile="showOptionalProfile = $event"
        />

        <AssessmentContextStep
          v-else-if="currentStep === 2"
          ref="stepContent"
          :context-draft="contextDraft"
          :context-error-summary="contextErrorSummary"
          :context-errors="contextErrors"
          :context-message="contextMessage"
          :decision-style-options="decisionStyleOptions"
          :draft-restored="draftRestored"
          :draft-status="draftStatus"
          :expected-outcome-options="expectedOutcomeOptions"
          :form-message="formMessage"
          :last-context="lastContext"
          :profile="profileDraft"
          :profile-last-confirmed-at="profileLastConfirmedAt"
          :profile-version="profileVersion"
          :show-advanced-context="showAdvancedContext"
          :submitting="submitting"
          :topics="topics"
          @edit-profile="editProfile"
          @reuse-context="reusePreviousContext"
          @submit-assessment="submitAssessment"
          @toggle-advanced-context="showAdvancedContext = !showAdvancedContext"
          @toggle-decision-style="toggleDecisionStyle"
          @toggle-expected-outcome="toggleExpectedOutcome"
          @toggle-topic="toggleTopic"
          @update:context-draft="contextDraft = $event"
          @validate-context-field="validateContextField"
        />

        <AssessmentResultStep
          v-else
          ref="stepContent"
          :gen-step="genStep"
          :is-generating="isGenerating"
          :report-preview="reportPreview"
          @go-to-calendar="goToCalendar"
          @view-report="viewFullReport"
        />
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script src="../features/assessment/page.js"></script>

<style scoped src="../features/assessment/assessment.css"></style>
