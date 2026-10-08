import { getAllAdminUsers } from '../../admin/api.js'
import { consultantCanHandle, specialtyFields } from '../../report-cases/professional-ownership.js'
import { updateAdminServiceRequestAssignment } from '../api.js'
import { confirmAction } from '../../../utils/confirmAction.js'

function hasActiveOrCompletedStep(steps, specialty) {
  return (steps || []).some(step =>
    step.required_capability === specialty &&
    ['IN_REVIEW', 'COMPLETED'].includes(step.status)
  )
}

export default {
  async assignProfessional(specialty, value) {
    if (!this.admin || this.assignmentSaving || !this.workspace) return
    const currentId = this.workspace.request[specialtyFields[specialty]]
    const nextId = value ? Number(value) : null
    if (nextId !== currentId && currentId !== null && currentId !== undefined) {
      const steps = this.reportCase?.workflow_instance?.steps || []
      if (hasActiveOrCompletedStep(steps, specialty)) {
        const confirmed = await confirmAction({
          title: '确认更换专业负责人',
          message: '当前专业已有审核中或已完成的节点。更换负责人后，节点进度和已确认结果会保留，但后续处理将转交新的负责人。',
          confirmButtonText: '确认更换'
        })
        if (!confirmed) {
          await this.loadWorkspace(this.workspace.request.id)
          return
        }
      }
    }
    this.assignmentSaving = true
    try {
      await updateAdminServiceRequestAssignment(
        this.workspace.request.id,
        nextId,
        specialty,
        this.consultationType
      )
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
    if (!this.admin || !this.workspace || this.assignmentSaving || !this.assignmentChanged) return
    this.assignmentSaving = true
    try {
      const updated = await updateAdminServiceRequestAssignment(
        this.workspace.request.id,
        this.assignmentId ? Number(this.assignmentId) : null,
        undefined,
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
      ? ['mingli', 'psychology']
      : [this.consultationType === 'metaphysics' ? 'mingli' : 'psychology']
    if (!required.every(specialty => consultantCanHandle(current, specialty))) {
      this.assignmentId = null
    }
  },
  async saveConsultationType() {
    if (!this.admin || !this.workspace || this.assignmentSaving) return
    if ((this.workspace.request.consultation_type || 'integrated') === this.consultationType) return
    this.assignmentSaving = true
    try {
      const updated = await updateAdminServiceRequestAssignment(
        this.workspace.request.id,
        undefined,
        undefined,
        this.consultationType
      )
      this.workspace.request = { ...this.workspace.request, ...updated }
      this.message = '咨询方向已更新。'
      await this.loadRequests()
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.assignmentSaving = false
    }
  }
}
