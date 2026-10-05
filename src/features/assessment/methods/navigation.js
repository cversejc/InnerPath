export default {
  focusStepHeading() {
    this.$nextTick(() => {
      const stepContent = this.$refs.stepContent
      if (!stepContent) return
      window.scrollTo({ top: 0, behavior: 'auto' })
      stepContent.focusStepHeading()
    })
  },
  truncate(value, length) {
    const text = String(value || '')
    return text.length > length ? text.slice(0, length) + '…' : text
  },
  viewMyRequests() {
    this.$router.push('/pages/requests/requests')
  },
  startAnotherApplication() {
    this.currentRequestId = null
    this.submissionFingerprint = null
    this.submissionIdempotencyKey = null
    this.contextDraft = {
      focus_topics: [],
      current_challenge: '',
      expected_outcomes: [],
      issue_duration: '',
      impact_level: '',
      decision_status: '',
      decision_description: '',
      decision_style: [],
      additional_info: ''
    }
    this.currentStep = 2
    this.focusStepHeading()
  },
  goToCalendar() {
    this.$router.push('/pages/calendar/calendar')
  }
}
