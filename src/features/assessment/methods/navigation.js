export default {
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
    return text.length > length ? text.slice(0, length) + '…' : text
  },
  viewFullReport() {
    if (this.currentReportId) this.$router.push('/pages/report/detail?id=' + this.currentReportId)
  },
  goToCalendar() {
    this.$router.push('/pages/calendar/calendar')
  }
}
