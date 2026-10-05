import { updateAdminUserRole } from "../api.js"
import { createStaffInvite } from '../api'

export default {
  async updateStaffSpecialty(member, specialty) {
    try { await updateAdminUserRole(member.id, "consultant", specialty); await this.loadStaff(); this.message = "咨询师专业类型已更新" }
    catch (error) { this.message = this.errorText(error) }
  },
  async inviteStaff() { if (this.inviteSaving) return; this.inviteSaving = true; try { const response = await createStaffInvite(this.inviteForm.phone, this.inviteForm.role, this.inviteForm.consultant_type); this.inviteToken = response.token; this.message = '邀请链接已生成，请安全发送给对方'; await this.loadStaff() } catch (error) { this.message = this.errorText(error) } finally { this.inviteSaving = false } }
}
