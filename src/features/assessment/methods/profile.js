import { setAuthenticatedUser } from '../../../stores/auth.js'
import { updateUserProfile } from '../../users/service.js'
import { buildProfilePayload, mapUserToProfile } from '../../users/profile.js'
import { validateAssessmentProfile } from '../form.js'

export default {
  validateProfile() {
    const errors = validateAssessmentProfile(this.profileDraft)
    this.profileErrors = errors
    return Object.keys(errors).length === 0
  },
  async saveProfileAndContinue() {
    this.formMessage = ''
    if (!this.validateProfile()) {
      this.formMessage = '请先补充个人档案中的必填项。'
      this.focusStepHeading()
      return
    }
    this.savingProfile = true
    try {
      const user = await updateUserProfile(buildProfilePayload(this.profileDraft))
      setAuthenticatedUser(user)
      this.profileDraft = mapUserToProfile(user)
      this.profileVersion = user.profile_version || this.profileVersion
      this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
      this.hasExistingProfile = true
      this.draftStatus = '档案已确认 · 版本 v' + this.profileVersion
      this.currentStep = 2
      this.focusStepHeading()
    } catch (error) {
      this.formMessage = error.response?.data?.detail || '档案保存失败，请检查网络后重试。'
    } finally {
      this.savingProfile = false
    }
  },
  editProfile() {
    this.formMessage = ''
    this.currentStep = 1
    this.focusStepHeading()
  }
}
