import {
  createEmptyAssessmentContext,
  validateAssessmentContext
} from '../form.js'

export default {
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
    if (field === 'current_challenge' && String(this.contextDraft.current_challenge || '').trim()) {
      delete this.contextErrors.current_challenge
    }
  },
  validateContext() {
    const errors = validateAssessmentContext(this.contextDraft)
    this.contextErrors = errors
    return Object.keys(errors).length === 0
  },
  reusePreviousContext() {
    this.contextDraft = {
      ...createEmptyAssessmentContext(),
      ...(this.lastContext || {}),
      focus_topics: [...(this.lastContext?.focus_topics || [])],
      expected_outcomes: [...(this.lastContext?.expected_outcomes || [])],
      decision_style: [...(this.lastContext?.decision_style || [])]
    }
    this.contextMessage = this.lastContextReportId
      ? '已带入报告 #' + this.lastContextReportId + ' 的背景，请按这一次的情况编辑。'
      : '已带入上次背景，请按这一次的情况编辑。'
    this.$nextTick(() => document.getElementById('assessment-current-challenge')?.focus())
  }
}
