<template>
  <div class="booking">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/assessment/assessment" class="nav-link">能量测评</router-link></li>
          <li><router-link to="/pages/booking/booking" class="nav-link active">预约咨询</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 页面标题 -->
    <section class="page-header">
      <div class="container">
        <h1>预约咨询</h1>
        <p>选择适合你的服务套餐<br>开启你的个人成长之旅</p>
      </div>
    </section>

    <!-- 预约流程 -->
    <section class="booking-section">
      <div class="container">
        <!-- 选择服务 -->
        <div v-if="!selectedService" class="service-selection">
          <h2>选择服务套餐</h2>

          <div class="services-grid">
            <div class="service-option" @click="selectService('basic')">
              <div class="service-badge">入门</div>
              <h3>个人能量地图解读</h3>
              <div class="service-price">¥499 - ¥699</div>
              <ul class="service-includes">
                <li>3-5页专业报告</li>
                <li>60分钟深度解读</li>
                <li>八字/紫微基础结构</li>
                <li>性格动力与能量模式</li>
                <li>关系模式分析</li>
                <li>职业优势倾向</li>
              </ul>
              <button class="btn-select">选择此套餐</button>
            </div>

            <div class="service-option featured" @click="selectService('advanced')">
              <div class="service-badge recommended">推荐</div>
              <h3>个人成长深度咨询</h3>
              <div class="service-price">¥1599 - ¥3599</div>
              <ul class="service-includes">
                <li>3-4次深度咨询</li>
                <li>完整能量结构分析</li>
                <li>能量消耗点识别</li>
                <li>关系模式深度探索</li>
                <li>天赋优势挖掘</li>
                <li>个性化行动方案</li>
              </ul>
              <button class="btn-select primary">选择此套餐</button>
            </div>

            <div class="service-option" @click="selectService('trial')">
              <div class="service-badge">体验</div>
              <h3>种子用户体验</h3>
              <div class="service-price">¥99 - ¥199</div>
              <ul class="service-includes">
                <li>个人成长地图</li>
                <li>基础解读服务</li>
                <li>能量特质概览</li>
                <li>成长方向建议</li>
                <li>限时优惠价格</li>
                <li>收集用户反馈</li>
              </ul>
              <button class="btn-select">选择此套餐</button>
            </div>
          </div>
        </div>

        <!-- 预约表单 -->
        <div v-else class="booking-form-section">
          <button class="btn-back-service" @click="selectedService = null">← 返回选择服务</button>

          <div class="selected-service-info">
            <h3>已选择：{{ getServiceName(selectedService) }}</h3>
            <p class="service-price-info">{{ getServicePrice(selectedService) }}</p>
          </div>

          <form class="booking-form" @submit.prevent="submitBooking">
            <h2>填写预约信息</h2>

            <div class="form-group">
              <label>姓名 <span class="required">*</span></label>
              <input v-model="bookingData.name" type="text" placeholder="请输入你的姓名" required>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>性别 <span class="required">*</span></label>
                <div class="radio-group">
                  <label class="radio-label">
                    <input v-model="bookingData.gender" type="radio" value="male" required>
                    <span>男</span>
                  </label>
                  <label class="radio-label">
                    <input v-model="bookingData.gender" type="radio" value="female" required>
                    <span>女</span>
                  </label>
                </div>
              </div>

              <div class="form-group">
                <label>联系方式 <span class="required">*</span></label>
                <input v-model="bookingData.contact" type="text" placeholder="手机号或微信" required>
              </div>
            </div>

            <div class="form-group">
              <label>出生日期 <span class="required">*</span></label>
              <div class="date-inputs">
                <input v-model="bookingData.birthYear" type="number" placeholder="年" min="1900" max="2026" required>
                <input v-model="bookingData.birthMonth" type="number" placeholder="月" min="1" max="12" required>
                <input v-model="bookingData.birthDay" type="number" placeholder="日" min="1" max="31" required>
              </div>
            </div>

            <div class="form-group">
              <label>出生时间 <span class="optional">(选填)</span></label>
              <div class="time-inputs">
                <input v-model="bookingData.birthHour" type="number" placeholder="时" min="0" max="23">
                <input v-model="bookingData.birthMinute" type="number" placeholder="分" min="0" max="59">
              </div>
            </div>

            <div class="form-group">
              <label>期望咨询时间 <span class="required">*</span></label>
              <select v-model="bookingData.preferredTime" required>
                <option value="">请选择</option>
                <option value="weekday-morning">工作日上午 (9:00-12:00)</option>
                <option value="weekday-afternoon">工作日下午 (14:00-18:00)</option>
                <option value="weekday-evening">工作日晚上 (19:00-21:00)</option>
                <option value="weekend-morning">周末上午 (9:00-12:00)</option>
                <option value="weekend-afternoon">周末下午 (14:00-18:00)</option>
                <option value="weekend-evening">周末晚上 (19:00-21:00)</option>
              </select>
            </div>

            <div class="form-group">
              <label>当前最关注的议题 <span class="required">*</span></label>
              <div class="checkbox-group">
                <label class="checkbox-label" v-for="topic in topics" :key="topic.value">
                  <input type="checkbox" :value="topic.value" v-model="bookingData.topics">
                  <span>{{ topic.label }}</span>
                </label>
              </div>
            </div>

            <div class="form-group">
              <label>补充说明 <span class="optional">(选填)</span></label>
              <textarea
                v-model="bookingData.notes"
                placeholder="如果有其他想要了解的具体问题，可以在这里补充..."
                rows="4"
              ></textarea>
            </div>

            <div class="form-notice">
              <p>📌 提交后，我们的咨询师将在24小时内与你联系，确认具体咨询时间</p>
            </div>

            <button type="submit" class="btn-submit-booking">提交预约</button>
          </form>
        </div>

        <!-- 预约成功 -->
        <div v-if="bookingSuccess" class="booking-success-modal" @click="bookingSuccess = false">
          <div class="success-content" @click.stop>
            <div class="success-icon">✓</div>
            <h2>预约成功！</h2>
            <p>我们已收到你的预约信息</p>
            <p class="success-detail">咨询师将在24小时内通过 <strong>{{ bookingData.contact }}</strong> 与你联系</p>
            <div class="success-actions">
              <button @click="bookingSuccess = false" class="btn-close">关闭</button>
              <button @click="goToHome" class="btn-home">返回首页</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 离火引 InnerSeek. 欢迎来到「离火引」，开启你的"灵魂战略"第一步。</p>
      </div>
    </footer>
  </div>
</template>

<script>
export default {
  name: 'Booking',
  data() {
    return {
      selectedService: null,
      bookingSuccess: false,
      bookingData: {
        name: '',
        gender: '',
        contact: '',
        birthYear: '',
        birthMonth: '',
        birthDay: '',
        birthHour: '',
        birthMinute: '',
        preferredTime: '',
        topics: [],
        notes: ''
      },
      topics: [
        { value: 'career', label: '职业发展' },
        { value: 'relationship', label: '亲密关系' },
        { value: 'family', label: '家庭议题' },
        { value: 'self', label: '自我价值' },
        { value: 'growth', label: '个人成长' },
        { value: 'stress', label: '压力焦虑' }
      ]
    }
  },
  methods: {
    selectService(service) {
      this.selectedService = service
      window.scrollTo(0, 0)
    },
    getServiceName(service) {
      const names = {
        trial: '种子用户体验',
        basic: '个人能量地图解读',
        advanced: '个人成长深度咨询'
      }
      return names[service] || ''
    },
    getServicePrice(service) {
      const prices = {
        trial: '¥99 - ¥199',
        basic: '¥499 - ¥699',
        advanced: '¥1599 - ¥3599'
      }
      return prices[service] || ''
    },
    submitBooking() {
      // 验证必填项
      if (!this.bookingData.name || !this.bookingData.gender || !this.bookingData.contact ||
          !this.bookingData.birthYear || !this.bookingData.birthMonth || !this.bookingData.birthDay ||
          !this.bookingData.preferredTime || this.bookingData.topics.length === 0) {
        alert('请填写所有必填项')
        return
      }

      // 模拟提交
      console.log('预约信息：', {
        service: this.selectedService,
        ...this.bookingData
      })

      this.bookingSuccess = true
    },
    goToHome() {
      this.$router.push('/pages/home/home')
    }
  }
}
</script>

<style scoped>
.booking {
  width: 100%;
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

/* 页面标题 */
.page-header {
  padding: 140px 20px 80px;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
  text-align: center;
}

.page-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 20px;
}

.page-header p {
  font-size: 18px;
  color: #636e72;
  line-height: 1.8;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 预约区域 */
.booking-section {
  padding: 80px 0;
  background: #fff;
  min-height: 600px;
}

/* 服务选择 */
.service-selection h2 {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  color: #2d3436;
  margin-bottom: 50px;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 30px;
  max-width: 1100px;
  margin: 0 auto;
}

.service-option {
  background: #f8f9fa;
  border-radius: 20px;
  padding: 35px;
  position: relative;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.service-option:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.1);
  border-color: #d4524f;
}

.service-option.featured {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border-color: #d4524f;
}

.service-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #666;
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.service-badge.recommended {
  background: #d4524f;
}

.service-option h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.service-price {
  font-size: 28px;
  font-weight: 700;
  color: #d4524f;
  margin-bottom: 25px;
}

.service-includes {
  margin-bottom: 25px;
}

.service-includes li {
  font-size: 15px;
  color: #666;
  line-height: 2;
  padding-left: 20px;
  position: relative;
}

.service-includes li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
}

.btn-select {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  color: #d4524f;
  border: 2px solid #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-select:hover {
  background: #d4524f;
  color: #fff;
}

.btn-select.primary {
  background: #d4524f;
  color: #fff;
}

.btn-select.primary:hover {
  background: #c0392b;
}

/* 预约表单区域 */
.booking-form-section {
  max-width: 700px;
  margin: 0 auto;
}

.btn-back-service {
  padding: 10px 20px;
  font-size: 14px;
  color: #666;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 30px;
  transition: all 0.3s;
}

.btn-back-service:hover {
  background: #e0e0e0;
}

.selected-service-info {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  padding: 25px;
  border-radius: 12px;
  margin-bottom: 40px;
  text-align: center;
  border: 2px solid #d4524f;
}

.selected-service-info h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 10px;
}

.service-price-info {
  font-size: 20px;
  font-weight: 700;
  color: #d4524f;
}

/* 表单 */
.booking-form {
  background: #f8f9fa;
  padding: 40px;
  border-radius: 15px;
}

.booking-form h2 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 30px;
  text-align: center;
}

.form-group {
  margin-bottom: 25px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-group label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 10px;
}

.required {
  color: #d4524f;
}

.optional {
  color: #999;
  font-weight: 400;
  font-size: 13px;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.3s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #d4524f;
  outline: none;
}

.date-inputs,
.time-inputs {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 10px;
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

.checkbox-group {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 400;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.form-notice {
  background: #fff;
  padding: 15px 20px;
  border-radius: 8px;
  border-left: 4px solid #d4524f;
  margin: 25px 0;
}

.form-notice p {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

.btn-submit-booking {
  width: 100%;
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-submit-booking:hover {
  background: #c0392b;
  transform: translateY(-2px);
}

/* 预约成功弹窗 */
.booking-success-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.success-content {
  background: #fff;
  padding: 50px;
  border-radius: 20px;
  text-align: center;
  max-width: 500px;
  margin: 20px;
}

.success-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #27ae60;
  color: #fff;
  font-size: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 25px;
}

.success-content h2 {
  font-size: 28px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 15px;
}

.success-content p {
  font-size: 16px;
  color: #666;
  margin-bottom: 10px;
}

.success-detail {
  font-size: 15px;
  color: #555;
  margin-top: 20px;
}

.success-detail strong {
  color: #d4524f;
}

.success-actions {
  display: flex;
  gap: 15px;
  margin-top: 30px;
}

.btn-close,
.btn-home {
  flex: 1;
  padding: 14px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-close {
  color: #666;
  background: #f8f9fa;
}

.btn-close:hover {
  background: #e0e0e0;
}

.btn-home {
  color: #fff;
  background: #d4524f;
}

.btn-home:hover {
  background: #c0392b;
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
    gap: 12px;
  }

  .nav-link {
    font-size: 13px;
  }

  .page-header {
    padding: 100px 20px 60px;
  }

  .page-header h1 {
    font-size: 32px;
  }

  .booking-section {
    padding: 40px 0;
  }

  .services-grid {
    grid-template-columns: 1fr;
  }

  .booking-form {
    padding: 25px 20px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .checkbox-group {
    grid-template-columns: 1fr;
  }

  .success-content {
    padding: 35px 25px;
  }

  .success-actions {
    flex-direction: column;
  }
}
</style>
