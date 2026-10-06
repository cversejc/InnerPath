import { getAllAdminUsers } from '../../admin/api.js'
import { updateAdminServiceRequestAssignment } from '../api.js'

export default {
  async assignProfessional(specialty, value) {
    if (!this.admin || this.assignmentSaving || !this.workspace) return
    this.assignmentSaving = true
    try {
      await updateAdminServiceRequestAssignment(this.workspace.request.id, value ? Number(value) : null, specialty)
      await this.loadWorkspace(this.workspace.request.id)
      this.message = "专业负责人已更新"
    } catch (error) { this.message = this.errorText(error) }
    finally { this.assignmentSaving = false }
  },
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
    if (!this.admin || !this.workspace || this.assignmentSaving) return
    this.assignmentSaving = true
    try {
      const updated = await updateAdminServiceRequestAssignment(
        this.workspace.request.id,
        this.assignmentId ? Number(this.assignmentId) : null
      )
      this.workspace.request = { ...this.workspace.request, ...updated }
      this.message = this.assignmentId ? '已改派咨询师。' : '已取消分配，申请回到待接单池。'
      await this.loadRequests()
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.assignmentSaving = false
    }
  }
}
