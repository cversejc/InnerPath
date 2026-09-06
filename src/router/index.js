import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Services from '../views/Services.vue'
import About from '../views/About.vue'
import Assessment from '../views/Assessment.vue'
import Booking from '../views/Booking.vue'
import Course from '../views/Course.vue'
import UserCenter from '../views/UserCenter.vue'
import ReportDetail from '../views/ReportDetail.vue'
import Calendar from '../views/Calendar.vue'

const routes = [
  {
    path: '/',
    redirect: '/pages/home/home'
  },
  {
    path: '/pages/home/home',
    name: 'Home',
    component: Home
  },
  {
    path: '/pages/services/services',
    name: 'Services',
    component: Services
  },
  {
    path: '/pages/assessment/assessment',
    name: 'Assessment',
    component: Assessment
  },
  {
    path: '/pages/booking/booking',
    name: 'Booking',
    component: Booking
  },
  {
    path: '/pages/course/course',
    name: 'Course',
    component: Course
  },
  {
    path: '/pages/user/user',
    name: 'UserCenter',
    component: UserCenter
  },
  {
    path: '/pages/report/detail',
    name: 'ReportDetail',
    component: ReportDetail
  },
  {
    path: '/pages/calendar/calendar',
    name: 'Calendar',
    component: Calendar
  },
  {
    path: '/pages/about/about',
    name: 'About',
    component: About
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
