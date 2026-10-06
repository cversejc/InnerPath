import { getAllAdminUsers } from '../../admin/api.js'
import { updateAdminServiceRequestAssignment } from '../api.js'

export default {
  async loadConsultants() {
    if (!this.admin) return
    try {
      const response = await getAllAdminUsers({ role: 'consultant', is_active: true, size: 100 })
      this.consultants = response.items || []
    } catch (error) {
      this.message = this.errorText(error)
    }
  },
  async assignConsultant() {
    if (!this.admin || !this.workspace || this.assignmentSaving || !this.assignmentChanged) return
    this.assignmentSaving = true
    try {
      const updated = await updateAdminServiceRequestAssignment(
        this.workspace.request.id,
        this.assignmentId ? Number(this.assignmentId) : null,
        this.workspace.request.service_type === 'report' ? this.consultationType : undefined
      )
      this.workspace.request = { ...this.workspace.request, ...updated }
      this.assignmentId = updated.assigned_consultant_id ?? null
      this.consultationType = updated.consultation_type || this.consultationType
      this.message = this.assignmentId ? '咨询方向与负责人已保存。' : '咨询方向与负责人已保存，申请当前未分配。'
      await this.loadRequests()
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.assignmentSaving = false
    }
  },
  changeConsultationType() {
    if (this.workspace?.request.service_type !== 'report') return
    const current = this.consultants.find(item => item.id === Number(this.assignmentId))
    if (!current) return
    const required = this.consultationType === 'integrated'
      ? ['metaphysics', 'psychology']
      : [this.consultationType]
    if (!required.every(specialty => (current.consultant_specialties || []).includes(specialty))) {
      this.assignmentId = null
    }
  }
}
