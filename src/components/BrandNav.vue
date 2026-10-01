<template>
  <nav class="navbar" :class="{ 'is-menu-open': mobileMenuOpen }" aria-label="主导航">
    <div class="nav-container">
      <router-link to="/pages/home/home" class="logo" aria-label="返回辰鉴首页" @click="closeMobileMenu({ restoreFocus: false })">辰鉴</router-link>
      <ul class="nav-menu" aria-label="主导航">
        <li v-for="link in navLinks" :key="link.to">
          <router-link :to="link.to" class="nav-link" @click="closeMobileMenu({ restoreFocus: false })">
            {{ link.label }}
          </router-link>
        </li>
      </ul>
      <div v-if="authState.user" class="nav-account">
        <router-link v-if="hasRole('admin')" to="/admin" class="nav-role-link">管理后台</router-link>
        <router-link v-else-if="hasRole('consultant')" to="/staff" class="nav-role-link">咨询工作台</router-link>
        <span class="nav-user-name">{{ authState.user.name }}</span>
        <button class="nav-logout" type="button" @click="handleLogout">退出</button>
      </div>
      <button
        class="nav-toggle"
        ref="navToggleRef"
        type="button"
        :aria-expanded="mobileMenuOpen"
        aria-controls="mobile-navigation"
        :aria-label="mobileMenuOpen ? '关闭主导航' : '打开主导航'"
        @click="toggleMobileMenu"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
    </div>
    <button
      v-if="mobileMenuOpen"
      class="nav-scrim"
      type="button"
      aria-label="关闭主导航"
      @click="closeMobileMenu"
    ></button>
    <div
      v-if="mobileMenuOpen"
      id="mobile-navigation"
      ref="mobilePanelRef"
      class="nav-mobile-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mobile-navigation-title"
      tabindex="-1"
    >
      <p id="mobile-navigation-title" class="nav-mobile-kicker">更多入口 / MORE</p>
      <router-link
        v-if="hasRole('admin')"
        to="/admin"
        class="nav-mobile-link nav-mobile-role-link"
        @click="closeMobileMenu({ restoreFocus: false })"
      >
        <span>管理中心</span>
        <IconMark name="arrow" class="nav-mobile-arrow" />
      </router-link>
      <router-link
        v-else-if="hasRole('consultant')"
        to="/staff"
        class="nav-mobile-link nav-mobile-role-link"
        @click="closeMobileMenu({ restoreFocus: false })"
      >
        <span>咨询工作台</span>
        <IconMark name="arrow" class="nav-mobile-arrow" />
      </router-link>
      <router-link
        v-for="link in mobileSecondaryLinks"
        :key="`mobile-${link.to}`"
        :to="link.to"
        class="nav-mobile-link"
        @click="closeMobileMenu({ restoreFocus: false })"
      >
        <span>{{ link.label }}</span>
        <IconMark name="arrow" class="nav-mobile-arrow" />
      </router-link>
      <div v-if="authState.user" class="nav-mobile-account">
        <div>
          <span class="nav-mobile-account-label">当前账号</span>
          <strong>{{ authState.user.name }}</strong>
        </div>
        <button type="button" @click="handleLogout">退出登录</button>
      </div>
    </div>
    <nav
      class="mobile-quick-nav"
      :aria-hidden="mobileMenuOpen ? 'true' : undefined"
      :inert="mobileMenuOpen"
      aria-label="快捷导航"
    >
      <router-link
        v-for="link in quickLinks"
        :key="`quick-${link.to}`"
        :to="link.to"
        class="mobile-quick-link"
        @click="closeMobileMenu({ restoreFocus: false })"
      >
        <IconMark :name="link.icon" />
        <span>{{ link.label }}</span>
      </router-link>
    </nav>
  </nav>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, hasRole, logout as logoutUser } from '../stores/auth'

const navLinks = [
  { to: '/pages/home/home', label: '首页' },
  { to: '/pages/assessment/assessment', label: '报告' },
  { to: '/pages/calendar/calendar', label: '日历' },
  { to: '/pages/about/about', label: '关于' },
  { to: '/pages/user/user', label: '我的' }
]

const quickLinks = [
  { ...navLinks[0], icon: 'compass' },
  { ...navLinks[1], icon: 'reports' },
  { ...navLinks[2], icon: 'calendar' },
  { ...navLinks[4], icon: 'person' }
]

const mobileSecondaryLinks = [
  { to: '/pages/about/about', label: '关于辰鉴' }
]

const router = useRouter()
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
  const firstFocusable = getMobileMenuFocusables()[0]
  const focusTarget = firstFocusable || mobilePanelRef.value
  focusTarget?.focus()
}

function getMobileMenuFocusables() {
  if (!mobilePanelRef.value) return []
  return Array.from(mobilePanelRef.value.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )).filter(element => element.getClientRects().length > 0)
}

function handleKeydown(event) {
  if (!mobileMenuOpen.value) return

  if (event.key === 'Escape') {
    event.preventDefault()
    closeMobileMenu()
    return
  }

  if (event.key !== 'Tab') return

  const focusables = getMobileMenuFocusables()
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
  mobileMediaQuery = window.matchMedia('(max-width: 1023px)')
  mobileMediaQuery.addEventListener('change', handleViewportChange)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
  mobileMediaQuery?.removeEventListener('change', handleViewportChange)
  document.body.classList.remove('menu-open')
})

async function handleLogout() {
  closeMobileMenu({ restoreFocus: false })
  try {
    await logoutUser()
  } finally {
    await router.replace('/auth/login')
  }
}
</script>

<style scoped src="./BrandNav.css"></style>
