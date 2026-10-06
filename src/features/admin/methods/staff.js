import { createStaffInvite, updateAdminConsultantSpecialties } from '../api.js'

export default {
  async inviteStaff() { if (this.inviteSaving) return; this.inviteSaving = true; try { const response = await createStaffInvite(this.inviteForm.phone, this.inviteForm.role, this.inviteForm.consultant_type); this.inviteToken = response.token; this.message = '邀请链接已生成，请安全发送给对方'; await this.loadStaff() } catch (error) { this.message = this.errorText(error) } finally { this.inviteSaving = false } },
  async updateConsultantSpecialties({ userId, specialties }) {
    if (this.consultantSpecialtySavingId) return
    this.consultantSpecialtySavingId = userId
    try {
      const updated = await updateAdminConsultantSpecialties(userId, specialties)
      const member = this.staffUsers.find(item => item.id === userId)
      if (member) Object.assign(member, updated)
      this.message = '咨询师能力标签已更新'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.consultantSpecialtySavingId = null
    }
  }
}
