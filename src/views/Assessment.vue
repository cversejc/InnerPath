<template>
  <div class="page-shell assessment-page">
    <BrandNav />

    <BrandPageHeader
      eyebrow="YOUR LIFE MANUAL"
      title="书写你的人生说明书"
      description="先填写一份个人档案，再把当下想解决的问题告诉我们。"
      seal="见己"
    />

    <section class="section-band assessment-section">
      <div class="container assessment-container">
        <div class="progress-card paper-card" role="group" aria-label="人生说明书申请进度">
          <p class="progress-summary" role="status" aria-live="polite">
            <span>第 {{ currentStep }} 步 / 共 3 步</span>
            <strong>{{ currentStepLabel }}</strong>
          </p>
          <div class="progress-steps">
            <div class="progress-track" aria-hidden="true">
              <span :style="{ width: `${stepProgress}%` }"></span>
            </div>
            <ol class="progress-step-list" aria-label="申请步骤">
              <li class="progress-step" :class="{ active: currentStep === 1, completed: currentStep > 1 }" :aria-current="currentStep === 1 ? 'step' : undefined">
                <span class="progress-step-index" aria-hidden="true">01</span>
                <span class="progress-step-name">个人档案</span>
              </li>
              <li class="progress-step" :class="{ active: currentStep === 2, completed: currentStep > 2 }" :aria-current="currentStep === 2 ? 'step' : undefined">
                <span class="progress-step-index" aria-hidden="true">02</span>
                <span class="progress-step-name">本次问题</span>
              </li>
              <li class="progress-step" :class="{ active: currentStep === 3 }" :aria-current="currentStep === 3 ? 'step' : undefined">
                <span class="progress-step-index" aria-hidden="true">03</span>
                <span class="progress-step-name">提交申请</span>
              </li>
            </ol>
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
          :latest-report-status="latestReportStatus"
          :profile="profileDraft"
          :profile-last-confirmed-at="profileLastConfirmedAt"
          :profile-version="profileVersion"
          :show-advanced-context="showAdvancedContext"
          :submitting="submitting"
          :is-editing-request="Boolean(editingRequestId)"
          :topics="topics"
          @edit-profile="editProfile"
          @open-latest-report="openLatestReport"
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
          :is-generating="isGenerating"
          :gen-step="genStep"
          :request-id="currentRequestId"
          @view-requests="viewMyRequests"
          @new-application="startAnotherApplication"
        />
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script src="../features/assessment/page.js"></script>

<style scoped src="../features/assessment/assessment.css"></style>
