import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const MOBILE_NAV_QUERY = '(max-width: 1023px)'
const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function useMobileNavigationMenu() {
  const route = useRoute()
  const mobileMenuOpen = ref(false)
  const navToggleRef = ref(null)
  const mobilePanelRef = ref(null)
  const lastFocusedElement = ref(null)
  let mobileMediaQuery = null

  function closeMobileMenu({ restoreFocus = true } = {}) {
    mobileMenuOpen.value = false
    if (!restoreFocus) return

    nextTick(() => {
      const target = lastFocusedElement.value || navToggleRef.value
      if (target && typeof target.focus === 'function') target.focus()
    })
  }

  async function toggleMobileMenu() {
    if (mobileMenuOpen.value) {
      closeMobileMenu()
      return
    }

    lastFocusedElement.value = document.activeElement
    mobileMenuOpen.value = true
    await nextTick()
    const focusTarget = getFocusables()[0] || mobilePanelRef.value
    focusTarget?.focus()
  }

  function getFocusables() {
    if (!mobilePanelRef.value) return []
    return Array.from(mobilePanelRef.value.querySelectorAll(FOCUSABLE_SELECTOR))
      .filter(element => element.getClientRects().length > 0)
  }

  function handleKeydown(event) {
    if (!mobileMenuOpen.value) return

    if (event.key === 'Escape') {
      event.preventDefault()
      closeMobileMenu()
      return
    }

    if (event.key !== 'Tab') return

    const focusables = getFocusables()
    if (!focusables.length) {
      event.preventDefault()
      mobilePanelRef.value?.focus()
      return
    }

    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    const active = document.activeElement
    if (!mobilePanelRef.value?.contains(active)) {
      event.preventDefault()
      first.focus()
    } else if (event.shiftKey && active === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function handleViewportChange(event) {
    if (!event.matches && mobileMenuOpen.value) {
      closeMobileMenu({ restoreFocus: false })
    }
  }

  watch(() => route.fullPath, () => closeMobileMenu({ restoreFocus: false }))
  watch(mobileMenuOpen, value => {
    document.body.classList.toggle('menu-open', value)
  })

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
    mobileMediaQuery = window.matchMedia(MOBILE_NAV_QUERY)
    mobileMediaQuery.addEventListener('change', handleViewportChange)
  })
  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown)
    mobileMediaQuery?.removeEventListener('change', handleViewportChange)
    document.body.classList.remove('menu-open')
  })

  return { mobileMenuOpen, navToggleRef, mobilePanelRef, closeMobileMenu, toggleMobileMenu }
}
