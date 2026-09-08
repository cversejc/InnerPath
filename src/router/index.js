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

const routes = [
  { path: '/', redirect: '/pages/home/home' },
  { path: '/auth/login', name: 'Login', component: Auth, meta: { public: true } },
  { path: '/auth/register', name: 'Register', component: Auth, meta: { public: true } },
  { path: '/auth/forgot-password', name: 'ForgotPassword', component: Auth, meta: { public: true } },
  { path: '/auth/invite', name: 'StaffInvite', component: Auth, meta: { public: true } },
  { path: '/pages/home/home', name: 'Home', component: Home, meta: { requiresAuth: true } },
  { path: '/pages/services/services', name: 'Services', component: Services, meta: { requiresAuth: true } },
  { path: '/pages/assessment/assessment', name: 'Assessment', component: Assessment, meta: { requiresAuth: true } },
  { path: '/pages/booking/booking', name: 'Booking', component: Booking, meta: { requiresAuth: true } },
  { path: '/pages/course/course', name: 'Course', component: Course, meta: { requiresAuth: true } },
  { path: '/pages/user/user', name: 'UserCenter', component: UserCenter, meta: { requiresAuth: true } },
  { path: '/pages/report/detail', name: 'ReportDetail', component: ReportDetail, meta: { requiresAuth: true } },
  { path: '/pages/calendar/calendar', name: 'Calendar', component: Calendar, meta: { requiresAuth: true } },
  { path: '/pages/about/about', name: 'About', component: About, meta: { requiresAuth: true } },
  { path: '/admin', name: 'AdminConsole', component: AdminConsole, meta: { requiresAuth: true, roles: ['admin'] } },
  { path: '/staff', name: 'StaffConsole', component: StaffConsole, meta: { requiresAuth: true, roles: ['admin', 'consultant'] } }
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

export default router
