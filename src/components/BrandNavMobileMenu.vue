<template>
  <button
    class="nav-toggle"
    :class="{ 'is-menu-open': mobileMenuOpen }"
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
        v-for="link in secondaryLinks"
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
        <button type="button" @click="requestLogout">退出登录</button>
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
</template>

<script setup>
import { useMobileNavigationMenu } from '../features/navigation/useMobileNavigationMenu.js'
import { authState, hasRole } from '../stores/auth'

defineProps({
  quickLinks: { type: Array, required: true },
  secondaryLinks: { type: Array, default: () => [] }
})

const emit = defineEmits(['logout'])
const { mobileMenuOpen, navToggleRef, mobilePanelRef, closeMobileMenu, toggleMobileMenu } = useMobileNavigationMenu()

function requestLogout() {
  closeMobileMenu({ restoreFocus: false })
  emit('logout')
}

defineExpose({ closeMobileMenu })
</script>

<style scoped src="./BrandNavMobileMenu.css"></style>
