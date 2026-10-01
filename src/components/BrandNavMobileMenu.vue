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

  <VanActionSheet
    v-model:show="mobileMenuOpen"
    teleport="body"
    id="mobile-navigation"
    title="更多入口 / MORE"
    :closeable="false"
    :safe-area-inset-bottom="true"
    aria-label="主导航菜单"
    aria-modal="true"
    tabindex="0"
  >
    <div ref="mobilePanelRef" class="nav-mobile-panel" tabindex="-1">
      <VanCellGroup inset class="nav-mobile-links">
        <router-link
          v-for="link in menuLinks"
          :key="`mobile-${link.to}`"
          :to="link.to"
          custom
          v-slot="{ href, navigate, isActive }"
        >
          <a
            :href="href"
            class="nav-mobile-link"
            :class="{ 'router-link-active': isActive }"
            @click="navigateMenuLink(navigate, $event)"
          >
            <VanCell :title="link.label" is-link :clickable="false" />
          </a>
        </router-link>
      </VanCellGroup>

      <div v-if="authState.user" class="nav-mobile-account">
        <div>
          <span class="nav-mobile-account-label">当前账号</span>
          <strong>{{ authState.user.name }}</strong>
        </div>
        <VanButton native-type="button" size="small" plain type="danger" @click="requestLogout">
          退出登录
        </VanButton>
      </div>

      <VanButton native-type="button" class="nav-mobile-close" block @click="closeMobileMenu">
        关闭菜单
      </VanButton>
    </div>
  </VanActionSheet>

  <Teleport to="body">
    <VanTabbar
      class="mobile-quick-nav"
      route
      :border="false"
      :z-index="1001"
      :safe-area-inset-bottom="true"
      :aria-hidden="mobileMenuOpen ? 'true' : undefined"
      :inert="mobileMenuOpen"
      aria-label="快捷导航"
    >
      <VanTabbarItem v-for="link in quickLinks" :key="`quick-${link.to}`" :to="link.to">
        {{ link.label }}
        <template #icon>
          <IconMark :name="link.icon" />
        </template>
      </VanTabbarItem>
    </VanTabbar>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import {
  ActionSheet as VanActionSheet,
  Button as VanButton,
  Cell as VanCell,
  CellGroup as VanCellGroup,
  Tabbar as VanTabbar,
  TabbarItem as VanTabbarItem
} from 'vant'
import { useMobileNavigationMenu } from '../features/navigation/useMobileNavigationMenu.js'
import { authState, hasRole } from '../stores/auth'

const props = defineProps({
  quickLinks: { type: Array, required: true },
  secondaryLinks: { type: Array, default: () => [] }
})

const emit = defineEmits(['logout'])
const { mobileMenuOpen, navToggleRef, mobilePanelRef, closeMobileMenu, toggleMobileMenu } = useMobileNavigationMenu()
const menuLinks = computed(() => {
  const roleLink = hasRole('admin')
    ? { to: '/admin', label: '管理中心' }
    : hasRole('consultant')
      ? { to: '/staff', label: '咨询工作台' }
      : null
  return roleLink ? [roleLink, ...props.secondaryLinks] : props.secondaryLinks
})

function navigateMenuLink(navigate, event) {
  closeMobileMenu({ restoreFocus: false })
  navigate(event)
}

function requestLogout() {
  closeMobileMenu({ restoreFocus: false })
  emit('logout')
}

defineExpose({ closeMobileMenu })
</script>

<style scoped src="./BrandNavMobileMenu.css"></style>
