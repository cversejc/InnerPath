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
  viewFullReport() {
    if (this.currentReportId) this.$router.push('/pages/report/detail?id=' + this.currentReportId)
  },
  goToCalendar() {
    this.$router.push('/pages/calendar/calendar')
  }
}
