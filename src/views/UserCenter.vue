<template>
  <div class="user-center">
    <BrandNav />

    <!-- 用户信息头部 -->
    <section class="user-header">
      <div class="container">
        <div class="user-info">
          <div class="user-avatar">{{ userName.charAt(0) }}</div>
          <div class="user-details">
            <h2>{{ userName }}</h2>
            <p class="user-type">{{ userType }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 主内容区 -->
    <section class="user-content">
      <div class="container">
        <div class="content-layout">
          <!-- 侧边栏 -->
          <aside class="sidebar">
            <nav class="sidebar-nav">
              <a
                v-for="tab in tabs"
                :key="tab.id"
                class="nav-item"
                :class="{ active: activeTab === tab.id }"
                @click="activeTab = tab.id"
              >
                <span class="nav-icon">{{ tab.icon }}</span>
                <span class="nav-label">{{ tab.label }}</span>
              </a>
            </nav>
          </aside>

          <!-- 内容区 -->
          <main class="main-content">
            <!-- 我的报告 -->
            <div v-if="activeTab === 'reports'" class="content-section">
              <h3 class="section-title">我的报告</h3>
              <div v-if="reports.length === 0" class="empty-state">
                <div class="empty-icon">📄</div>
                <p>暂无报告</p>
                <button class="btn-action" @click="goToAssessment">生成说明书</button>
              </div>
              <div v-else class="reports-list">
                <div v-for="report in reports" :key="report.id" class="report-card">
                  <div class="report-header">
                    <h4>{{ report.title }}</h4>
                    <span class="report-date">{{ report.date }}</span>
                  </div>
                  <div class="report-preview">
                    <div class="preview-item">
                      <strong>个人属性：</strong>{{ report.energyType }}
                    </div>
                    <div class="preview-item">
                      <strong>核心特质：</strong>{{ report.coreTraits }}
                    </div>
                  </div>
                  <div class="report-actions">
                    <button class="btn-view" @click="viewReport(report.id)">查看完整报告</button>
                    <button class="btn-download">下载PDF</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 我的预约 -->
            <div v-if="activeTab === 'bookings'" class="content-section">
              <h3 class="section-title">我的预约</h3>
              <div v-if="bookings.length === 0" class="empty-state">
                <div class="empty-icon">📅</div>
                <p>暂无预约</p>
                <button class="btn-action" @click="goToBooking">预约行动端</button>
              </div>
              <div v-else class="bookings-list">
                <div v-for="booking in bookings" :key="booking.id" class="booking-card">
                  <div class="booking-status" :class="booking.status">
                    {{ getStatusText(booking.status) }}
                  </div>
                  <div class="booking-info">
                    <h4>{{ booking.service }}</h4>
                    <div class="booking-detail">
                      <span class="detail-icon">📅</span>
                      <span>{{ booking.date }}</span>
                    </div>
                    <div class="booking-detail">
                      <span class="detail-icon">⏰</span>
                      <span>{{ booking.time }}</span>
                    </div>
                    <div class="booking-detail" v-if="booking.consultant">
                      <span class="detail-icon">👤</span>
                      <span>咨询师：{{ booking.consultant }}</span>
                    </div>
                  </div>
                  <div class="booking-actions">
                    <button v-if="booking.status === 'confirmed'" class="btn-join">进入咨询</button>
                    <button v-if="booking.status === 'pending'" class="btn-cancel">取消预约</button>
                    <button v-if="booking.status === 'completed'" class="btn-feedback">评价</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 我的课程 -->
            <div v-if="activeTab === 'courses'" class="content-section">
              <h3 class="section-title">我的课程</h3>
              <div v-if="courses.length === 0" class="empty-state">
                <div class="empty-icon">📚</div>
                <p>暂无课程</p>
                <button class="btn-action" @click="goToCourse">浏览课程</button>
              </div>
              <div v-else class="courses-list">
                <div v-for="course in courses" :key="course.id" class="course-card">
                  <div class="course-cover">
                    <div class="course-progress-ring">
                      <span class="progress-text">{{ course.progress }}%</span>
                    </div>
                  </div>
                  <div class="course-info">
                    <h4>{{ course.title }}</h4>
                    <div class="course-stats">
                      <span>已学习 {{ course.completed }}/{{ course.total }} 课时</span>
                    </div>
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: course.progress + '%' }"></div>
                    </div>
                  </div>
                  <div class="course-actions">
                    <button class="btn-continue">继续学习</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 账户设置 -->
            <div v-if="activeTab === 'settings'" class="content-section">
              <h3 class="section-title">账户设置</h3>
              <form class="settings-form">
                <div class="form-group">
                  <label>姓名</label>
                  <input v-model="settings.name" type="text">
                </div>
                <div class="form-group">
                  <label>性别</label>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input v-model="settings.gender" type="radio" value="male">
                      <span>男</span>
                    </label>
                    <label class="radio-label">
                      <input v-model="settings.gender" type="radio" value="female">
                      <span>女</span>
                    </label>
                  </div>
                </div>
                <div class="form-group">
                  <label>联系方式</label>
                  <input v-model="settings.contact" type="text">
                </div>
                <div class="form-group">
                  <label>出生日期</label>
                  <input v-model="settings.birthDate" type="date">
                </div>
                <div class="form-group">
                  <label>邮箱</label>
                  <input v-model="settings.email" type="email">
                </div>
                <button type="button" class="btn-save" @click="saveSettings">保存设置</button>
              </form>
            </div>
          </main>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
export default {
  name: 'UserCenter',
  data() {
    return {
      userName: '张三',
      userType: '成长探索者',
      activeTab: 'reports',
      tabs: [
        { id: 'reports', icon: '📊', label: '我的报告' },
        { id: 'bookings', icon: '📅', label: '我的预约' },
        { id: 'courses', icon: '📚', label: '我的课程' },
        { id: 'settings', icon: '⚙️', label: '账户设置' }
      ],
      reports: [],
      bookings: [
        {
          id: 1,
          service: '辰鉴·行动与决策',
          date: '2026-05-28',
          time: '14:00-15:30',
          consultant: '李老师',
          status: 'confirmed'
        },
        {
          id: 2,
          service: '辰鉴·人生说明书',
          date: '2026-05-15',
          time: '10:00-11:00',
          consultant: '王老师',
          status: 'completed'
        }
      ],
      courses: [
        {
          id: 1,
          title: '辰鉴·共鉴计划',
          progress: 35,
          completed: 4,
          total: 12
        }
      ],
      settings: {
        name: '张三',
        gender: 'male',
        contact: '138****8888',
        birthDate: '1990-01-01',
        email: 'zhangsan@example.com'
      }
    }
  },
  mounted() {
    this.loadReports()
  },
  methods: {
    loadReports() {
      const savedReports = JSON.parse(localStorage.getItem('userReports') || '[]')
      this.reports = savedReports.map(item => ({
        id: item.id,
        title: '辰鉴·人生说明书',
        date: item.date,
        energyType: item.report.energyProfile.type,
        coreTraits: item.report.energyProfile.coreTraits,
        fullReport: item.report
      }))
    },
    getStatusText(status) {
      const statusMap = {
        pending: '待确认',
        confirmed: '已确认',
        completed: '已完成',
        cancelled: '已取消'
      }
      return statusMap[status] || status
    },
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    },
    goToBooking() {
      this.$router.push('/pages/booking/booking')
    },
    goToCourse() {
      this.$router.push('/pages/course/course')
    },
    viewReport(reportId) {
      this.$router.push(`/pages/report/detail?id=${reportId}`)
    },
    saveSettings() {
      alert('设置已保存')
    }
  }
}
</script>

<style scoped>
.user-center {
  width: 100%;
  background: #f8f9fa;
  min-height: 100vh;
}

/* 导航栏 */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 1000;
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 24px;
  font-weight: 600;
  color: #d4524f;
}

.nav-menu {
  display: flex;
  gap: 30px;
}

.nav-link {
  font-size: 16px;
  color: #666;
  transition: color 0.3s;
}

.nav-link:hover,
.nav-link.active {
  color: #d4524f;
}

/* 用户头部 */
.user-header {
  padding: 100px 20px 40px;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #d4524f;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 600;
}

.user-details h2 {
  font-size: 28px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 8px;
}

.user-type {
  font-size: 16px;
  color: #636e72;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 内容区 */
.user-content {
  padding: 40px 0 80px;
}

.content-layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 30px;
}

/* 侧边栏 */
.sidebar {
  background: #fff;
  border-radius: 12px;
  padding: 20px 0;
  height: fit-content;
  position: sticky;
  top: 100px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 25px;
  color: #666;
  cursor: pointer;
  transition: all 0.3s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #f8f9fa;
  color: #2d3436;
}

.nav-item.active {
  background: #fff5f5;
  color: #d4524f;
  border-left-color: #d4524f;
  font-weight: 600;
}

.nav-icon {
  font-size: 20px;
}

.nav-label {
  font-size: 15px;
}

/* 主内容 */
.main-content {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  min-height: 500px;
}

.section-title {
  font-size: 24px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  color: #999;
  margin-bottom: 25px;
}

.btn-action {
  padding: 12px 32px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-action:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

/* 报告列表 */
.reports-list {
  display: grid;
  gap: 20px;
}

.report-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 25px;
  transition: all 0.3s;
}

.report-card:hover {
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.report-header h4 {
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
}

.report-date {
  font-size: 14px;
  color: #999;
}

.report-preview {
  margin-bottom: 20px;
}

.preview-item {
  font-size: 14px;
  color: #666;
  line-height: 2;
}

.preview-item strong {
  color: #2d3436;
}

.report-actions {
  display: flex;
  gap: 10px;
}

.btn-view,
.btn-download {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.3s;
}

.btn-view {
  color: #fff;
  background: #d4524f;
}

.btn-view:hover {
  background: #c0392b;
}

.btn-download {
  color: #666;
  background: #fff;
  border: 2px solid #e0e0e0;
}

.btn-download:hover {
  border-color: #d4524f;
  color: #d4524f;
}

/* 预约列表 */
.bookings-list {
  display: grid;
  gap: 20px;
}

.booking-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 25px;
  position: relative;
  transition: all 0.3s;
}

.booking-card:hover {
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
}

.booking-status {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.booking-status.pending {
  background: #fff3cd;
  color: #856404;
}

.booking-status.confirmed {
  background: #d1ecf1;
  color: #0c5460;
}

.booking-status.completed {
  background: #d4edda;
  color: #155724;
}

.booking-info h4 {
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.booking-detail {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.detail-icon {
  font-size: 16px;
}

.booking-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-join,
.btn-cancel,
.btn-feedback {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.3s;
}

.btn-join {
  color: #fff;
  background: #27ae60;
}

.btn-join:hover {
  background: #229954;
}

.btn-cancel {
  color: #666;
  background: #fff;
  border: 2px solid #e0e0e0;
}

.btn-cancel:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}

.btn-feedback {
  color: #fff;
  background: #d4524f;
}

.btn-feedback:hover {
  background: #c0392b;
}

/* 课程列表 */
.courses-list {
  display: grid;
  gap: 20px;
}

.course-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 25px;
  display: grid;
  grid-template-columns: 100px 1fr auto;
  gap: 20px;
  align-items: center;
  transition: all 0.3s;
}

.course-card:hover {
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
}

.course-cover {
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.course-progress-ring {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 4px solid #d4524f;
}

.progress-text {
  font-size: 18px;
  font-weight: 700;
  color: #d4524f;
}

.course-info h4 {
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 10px;
}

.course-stats {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #d4524f;
  transition: width 0.3s;
}

.btn-continue {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 8px;
  transition: all 0.3s;
  white-space: nowrap;
}

.btn-continue:hover {
  background: #c0392b;
}

/* 设置表单 */
.settings-form {
  max-width: 600px;
}

.form-group {
  margin-bottom: 25px;
}

.form-group label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 10px;
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group input[type="date"] {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.3s;
}

.form-group input:focus {
  border-color: #d4524f;
  outline: none;
}

.radio-group {
  display: flex;
  gap: 20px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 400;
}

.radio-label input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.btn-save {
  padding: 14px 40px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
  margin-top: 10px;
}

.btn-save:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

/* 页脚 */
.footer {
  background: #2d3436;
  padding: 40px 0;
  text-align: center;
  color: #b2bec3;
}

/* 响应式 */
@media (max-width: 768px) {
  .nav-container {
    padding: 15px 20px;
  }

  .nav-menu {
    gap: 15px;
  }

  .nav-link {
    font-size: 14px;
  }

  .user-header {
    padding: 80px 20px 30px;
  }

  .user-avatar {
    width: 60px;
    height: 60px;
    font-size: 24px;
  }

  .user-details h2 {
    font-size: 22px;
  }

  .content-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
  }

  .nav-item {
    flex-direction: column;
    gap: 5px;
    padding: 12px 20px;
    border-left: none;
    border-bottom: 3px solid transparent;
    white-space: nowrap;
  }

  .nav-item.active {
    border-left: none;
    border-bottom-color: #d4524f;
  }

  .main-content {
    padding: 25px 20px;
  }

  .course-card {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .course-cover {
    margin: 0 auto;
  }
}
</style>
