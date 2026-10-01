export default {
  async loadBookings() {
      this.bookingsLoading = true
      try { this.bookings = await getAdminBookings({ ...this.cleanParams(this.bookingFilters), page: this.bookingPage, size: this.bookingPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.bookingsLoading = false }
    },
  async searchBookings() { this.bookingPage = 1; await this.loadBookings() },
  resetBookingFilters() { this.bookingFilters = { search: '', status: '', consultant_id: '', date_from: '', date_to: '' }; this.searchBookings() },
  async changeBookingPage(offset) { const next = this.bookingPage + offset; if (next < 1 || next > this.pageCount(this.bookings.total, this.bookingPageSize)) return; this.bookingPage = next; await this.loadBookings() },
  openBookingDetail(booking) { this.drawerTrigger = document.activeElement; this.bookingDetail = booking; this.bookingEditor = { status: booking.status, confirmed_date: booking.confirmed_date || '', confirmed_time: booking.confirmed_time || '', consultant_id: booking.consultant_id ?? null, meeting_url: booking.meeting_url || '', meeting_notes: booking.meeting_notes || '', cancellation_reason: booking.cancellation_reason || '' }; this.focusDrawer('bookingDrawer') },
  closeBookingDetail() { this.bookingDetail = null; this.restoreDrawerFocus() },
  async saveBooking() {
      if (!this.bookingDetail || this.bookingSaving) return
      this.bookingSaving = true
      try { const updated = await updateAdminBooking(this.bookingDetail.id, { ...this.bookingEditor, consultant_id: this.bookingEditor.consultant_id || null, confirmed_date: this.bookingEditor.confirmed_date || null, confirmed_time: this.bookingEditor.confirmed_time || null, cancellation_reason: this.bookingEditor.cancellation_reason || null }); Object.assign(this.bookingDetail, updated); this.message = '预约已更新'; await this.loadBookings() } catch (error) { this.message = this.errorText(error) } finally { this.bookingSaving = false }
    }
}
