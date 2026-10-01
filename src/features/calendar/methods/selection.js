export default {
  selectDate(date) {
      this.selectedDate = date
      this.closeRecordForm()
      this.recordFeedback = ''
      this.showFullGuidance = false
      if (this.isMobileLayout) {
        this.openMobileDetail()
      }
    },
  selectDecisionNode(node) {
      this.selectDate(node.dateKey || this.selectedDate)
    },
  showCurrentDate() {
      if (this.todayDate) {
        this.selectDate(this.todayDate)
      } else if (this.isMobileLayout) {
        this.openMobileDetail()
      }
    },
  handleLayoutChange(event) {
      this.isMobileLayout = event.matches
      this.mobileDetailOpen = !event.matches
      document.body.classList.remove('dialog-open')
    },
  openMobileDetail() {
      if (!this.isMobileLayout) return
      this.mobileDetailOpen = true
      document.body.classList.add('dialog-open')
      this.$nextTick(() => this.$refs.planningSection?.focusCloseButton())
    },
  closeMobileDetail({ restoreFocus = true } = {}) {
      this.mobileDetailOpen = false
      document.body.classList.remove('dialog-open')
      if (restoreFocus) {
        this.$nextTick(() => this.$refs.planningSection?.focusTrigger())
      }
    },
  handleDetailKeydown(event) {
      if (!this.mobileDetailOpen) return

      if (event.key === 'Escape') {
        event.preventDefault()
        this.closeMobileDetail()
        return
      }

      if (event.key !== 'Tab') return
      const focusables = this.$refs.planningSection?.getFocusableItems() || []
      if (!focusables.length) {
        event.preventDefault()
        this.$refs.planningSection?.focusContainer()
        return
      }

      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    },
  handleEscape(event) {
      if (event.key === 'Escape' && this.isMobileLayout && this.mobileDetailOpen) {
        this.closeMobileDetail()
      }
    }
}
