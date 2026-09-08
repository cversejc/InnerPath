<template>
  <nav class="navbar">
    <div class="nav-container">
      <router-link to="/pages/home/home" class="logo" aria-label="返回辰鉴首页">辰鉴</router-link>
      <ul class="nav-menu" aria-label="主导航">
        <li v-for="link in navLinks" :key="link.to">
          <router-link :to="link.to" class="nav-link">
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
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { authState, hasRole, logout as logoutUser } from '../stores/auth'

const navLinks = [
  { to: '/pages/home/home', label: '首页' },
  { to: '/pages/assessment/assessment', label: '人生说明书' },
  { to: '/pages/services/services', label: '服务' },
  { to: '/pages/calendar/calendar', label: '决策日历' },
  { to: '/pages/about/about', label: '关于辰鉴' },
  { to: '/pages/user/user', label: '我的辰鉴' }
]

const router = useRouter()

async function handleLogout() {
  await logoutUser()
  await router.replace('/auth/login')
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
</style>
