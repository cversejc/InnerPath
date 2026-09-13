import { createRouter, createWebHashHistory } from 'vue-router'
import { hasRole, initializeAuth } from '../stores/auth'
import About from '../views/About.vue'
import AdminConsole from '../views/AdminConsole.vue'
import Assessment from '../views/Assessment.vue'
import Auth from '../views/Auth.vue'
import Booking from '../views/Booking.vue'
import Calendar from '../views/Calendar.vue'
import Course from '../views/Course.vue'
import Home from '../views/Home.vue'
import ReportDetail from '../views/ReportDetail.vue'
import Services from '../views/Services.vue'
import StaffConsole from '../views/StaffConsole.vue'
import UserCenter from '../views/UserCenter.vue'
import { isLaunchFeatureEnabled } from '../config/launchScope'

const routes = [
  { path: '/', redirect: '/pages/home/home' },
  { path: '/auth/login', name: 'Login', component: Auth, meta: { public: true, title: '登录' } },
  { path: '/auth/register', name: 'Register', component: Auth, meta: { public: true, title: '注册' } },
  { path: '/auth/forgot-password', name: 'ForgotPassword', component: Auth, meta: { public: true, title: '找回密码' } },
  { path: '/auth/invite', name: 'StaffInvite', component: Auth, meta: { public: true, title: '接受邀请' } },
  { path: '/pages/home/home', name: 'Home', component: Home, meta: { requiresAuth: true, title: '首页' } },
  { path: '/pages/services/services', name: 'Services', component: Services, meta: { requiresAuth: true, hiddenFeature: 'services', title: '服务' } },
  { path: '/pages/assessment/assessment', name: 'Assessment', component: Assessment, meta: { requiresAuth: true, title: '人生说明书' } },
  { path: '/pages/booking/booking', name: 'Booking', component: Booking, meta: { requiresAuth: true, hiddenFeature: 'booking', title: '预约' } },
  { path: '/pages/course/course', name: 'Course', component: Course, meta: { requiresAuth: true, hiddenFeature: 'courses', title: '共鉴计划' } },
  { path: '/pages/user/user', name: 'UserCenter', component: UserCenter, meta: { requiresAuth: true, title: '个人空间' } },
  { path: '/pages/report/detail', name: 'ReportDetail', component: ReportDetail, meta: { requiresAuth: true, title: '个人报告' } },
  { path: '/pages/calendar/calendar', name: 'Calendar', component: Calendar, meta: { requiresAuth: true, title: '决策日历' } },
  { path: '/pages/about/about', name: 'About', component: About, meta: { requiresAuth: true, title: '关于辰鉴' } },
  { path: '/admin', name: 'AdminConsole', component: AdminConsole, meta: { requiresAuth: true, roles: ['admin'], title: '运营中枢' } },
  { path: '/staff', name: 'StaffConsole', component: StaffConsole, meta: { requiresAuth: true, roles: ['admin', 'consultant'], title: '咨询工作台' } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach(async to => {
  const user = await initializeAuth()
  if (to.meta.public) {
    if (user && to.path.startsWith('/auth/')) {
      return user.role === 'admin' ? '/admin' : user.role === 'consultant' ? '/staff' : '/pages/home/home'
    }
    return true
  }
  if (to.meta.hiddenFeature && !isLaunchFeatureEnabled(to.meta.hiddenFeature)) {
    return '/pages/home/home'
  }
  if (to.meta.requiresAuth && !user) {
    return {
      path: '/auth/login',
      query: { redirect: to.fullPath }
    }
  }
  if (to.meta.roles && !hasRole(...to.meta.roles)) {
    return '/pages/home/home'
  }
  return true
})

router.afterEach(to => {
  document.title = to.meta.title ? `${to.meta.title} · 辰鉴` : '辰鉴 · 星辰引路，镜子照见'
})

export default router
