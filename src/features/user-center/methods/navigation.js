export default {
  goToAssessment() {
    this.$router.push('/pages/assessment/assessment')
  },
  goToCalendar() {
    this.$router.push('/pages/calendar/calendar')
  },
  viewReport(reportId) {
    this.$router.push('/pages/report/detail?id=' + reportId)
  },
  selectTab(tabId) {
    this.activeTab = tabId
  },
  moveTab(offset) {
    const currentIndex = this.tabs.findIndex(tab => tab.id === this.activeTab)
    const nextIndex = (currentIndex + offset + this.tabs.length) % this.tabs.length
    const nextTab = this.tabs[nextIndex]
    this.activeTab = nextTab.id
    this.$nextTick(() => document.getElementById('user-tab-' + nextTab.id)?.focus())
  }
}
