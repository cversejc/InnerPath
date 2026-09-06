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
    </div>
  </nav>
</template>

<script setup>
const navLinks = [
  { to: '/pages/home/home', label: '首页' },
  { to: '/pages/assessment/assessment', label: '人生说明书' },
  { to: '/pages/services/services', label: '服务' },
  { to: '/pages/calendar/calendar', label: '决策日历' },
  { to: '/pages/about/about', label: '关于辰鉴' },
  { to: '/pages/user/user', label: '我的辰鉴' }
]
</script>
