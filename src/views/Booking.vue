<template>
  <div class="page-shell booking">
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/assessment/assessment" class="nav-link">测评</router-link></li>
          <li><router-link to="/pages/booking/booking" class="nav-link active">预约</router-link></li>
        </ul>
      </div>
    </nav>

    <section class="page-header">
      <div class="container header-inner">
        <p class="section-kicker">BOOKING</p>
        <h1>预约咨询</h1>
        <p>选择适合当下阶段的服务，再留下你的基本信息。</p>
      </div>
    </section>

    <section class="section-band booking-section">
      <div class="container booking-container">
        <div v-if="!selectedService" class="service-selection">
          <div class="section-heading">
            <p class="section-kicker">CHOOSE YOUR MAP</p>
            <h2 class="section-title">先选择一套服务</h2>
          </div>

          <div class="service-options">
            <article class="paper-card service-option" @click="selectService('basic')">
              <span class="seal-badge">入门</span>
              <h3>个人能量地图解读</h3>
              <p class="service-price">¥499 - ¥699</p>
              <ul>
                <li>3-5 页专业报告</li>
                <li>60 分钟深度解读</li>
                <li>八字 / 紫微基础结构</li>
                <li>关系模式与职业优势</li>
              </ul>
              <button class="secondary-button">选择此服务</button>
            </article>

            <article class="paper-card service-option featured" @click="selectService('advanced')">
              <span class="seal-badge">推荐</span>
              <h3>个人成长深度咨询</h3>
              <p class="service-price">¥1599 - ¥3599</p>
              <ul>
                <li>3-4 次深度咨询</li>
                <li>完整能量结构分析</li>
                <li>能量消耗点识别</li>
                <li>个性化行动方案</li>
              </ul>
              <button class="primary-button">选择此服务</button>
            </article>

            <article class="paper-card service-option" @click="selectService('trial')">
              <span class="seal-badge">体验</span>
              <h3>种子用户体验</h3>
              <p class="service-price">¥99 - ¥199</p>
              <ul>
                <li>个人成长地图</li>
                <li>基础解读服务</li>
                <li>能量特质概览</li>
                <li>成长方向建议</li>
              </ul>
              <button class="secondary-button">选择此服务</button>
            </article>
          </div>
        </div>

        <div v-else class="booking-form-section">
          <button class="back-link" @click="selectedService = null">返回服务选择</button>

          <div class="selected-service paper-card">
            <span class="seal-badge">已选择</span>
            <h2>{{ getServiceName(selectedService) }}</h2>
            <p>{{ getServicePrice(selectedService) }}</p>
          </div>

          <form class="booking-form form-panel" @submit.prevent="submitBooking">
            <div class="step-heading">
              <p class="section-kicker">CONTACT</p>
              <h2>填写预约信息</h2>
            </div>

            <div class="form-grid two">
              <div class="form-group">
                <label>姓名 <span class="required">*</span></label>
                <input v-model="bookingData.name" type="text" placeholder="请输入你的姓名" required>
              </div>

              <div class="form-group">
                <label>联系方式 <span class="required">*</span></label>
                <input v-model="bookingData.contact" type="text" placeholder="手机号或微信" required>
              </div>
            </div>

            <div class="form-group">
              <label>性别 <span class="required">*</span></label>
              <div class="radio-cards">
                <label :class="{ selected: bookingData.gender === 'male' }">
                  <input v-model="bookingData.gender" type="radio" value="male" required>
                  <span>男</span>
                </label>
                <label :class="{ selected: bookingData.gender === 'female' }">
                  <input v-model="bookingData.gender" type="radio" value="female" required>
                  <span>女</span>
                </label>
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
              <div class="checkbox-grid">
                <label
                  v-for="topic in topics"
                  :key="topic.value"
                  :class="{ selected: bookingData.topics.includes(topic.value) }"
                >
                  <input type="checkbox" :value="topic.value" v-model="bookingData.topics">
                  <span>{{ topic.label }}</span>
                </label>
              </div>
            </div>

            <div class="form-group">
              <label>补充说明 <span class="optional">(选填)</span></label>
              <textarea
                v-model="bookingData.notes"
                placeholder="如果有具体问题，可以写在这里。"
                rows="4"
              ></textarea>
            </div>

            <div class="form-notice">
              提交后，咨询师会在 24 小时内与你联系，确认具体咨询时间。
            </div>

            <button type="submit" class="primary-button full-width">提交预约</button>
          </form>
        </div>

        <div v-if="bookingSuccess" class="booking-success-modal" @click="bookingSuccess = false">
          <div class="success-content paper-card" @click.stop>
            <span class="seal-badge">预约成功</span>
            <h2>我们已收到你的预约信息</h2>
            <p>咨询师将通过 <strong>{{ bookingData.contact }}</strong> 与你联系。</p>
            <div class="success-actions">
              <button @click="bookingSuccess = false" class="secondary-button">关闭</button>
              <button @click="goToHome" class="primary-button">返回首页</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 离火引 InnerSeek. 开启你的灵魂战略第一步。</p>
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
      if (!this.bookingData.name || !this.bookingData.gender || !this.bookingData.contact ||
          !this.bookingData.birthYear || !this.bookingData.birthMonth || !this.bookingData.birthDay ||
          !this.bookingData.preferredTime || this.bookingData.topics.length === 0) {
        alert('请填写所有必填项')
        return
      }

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
.page-header {
  padding: 82px 0 58px;
  text-align: center;
}

.header-inner {
  max-width: 720px;
}

.page-header h1 {
  font-size: clamp(40px, 8vw, 72px);
  line-height: 1.08;
}

.page-header p:not(.section-kicker) {
  margin-top: 18px;
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1.75;
}

.booking-container {
  max-width: 1100px;
}

.section-heading,
.step-heading {
  margin-bottom: 26px;
  text-align: center;
}

.service-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.service-option {
  display: flex;
  min-width: 0;
  min-height: 420px;
  flex-direction: column;
  padding: 24px;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.service-option:hover {
  transform: translateY(-3px);
}

.service-option.featured {
  border-color: rgba(184, 92, 80, 0.34);
  background:
    linear-gradient(180deg, rgba(255, 252, 245, 0.96), rgba(255, 239, 222, 0.82));
}

.service-option h3 {
  max-width: 100%;
  margin-top: 18px;
  color: var(--ink);
  font-size: 24px;
  line-height: 1.3;
}

.service-price {
  margin: 14px 0 18px;
  color: var(--cinnabar-deep);
  font-family: "Manrope", "PingFang SC", sans-serif;
  font-size: 25px;
  font-weight: 900;
}

.service-option ul {
  display: grid;
  min-width: 0;
  gap: 9px;
  margin-bottom: 24px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.service-option li {
  position: relative;
  padding-left: 18px;
  overflow-wrap: anywhere;
}

.service-option li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
}

.service-option button {
  width: 100%;
  margin-top: auto;
}

.booking-form-section {
  max-width: 760px;
  min-width: 0;
  margin: 0 auto;
}

.back-link {
  margin-bottom: 16px;
  color: var(--cinnabar-deep);
  font-weight: 800;
}

.selected-service {
  margin-bottom: 18px;
  padding: 22px;
  text-align: center;
}

.selected-service h2 {
  margin-top: 12px;
  font-size: clamp(24px, 5vw, 34px);
}

.selected-service p {
  margin-top: 8px;
  color: var(--cinnabar-deep);
  font-family: "Manrope", sans-serif;
  font-size: 22px;
  font-weight: 900;
}

.booking-form {
  display: grid;
  gap: 22px;
  padding: clamp(22px, 4vw, 36px);
}

.booking-form h2 {
  font-size: clamp(26px, 5vw, 38px);
}

.form-grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-group {
  display: grid;
  min-width: 0;
  gap: 10px;
}

.form-group label {
  color: var(--ink);
  font-weight: 800;
}

.required {
  color: var(--cinnabar-deep);
}

.optional {
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 14px 16px;
}

.radio-cards,
.checkbox-grid {
  display: grid;
  gap: 10px;
}

.radio-cards {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.checkbox-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.radio-cards label,
.checkbox-grid label {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255, 250, 240, 0.64);
  padding: 13px 14px;
  color: var(--ink-soft);
}

.radio-cards label.selected,
.checkbox-grid label.selected {
  border-color: rgba(184, 92, 80, 0.5);
  background: rgba(255, 239, 222, 0.78);
  color: var(--ink);
}

.date-inputs {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
}

.time-inputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-notice {
  border-left: 3px solid var(--cinnabar);
  border-radius: 14px;
  background: rgba(255, 250, 240, 0.66);
  padding: 14px 16px;
  color: var(--ink-soft);
  line-height: 1.65;
}

.full-width {
  width: 100%;
}

.booking-success-modal {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(47, 36, 27, 0.48);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}

.success-content {
  width: min(460px, 100%);
  padding: 30px;
  text-align: center;
}

.success-content h2 {
  margin-top: 14px;
  font-size: 28px;
}

.success-content p {
  margin-top: 12px;
  color: var(--ink-soft);
  line-height: 1.7;
}

.success-content strong {
  color: var(--cinnabar-deep);
}

.success-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 24px;
}

.footer {
  padding: 34px 0 calc(34px + var(--safe-bottom));
  text-align: center;
}

@media (max-width: 900px) {
  .service-options {
    grid-template-columns: 1fr;
  }

  .service-option {
    min-height: 0;
  }
}

@media (max-width: 767px) {
  .page-header {
    padding: 66px 0 42px;
  }

  .form-grid.two,
  .checkbox-grid,
  .success-actions {
    grid-template-columns: 1fr;
  }

  .date-inputs {
    gap: 8px;
  }

  .booking-form {
    gap: 20px;
  }
}
</style>
