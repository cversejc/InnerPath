export default {
  async inviteStaff() { if (this.inviteSaving) return; this.inviteSaving = true; try { const response = await createStaffInvite(this.inviteForm.phone, this.inviteForm.role); this.inviteToken = response.token; this.message = '邀请链接已生成，请安全发送给对方'; await this.loadStaff() } catch (error) { this.message = this.errorText(error) } finally { this.inviteSaving = false } }
}
