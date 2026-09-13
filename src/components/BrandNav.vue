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

<style scoped>
.nav-account {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 18px;
  white-space: nowrap;
}

.nav-toggle,
.nav-mobile-panel,
.nav-scrim,
.mobile-quick-nav {
  display: none;
}

.nav-role-link,
.nav-user-name,
.nav-logout {
  color: inherit;
  font-size: 12px;
}

.nav-role-link {
  color: var(--cinnabar-deep, #8f352f);
  font-weight: 800;
  text-decoration: none;
}

.nav-logout {
  border: 1px solid rgba(80, 54, 32, 0.18);
  border-radius: 999px;
  background: transparent;
  cursor: pointer;
  padding: 6px 10px;
}

@media (max-width: 980px) {
  .nav-account { margin-left: 8px; }
  .nav-user-name { display: none; }
}

@media (max-width: 1023px) {
  .nav-container {
    min-height: var(--nav-height, 62px);
  }

  .nav-menu,
  .nav-account {
    display: none;
  }

  .nav-toggle {
    display: grid;
    width: 44px;
    height: 44px;
    place-content: center;
    gap: 4px;
    border: 1px solid rgba(139, 90, 20, 0.18);
    border-radius: 50%;
    background: rgba(255, 252, 245, 0.72);
    color: var(--cinnabar-deep, #8f352f);
  }

  .nav-toggle span {
    display: block;
    width: 16px;
    height: 1.5px;
    border-radius: 999px;
    background: currentColor;
    transition: transform 0.2s ease, opacity 0.2s ease;
  }

  .is-menu-open .nav-toggle span:nth-child(1) {
    transform: translateY(5.5px) rotate(45deg);
  }

  .is-menu-open .nav-toggle span:nth-child(2) {
    opacity: 0;
  }

  .is-menu-open .nav-toggle span:nth-child(3) {
    transform: translateY(-5.5px) rotate(-45deg);
  }

  .nav-mobile-panel {
    position: absolute;
    left: 12px;
    right: 12px;
    top: calc(100% + 8px);
    z-index: 2;
    display: grid;
    max-height: min(70dvh, 560px);
    gap: 4px;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 14px;
    border: 1px solid rgba(139, 90, 20, 0.16);
    border-radius: 20px;
    background: rgba(255, 250, 240, 0.97);
    box-shadow: 0 22px 50px -28px rgba(84, 48, 25, 0.72);
    -webkit-backdrop-filter: blur(18px);
    backdrop-filter: blur(18px);
  }

  .nav-mobile-kicker {
    padding: 4px 8px 8px;
    color: var(--gold-deep, #8b5a14);
    font-family: "Manrope", "PingFang SC", sans-serif;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 0.16em;
  }

  .nav-mobile-link {
    display: flex;
    min-height: 48px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-radius: 12px;
    padding: 0 12px;
    color: var(--ink, #2f241b);
    font-size: 15px;
    font-weight: 800;
  }

  .nav-mobile-link.router-link-active {
    background: rgba(184, 92, 80, 0.09);
    color: var(--cinnabar-deep, #8f352f);
  }

  .nav-mobile-link > .nav-mobile-arrow {
    color: var(--gold-deep, #8b5a14);
  }

  .nav-mobile-arrow {
    width: 17px;
    height: 17px;
    color: var(--gold-deep, #8b5a14);
  }

  .nav-scrim {
    position: fixed;
    inset: calc(var(--nav-height, 62px) + env(safe-area-inset-top, 0px)) 0 calc(66px + env(safe-area-inset-bottom, 0px));
    z-index: 1;
    display: block;
    width: 100%;
    border-radius: 0;
    background: rgba(47, 36, 27, 0.14);
    -webkit-backdrop-filter: blur(2px);
    backdrop-filter: blur(2px);
  }

  .nav-mobile-account {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 8px;
    border-top: 1px solid rgba(139, 90, 20, 0.12);
    padding: 14px 8px 2px;
    color: var(--ink, #2f241b);
  }

  .nav-mobile-account > div {
    display: grid;
    min-width: 0;
    gap: 3px;
  }

  .nav-mobile-account-label {
    color: var(--muted, #7d6653);
    font-size: 11px;
  }

  .nav-mobile-account strong {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .nav-mobile-account a,
  .nav-mobile-account button {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    padding: 0 8px;
    color: var(--cinnabar-deep, #8f352f);
    font-size: 12px;
    font-weight: 800;
    white-space: nowrap;
  }

  .mobile-quick-nav {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1001;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
    min-height: var(--mobile-nav-height, 64px);
    padding: 6px 12px calc(6px + env(safe-area-inset-bottom, 0px));
    border-top: 1px solid rgba(139, 90, 20, 0.14);
    background: rgba(255, 250, 240, 0.94);
    box-shadow: 0 -14px 30px -24px rgba(84, 48, 25, 0.72);
    -webkit-backdrop-filter: blur(18px);
    backdrop-filter: blur(18px);
  }

  .mobile-quick-link {
    display: grid;
    min-height: 44px;
    place-items: center;
    gap: 2px;
    border-radius: 12px;
    color: var(--muted, #7d6653);
    font-size: 11px;
    font-weight: 800;
    line-height: 1.2;
  }

  .mobile-quick-link .icon-mark {
    width: 20px;
    height: 20px;
  }

  .mobile-quick-link.router-link-active {
    background: rgba(184, 92, 80, 0.1);
    color: var(--cinnabar-deep, #9e3f35);
  }
}
</style>
