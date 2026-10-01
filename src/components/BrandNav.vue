<template>
  <nav class="navbar" aria-label="主导航">
    <div class="nav-container">
      <router-link to="/pages/home/home" class="logo" aria-label="返回辰鉴首页" @click="closeMobileMenu">
        <img class="brand-emblem" src="/brand-emblem.png" alt="" />
        <span>辰鉴</span>
      </router-link>
      <ul class="nav-menu" aria-label="主导航">
        <li v-for="link in navLinks" :key="link.to">
          <router-link :to="link.to" class="nav-link" @click="closeMobileMenu">
            {{ link.label }}
          </router-link>
        </li>
      </ul>
      <div v-if="authState.user" class="nav-account">
        <router-link v-if="hasRole('admin')" to="/admin" class="nav-role-link">管理后台</router-link>
        <router-link v-else-if="hasRole('consultant')" to="/staff" class="nav-role-link">咨询工作台</router-link>
        <span class="nav-user-name">{{ authState.user.name }}</span>
        <VanButton class="nav-logout" type="default" plain round native-type="button" @click="handleLogout">退出</VanButton>
      </div>
      <BrandNavMobileMenu
        ref="mobileMenuRef"
        :quick-links="quickLinks"
        :secondary-links="mobileSecondaryLinks"
        @logout="handleLogout"
      />
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button as VanButton } from 'vant'
import BrandNavMobileMenu from './BrandNavMobileMenu.vue'
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
const mobileMenuRef = ref(null)

function closeMobileMenu() {
  mobileMenuRef.value?.closeMobileMenu({ restoreFocus: false })
}

async function handleLogout() {
  try {
    await logoutUser()
  } finally {
    await router.replace('/auth/login')
  }
}
</script>

<style scoped src="./BrandNav.css"></style>
