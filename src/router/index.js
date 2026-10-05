import { createRouter, createWebHashHistory } from 'vue-router'
import { hasRole, initializeAuth } from '../stores/auth'

const loadAuth = () => import('../views/Auth.vue')
const loadHome = () => import('../views/Home.vue')
const loadAssessment = () => import('../views/Assessment.vue')
const loadUserCenter = () => import('../views/UserCenter.vue')
const loadServiceRequests = () => import('../views/ServiceRequests.vue')
const loadServiceRequestForm = () => import('../views/ServiceRequestForm.vue')
const loadReportDetail = () => import('../features/reports/pages/ReportDetail.vue')
const loadCalendar = () => import('../views/Calendar.vue')
const loadAbout = () => import('../views/About.vue')
const loadAdminConsole = () => import('../views/AdminConsole.vue')
const loadStaffConsole = () => import('../views/StaffConsole.vue')
const loadSkillStudio = () => import('../features/skills/SkillStudio.vue')

const routes = [
  { path: '/', redirect: '/pages/home/home' },
  { path: '/auth/login', name: 'Login', component: loadAuth, meta: { public: true, title: '登录' } },
  { path: '/auth/register', name: 'Register', component: loadAuth, meta: { public: true, title: '注册' } },
  { path: '/auth/forgot-password', name: 'ForgotPassword', component: loadAuth, meta: { public: true, title: '找回密码' } },
  { path: '/auth/invite', name: 'StaffInvite', component: loadAuth, meta: { public: true, title: '接受邀请' } },
  { path: '/pages/home/home', name: 'Home', component: loadHome, meta: { requiresAuth: true, title: '首页' } },
  { path: '/pages/assessment/assessment', name: 'Assessment', component: loadAssessment, meta: { requiresAuth: true, title: '人生说明书' } },
  { path: '/pages/user/user', name: 'UserCenter', component: loadUserCenter, meta: { requiresAuth: true, title: '个人空间' } },
  { path: '/pages/requests/requests', name: 'ServiceRequests', component: loadServiceRequests, meta: { requiresAuth: true, title: '我的申请' } },
  { path: '/pages/requests/new', name: 'ServiceRequestForm', component: loadServiceRequestForm, meta: { requiresAuth: true, title: '申请决策日历' } },
  { path: '/pages/report/detail', name: 'ReportDetail', component: loadReportDetail, meta: { requiresAuth: true, title: '个人报告' } },
  { path: '/pages/calendar/calendar', name: 'Calendar', component: loadCalendar, meta: { requiresAuth: true, title: '决策日历' } },
  { path: '/pages/about/about', name: 'About', component: loadAbout, meta: { requiresAuth: true, title: '关于辰鉴' } },
  { path: '/admin', name: 'AdminConsole', component: loadAdminConsole, meta: { requiresAuth: true, roles: ['admin'], title: '运营中枢' } },
  { path: '/staff', name: 'StaffConsole', component: loadStaffConsole, meta: { requiresAuth: true, roles: ['admin', 'consultant'], title: '咨询工作台' } },
  { path: '/skills', name: 'SkillStudio', component: loadSkillStudio, meta: { requiresAuth: true, roles: ['admin', 'consultant'], title: '技能与示例工作台' } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach(async to => {
  if (import.meta.env.DEV && to.path === '/pages/report/detail' && to.query.preview === '1') {
    return true
  }

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

router.afterEach(to => {
  document.title = to.meta.title ? `${to.meta.title} · 辰鉴` : 'chenvis · 辰鉴 Life Timeline'
})

export default router
