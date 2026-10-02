import { showConfirmDialog } from 'vant'

export function createConfirmAction(showDialog = showConfirmDialog) {
  return async function confirmAction(options) {
    try {
      await showDialog({
        className: 'mobile-form-dialog',
        cancelButtonText: '取消',
        closeOnClickOverlay: false,
        messageAlign: 'left',
        ...options
      })
      return true
    } catch (action) {
      if (action === 'cancel') return false
      throw action
    }
  }
}

export const confirmAction = createConfirmAction()
