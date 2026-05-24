<template>
  <div class="assessment">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/assessment/assessment" class="nav-link active">能量测评</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 页面标题 -->
    <section class="page-header">
      <div class="container">
        <h1>东方能量测评</h1>
        <p>基于时间节律的个人特质分析<br>发现你的能量模式与天赋倾向</p>
      </div>
    </section>

    <!-- 测评流程 -->
    <section class="assessment-section">
      <div class="container">
        <div class="progress-bar">
          <div class="progress-step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
            <div class="step-number">1</div>
            <div class="step-label">基本信息</div>
          </div>
          <div class="progress-line" :class="{ active: currentStep > 1 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
            <div class="step-number">2</div>
            <div class="step-label">生命议题</div>
          </div>
          <div class="progress-line" :class="{ active: currentStep > 2 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 3 }">
            <div class="step-number">3</div>
            <div class="step-label">生成报告</div>
          </div>
        </div>

        <!-- 步骤1: 基本信息 -->
        <div v-if="currentStep === 1" class="step-content">
          <h2>请填写你的出生信息</h2>
          <p class="step-desc">基于你的时间节律，我们将为你绘制专属的能量地图</p>

          <form class="assessment-form">
            <!-- 性别选择 -->
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">👤</span>
                性别 <span class="required">*</span>
              </label>
              <div class="gender-selector">
                <div
                  class="gender-option"
                  :class="{ selected: formData.gender === 'male' }"
                  @click="formData.gender = 'male'"
                >
                  <span class="gender-icon male">♂</span>
                  <span class="gender-text">男</span>
                </div>
                <div
                  class="gender-option"
                  :class="{ selected: formData.gender === 'female' }"
                  @click="formData.gender = 'female'"
                >
                  <span class="gender-icon female">♀</span>
                  <span class="gender-text">女</span>
                </div>
              </div>
            </div>

            <!-- 历法类型 -->
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">📖</span>
                历法类型 <span class="required">*</span>
              </label>
              <div class="calendar-selector">
                <div
                  class="calendar-option"
                  :class="{ selected: formData.calendarType === 'solar' }"
                  @click="formData.calendarType = 'solar'"
                >
                  <div class="calendar-icon">☀️</div>
                  <div class="calendar-info">
                    <div class="calendar-title">公历（阳历）</div>
                    <div class="calendar-desc">身份证日期</div>
                  </div>
                </div>
                <div
                  class="calendar-option"
                  :class="{ selected: formData.calendarType === 'lunar' }"
                  @click="formData.calendarType = 'lunar'"
                >
                  <div class="calendar-icon">🌙</div>
                  <div class="calendar-info">
                    <div class="calendar-title">农历（阴历）</div>
                    <div class="calendar-desc">传统节日</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 出生日期 -->
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">📅</span>
                出生日期 <span class="required">*</span>
              </label>
              <div class="date-input-group">
                <div class="date-field">
                  <input
                    v-model="formData.birthYear"
                    type="tel"
                    inputmode="numeric"
                    placeholder="1990"
                    maxlength="4"
                    required
                    class="date-field-input"
                    @input="validateYear"
                  >
                  <span class="date-field-label">年</span>
                </div>
                <span class="date-divider">/</span>
                <div class="date-field">
                  <input
                    v-model="formData.birthMonth"
                    type="tel"
                    inputmode="numeric"
                    placeholder="01"
                    maxlength="2"
                    required
                    class="date-field-input"
                    @input="validateMonth"
                  >
                  <span class="date-field-label">月</span>
                </div>
                <span class="date-divider">/</span>
                <div class="date-field">
                  <input
                    v-model="formData.birthDay"
                    type="tel"
                    inputmode="numeric"
                    placeholder="01"
                    maxlength="2"
                    required
                    class="date-field-input"
                    @input="validateDay"
                  >
                  <span class="date-field-label">日</span>
                </div>
              </div>
              <p class="form-hint">💡 请按照上方选择的历法填写</p>
            </div>

            <!-- 出生时间 -->
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">⏰</span>
                出生时间 <span class="optional">(选填)</span>
              </label>
              <div class="time-accuracy-selector">
                <div
                  class="accuracy-option"
                  :class="{ selected: formData.timeAccuracy === 'unknown' }"
                  @click="selectTimeAccuracy('unknown')"
                >
                  <div class="accuracy-icon">❓</div>
                  <div class="accuracy-label">不知道</div>
                </div>
                <div
                  class="accuracy-option"
                  :class="{ selected: formData.timeAccuracy === 'approximate' }"
                  @click="selectTimeAccuracy('approximate')"
                >
                  <div class="accuracy-icon">🕐</div>
                  <div class="accuracy-label">大概时间</div>
                </div>
                <div
                  class="accuracy-option"
                  :class="{ selected: formData.timeAccuracy === 'exact' }"
                  @click="selectTimeAccuracy('exact')"
                >
                  <div class="accuracy-icon">⏱️</div>
                  <div class="accuracy-label">精确时间</div>
                </div>
              </div>

              <div v-if="formData.timeAccuracy !== 'unknown'" class="time-picker-modern">
                <div class="time-input-wrapper">
                  <input
                    v-model="formData.birthHour"
                    type="tel"
                    inputmode="numeric"
                    placeholder="08"
                    maxlength="2"
                    class="time-input"
                    @input="validateHour"
                  >
                  <span class="time-separator">:</span>
                </div>
                <div class="time-input-wrapper">
                  <input
                    v-model="formData.birthMinute"
                    type="tel"
                    inputmode="numeric"
                    placeholder="30"
                    maxlength="2"
                    class="time-input"
                    @input="validateMinute"
                  >
                </div>
              </div>
              <p class="form-hint" v-if="formData.timeAccuracy === 'unknown'">
                💡 没关系，我们会基于日期为你提供分析
              </p>
              <p class="form-hint" v-else-if="formData.timeAccuracy === 'approximate'">
                💡 大概时间也能提供较准确的分析
              </p>
              <p class="form-hint" v-else-if="formData.timeAccuracy === 'exact'">
                ✨ 精确时间将获得最准确的能量地图
              </p>
            </div>

            <!-- 出生地 -->
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">📍</span>
                出生地 <span class="optional">(选填)</span>
              </label>
              <input
                v-model="formData.birthPlace"
                type="text"
                placeholder="如：北京、上海、广州..."
                class="modern-input"
              >
              <p class="form-hint">💡 用于真太阳时校正，提升分析精度</p>
            </div>

            <button type="button" @click="nextStep" class="btn-next">
              <span>下一步</span>
              <span class="btn-arrow">→</span>
            </button>
          </form>
        </div>

        <!-- 步骤2: 生命议题 -->
        <div v-if="currentStep === 2" class="step-content">
          <h2>当前最关注的生命议题</h2>
          <p class="step-desc">选择你当前最关注的议题，帮助我们提供更精准的分析</p>

          <div class="topics-grid">
            <div
              v-for="topic in topics"
              :key="topic.id"
              class="topic-card"
              :class="{ selected: formData.selectedTopics.includes(topic.id) }"
              @click="toggleTopic(topic.id)"
            >
              <div class="topic-icon">{{ topic.icon }}</div>
              <h3>{{ topic.title }}</h3>
              <p>{{ topic.desc }}</p>
            </div>
          </div>

          <div class="form-group">
            <label>补充说明 <span class="optional">(选填)</span></label>
            <textarea
              v-model="formData.additionalInfo"
              placeholder="如果有其他想要了解的具体问题，可以在这里补充..."
              rows="4"
            ></textarea>
          </div>

          <div class="button-group">
            <button type="button" @click="prevStep" class="btn-back">上一步</button>
            <button type="button" @click="submitAssessment" class="btn-submit">生成我的能量地图</button>
          </div>
        </div>

        <!-- 步骤3: 生成中/完成 -->
        <div v-if="currentStep === 3" class="step-content">
          <div v-if="isGenerating" class="generating">
            <div class="loading-spinner"></div>
            <h2>正在生成你的专属能量地图...</h2>
            <p>我们正在分析你的时间节律特质与能量模式</p>
            <div class="generating-steps">
              <div class="gen-step" :class="{ active: genStep >= 1 }">
                <span class="check">✓</span> 解析时间节律结构
              </div>
              <div class="gen-step" :class="{ active: genStep >= 2 }">
                <span class="check">✓</span> 分析能量动力模式
              </div>
              <div class="gen-step" :class="{ active: genStep >= 3 }">
                <span class="check">✓</span> 识别关系互动特质
              </div>
              <div class="gen-step" :class="{ active: genStep >= 4 }">
                <span class="check">✓</span> 生成个性化报告
              </div>
            </div>
          </div>

          <div v-else class="result-success">
            <div class="success-icon">✓</div>
            <h2>你的能量地图已生成！</h2>
            <p>我们已将完整报告发送至你的联系方式</p>

            <div class="result-preview">
              <h3>报告预览</h3>
              <div class="preview-item">
                <strong>能量类型：</strong>{{ reportPreview.energyType }}
              </div>
              <div class="preview-item">
                <strong>核心特质：</strong>{{ reportPreview.coreTraits }}
              </div>
              <div class="preview-item">
                <strong>天赋倾向：</strong>{{ reportPreview.talents }}
              </div>
            </div>

            <div class="next-steps">
              <h3>接下来你可以：</h3>
              <div class="next-step-card">
                <h4>📊 查看完整报告</h4>
                <p>深入了解你的能量模式与成长建议</p>
                <button class="btn-action" @click="viewFullReport">查看报告</button>
              </div>
              <div class="next-step-card">
                <h4>💬 预约深度咨询</h4>
                <p>与专业咨询师一对一深度解读</p>
                <button class="btn-action" @click="goToBooking">立即预约</button>
              </div>
              <div class="next-step-card">
                <h4>📚 学习系统课程</h4>
                <p>掌握工具，开启自主成长之旅</p>
                <button class="btn-action" @click="goToCourse">查看课程</button>
              </div>
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
import { generateReportWithAI } from '../utils/aiService.js'

export default {
  name: 'Assessment',
  data() {
    return {
      currentStep: 1,
      isGenerating: false,
      genStep: 0,
      formData: {
        gender: '',
        birthYear: '',
        birthMonth: '',
        birthDay: '',
        birthHour: '',
        birthMinute: '',
        birthPlace: '',
        timeAccuracy: 'unknown',
        calendarType: 'solar',
        selectedTopics: [],
        additionalInfo: ''
      },
      years: Array.from({ length: 127 }, (_, i) => 2026 - i),
      topics: [
        { id: 'career', icon: '💼', title: '职业发展', desc: '职业选择、转型、瓶颈突破' },
        { id: 'relationship', icon: '💕', title: '亲密关系', desc: '恋爱、婚姻、关系模式' },
        { id: 'family', icon: '👨‍👩‍👧', title: '家庭议题', desc: '原生家庭、亲子关系' },
        { id: 'self', icon: '🎯', title: '自我价值', desc: '自我认同、人生意义' },
        { id: 'growth', icon: '🌱', title: '个人成长', desc: '突破局限、能力提升' },
        { id: 'stress', icon: '😰', title: '压力焦虑', desc: '情绪管理、压力应对' }
      ],
      reportPreview: {
        energyType: '创造驱动型',
        coreTraits: '独立思考、创新求变、追求自我表达',
        talents: '适合创意型、研究型工作，擅长整合资源'
      },
      generatedReport: null,
      currentReportId: null
    }
  },
  methods: {
    nextStep() {
      console.log('点击下一步，当前表单数据:', this.formData)
      if (!this.validateStep1()) {
        console.log('验证失败')
        alert('请填写必填项')
        return
      }
      console.log('验证通过，进入步骤2')
      this.currentStep = 2
      window.scrollTo(0, 0)
    },
    prevStep() {
      this.currentStep = 1
      window.scrollTo(0, 0)
    },
    validateStep1() {
      const { gender, birthYear, birthMonth, birthDay, calendarType } = this.formData
      return gender && birthYear && birthMonth && birthDay && calendarType
    },
    selectTimeAccuracy(accuracy) {
      this.formData.timeAccuracy = accuracy
      if (accuracy === 'unknown') {
        this.formData.birthHour = ''
        this.formData.birthMinute = ''
      }
    },
    validateYear(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value.length === 4) {
        const num = parseInt(value)
        if (num < 1900) value = '1900'
        if (num > 2026) value = '2026'
      }
      this.formData.birthYear = value
    },
    validateMonth(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 12) value = '12'
        if (num < 1 && value.length === 2) value = '01'
      }
      this.formData.birthMonth = value
    },
    validateDay(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 31) value = '31'
        if (num < 1 && value.length === 2) value = '01'
      }
      this.formData.birthDay = value
    },
    validateHour(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 23) value = '23'
        if (num < 0) value = '0'
      }
      this.formData.birthHour = value
    },
    validateMinute(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 59) value = '59'
        if (num < 0) value = '0'
      }
      this.formData.birthMinute = value
    },
    toggleTopic(topicId) {
      const index = this.formData.selectedTopics.indexOf(topicId)
      if (index > -1) {
        this.formData.selectedTopics.splice(index, 1)
      } else {
        this.formData.selectedTopics.push(topicId)
      }
    },
    async submitAssessment() {
      console.log('开始提交评估，表单数据:', this.formData)
      this.currentStep = 3
      this.isGenerating = true
      window.scrollTo(0, 0)

      try {
        // 步骤1: 解析时间节律结构
        this.genStep = 1
        await new Promise(resolve => setTimeout(resolve, 1000))

        // 步骤2: 调用 DeepSeek AI 生成报告
        this.genStep = 2
        console.log('准备调用 AI 服务...')
        this.generatedReport = await generateReportWithAI(this.formData)
        console.log('AI 服务返回结果:', this.generatedReport)

        // 步骤3: 分析能量动力模式
        this.genStep = 3
        await new Promise(resolve => setTimeout(resolve, 800))

        // 步骤4: 生成个性化报告
        this.genStep = 4
        await new Promise(resolve => setTimeout(resolve, 800))

        // 更新预览信息
        this.reportPreview = {
          energyType: this.generatedReport.energyProfile?.type || '综合型',
          coreTraits: this.generatedReport.energyProfile?.coreTraits || '独特的个人特质',
          talents: Array.isArray(this.generatedReport.careerGuidance?.suitablePaths)
            ? this.generatedReport.careerGuidance.suitablePaths.join('、')
            : '多元发展'
        }

        await new Promise(resolve => setTimeout(resolve, 500))
        this.isGenerating = false

        // 保存报告到本地存储
        this.saveReportToLocal()
      } catch (error) {
        console.error('报告生成失败:', error)
        alert('报告生成失败，请稍后重试')
        this.currentStep = 2
        this.isGenerating = false
      }
    },
    saveReportToLocal() {
      const reports = JSON.parse(localStorage.getItem('userReports') || '[]')
      const reportId = Date.now()
      reports.push({
        id: reportId,
        date: new Date().toISOString().split('T')[0],
        report: this.generatedReport
      })
      localStorage.setItem('userReports', JSON.stringify(reports))
      this.currentReportId = reportId
    },
    viewFullReport() {
      if (this.currentReportId) {
        this.$router.push(`/pages/report/detail?id=${this.currentReportId}`)
      }
    },
    goToBooking() {
      this.$router.push('/pages/booking/booking')
    },
    goToCourse() {
      this.$router.push('/pages/course/course')
    }
  }
}
</script>

<style scoped>
.assessment {
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
  gap: 40px;
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
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 测评区域 */
.assessment-section {
  padding: 80px 0;
  background: #fff;
  min-height: 600px;
}

/* 进度条 */
.progress-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 60px;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.step-number {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #e0e0e0;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  transition: all 0.3s;
}

.progress-step.active .step-number {
  background: #d4524f;
  color: #fff;
}

.progress-step.completed .step-number {
  background: #27ae60;
  color: #fff;
}

.step-label {
  font-size: 14px;
  color: #999;
  font-weight: 500;
}

.progress-step.active .step-label {
  color: #2d3436;
  font-weight: 600;
}

.progress-line {
  width: 100px;
  height: 3px;
  background: #e0e0e0;
  margin: 0 20px;
  transition: all 0.3s;
}

.progress-line.active {
  background: #d4524f;
}

/* 步骤内容 */
.step-content {
  max-width: 700px;
  margin: 0 auto;
}

.step-content h2 {
  font-size: 32px;
  font-weight: 700;
  color: #2d3436;
  text-align: center;
  margin-bottom: 15px;
}

.step-desc {
  text-align: center;
  color: #666;
  font-size: 16px;
  margin-bottom: 40px;
}

/* 表单 */
.assessment-form {
  background: #fff;
  padding: 0;
  border-radius: 0;
}

.form-group {
  margin-bottom: 32px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 16px;
}

.label-icon {
  font-size: 20px;
}

.required {
  color: #d4524f;
}

.optional {
  color: #999;
  font-weight: 400;
  font-size: 14px;
}

/* 性别选择器 */
.gender-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.gender-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 12px;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.gender-option:hover {
  background: #fff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.gender-option.selected {
  background: #fff;
  border-color: #d4524f;
  box-shadow: 0 2px 12px rgba(212, 82, 79, 0.15);
}

.gender-icon {
  font-size: 28px;
  margin-bottom: 4px;
  font-weight: bold;
}

.gender-icon.male {
  color: #3498db;
}

.gender-icon.female {
  color: #e74c3c;
}

.gender-text {
  font-size: 13px;
  font-weight: 600;
  color: #2d3436;
}

/* 日期输入组 */
.date-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8f9fa;
  padding: 12px 16px;
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.date-input-group:focus-within {
  background: #fff;
  border-color: #d4524f;
  box-shadow: 0 0 0 3px rgba(212, 82, 79, 0.1);
}

.date-field {
  display: flex;
  align-items: center;
  gap: 4px;
}

.date-field:first-child {
  flex: 1.5;
}

.date-field:not(:first-child) {
  flex: 1;
}

.date-field-input {
  width: 100%;
  border: none;
  background: transparent;
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  text-align: center;
  outline: none;
  padding: 4px;
}

.date-field-input::placeholder {
  color: #bbb;
  font-weight: 400;
}

.date-field-input::-webkit-outer-spin-button,
.date-field-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.date-field-label {
  font-size: 14px;
  color: #999;
  font-weight: 500;
  flex-shrink: 0;
}

.date-divider {
  font-size: 18px;
  color: #ccc;
  font-weight: 300;
  margin: 0 2px;
}

/* 简洁日期选择器（备用） */
.simple-date-picker {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 10px;
}

.date-select {
  width: 100%;
  padding: 14px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  font-size: 15px;
  background: #f8f9fa;
  color: #2d3436;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.date-select:focus {
  background-color: #fff;
  border-color: #d4524f;
  outline: none;
  box-shadow: 0 0 0 3px rgba(212, 82, 79, 0.1);
}

.date-select option {
  padding: 10px;
}

/* 原生日期选择器样式（备用） */
.modern-date-input {
  width: 100%;
  padding: 16px 20px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 16px;
  background: #f8f9fa;
  transition: all 0.3s ease;
  color: #2d3436;
  font-weight: 500;
}

.modern-date-input:focus {
  background: #fff;
  border-color: #d4524f;
  outline: none;
  box-shadow: 0 0 0 4px rgba(212, 82, 79, 0.1);
}

.modern-date-input::-webkit-calendar-picker-indicator {
  cursor: pointer;
  font-size: 18px;
  padding: 4px;
}

/* 现代日期选择器（已废弃，保留以防需要） */
.date-picker-modern {
  display: flex;
  gap: 12px;
  align-items: center;
}

.date-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8f9fa;
  padding: 16px;
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.date-input-wrapper:focus-within {
  background: #fff;
  border-color: #d4524f;
  box-shadow: 0 0 0 4px rgba(212, 82, 79, 0.1);
}

.date-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  text-align: center;
  outline: none;
}

.date-input::placeholder {
  color: #bbb;
  font-weight: 400;
}

.year-input {
  max-width: 80px;
}

.month-input,
.day-input {
  max-width: 50px;
}

.date-separator {
  font-size: 14px;
  color: #999;
  font-weight: 500;
}

/* 时间精度选择器 */
.time-accuracy-selector {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.accuracy-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.accuracy-option:hover {
  background: #fff;
  border-color: #ffd7d5;
  transform: translateY(-2px);
}

.accuracy-option.selected {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border-color: #d4524f;
  box-shadow: 0 2px 8px rgba(212, 82, 79, 0.15);
}

.accuracy-icon {
  font-size: 28px;
  margin-bottom: 6px;
}

.accuracy-label {
  font-size: 13px;
  font-weight: 600;
  color: #2d3436;
  text-align: center;
}

/* 现代时间选择器 */
.time-picker-modern {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
}

.time-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8f9fa;
  padding: 16px 20px;
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.time-input-wrapper:focus-within {
  background: #fff;
  border-color: #d4524f;
  box-shadow: 0 0 0 4px rgba(212, 82, 79, 0.1);
}

.time-input {
  width: 60px;
  border: none;
  background: transparent;
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  text-align: center;
  outline: none;
}

.time-input::placeholder {
  color: #bbb;
  font-weight: 400;
}

/* 移除 number 输入框的上下箭头 */
.time-input::-webkit-outer-spin-button,
.time-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.time-input[type="tel"] {
  -moz-appearance: textfield;
}

.time-separator {
  font-size: 24px;
  color: #999;
  font-weight: 600;
}

/* 现代输入框 */
.modern-input {
  width: 100%;
  padding: 16px 20px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 16px;
  background: #f8f9fa;
  transition: all 0.3s ease;
}

.modern-input:focus {
  background: #fff;
  border-color: #d4524f;
  outline: none;
  box-shadow: 0 0 0 4px rgba(212, 82, 79, 0.1);
}

.modern-input::placeholder {
  color: #bbb;
}

/* 历法选择器 */
.calendar-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.calendar-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.calendar-option:hover {
  background: #fff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.calendar-option.selected {
  background: #fff;
  border-color: #d4524f;
  box-shadow: 0 2px 12px rgba(212, 82, 79, 0.15);
}

.calendar-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.calendar-info {
  flex: 1;
}

.calendar-title {
  font-size: 14px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 2px;
}

.calendar-desc {
  font-size: 12px;
  color: #999;
}

.form-hint {
  font-size: 13px;
  color: #999;
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.3s;
}

.form-group input:focus,
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

/* 议题选择 */
.topics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.topic-card {
  background: #f8f9fa;
  padding: 25px;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.3s;
}

.topic-card:hover {
  border-color: #d4524f;
  transform: translateY(-3px);
}

.topic-card.selected {
  background: #fff5f5;
  border-color: #d4524f;
}

.topic-icon {
  font-size: 40px;
  margin-bottom: 15px;
}

.topic-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 8px;
}

.topic-card p {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

/* 按钮 */
.btn-next,
.btn-submit {
  width: 100%;
  padding: 18px;
  font-size: 17px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #d4524f 0%, #e74c3c 100%);
  border-radius: 16px;
  transition: all 0.3s ease;
  margin-top: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 16px rgba(212, 82, 79, 0.3);
}

.btn-next:hover,
.btn-submit:hover {
  background: linear-gradient(135deg, #c0392b 0%, #d4524f 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(212, 82, 79, 0.4);
}

.btn-next:active,
.btn-submit:active {
  transform: translateY(0);
}

.btn-arrow {
  font-size: 20px;
  transition: transform 0.3s ease;
}

.btn-next:hover .btn-arrow {
  transform: translateX(4px);
}

.button-group {
  display: flex;
  gap: 15px;
  margin-top: 30px;
}

.btn-back {
  flex: 1;
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #666;
  background: #f8f9fa;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-back:hover {
  background: #e0e0e0;
}

.btn-submit {
  flex: 2;
  margin-top: 0;
}

/* 生成中 */
.generating {
  text-align: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #d4524f;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 30px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.generating h2 {
  font-size: 28px;
  color: #2d3436;
  margin-bottom: 15px;
}

.generating p {
  color: #666;
  font-size: 16px;
  margin-bottom: 40px;
}

.generating-steps {
  max-width: 400px;
  margin: 0 auto;
  text-align: left;
}

.gen-step {
  padding: 15px 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 10px;
  color: #999;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.3s;
}

.gen-step.active {
  background: #fff5f5;
  color: #2d3436;
  font-weight: 500;
}

.gen-step .check {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e0e0e0;
  color: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.3s;
}

.gen-step.active .check {
  background: #27ae60;
  color: #fff;
}

/* 结果成功 */
.result-success {
  text-align: center;
  padding: 40px 20px;
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
  margin: 0 auto 30px;
}

.result-success h2 {
  font-size: 32px;
  color: #2d3436;
  margin-bottom: 15px;
}

.result-success > p {
  color: #666;
  font-size: 16px;
  margin-bottom: 40px;
}

.result-preview {
  background: #f8f9fa;
  padding: 30px;
  border-radius: 12px;
  margin-bottom: 40px;
  text-align: left;
}

.result-preview h3 {
  font-size: 20px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 20px;
  text-align: center;
}

.preview-item {
  padding: 12px 0;
  border-bottom: 1px solid #e0e0e0;
  font-size: 15px;
  color: #555;
}

.preview-item:last-child {
  border-bottom: none;
}

.preview-item strong {
  color: #2d3436;
  margin-right: 10px;
}

.next-steps {
  margin-top: 50px;
}

.next-steps h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 30px;
}

.next-step-card {
  background: #f8f9fa;
  padding: 25px;
  border-radius: 12px;
  margin-bottom: 15px;
  text-align: left;
}

.next-step-card h4 {
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 10px;
}

.next-step-card p {
  font-size: 14px;
  color: #666;
  margin-bottom: 15px;
}

.btn-action {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 600;
  color: #d4524f;
  border: 2px solid #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-action:hover {
  background: #d4524f;
  color: #fff;
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

  .page-header {
    padding: 100px 20px 60px;
  }

  .page-header h1 {
    font-size: 32px;
  }

  .assessment-section {
    padding: 40px 0;
  }

  .progress-bar {
    margin-bottom: 40px;
  }

  .step-number {
    width: 40px;
    height: 40px;
    font-size: 16px;
  }

  .progress-line {
    width: 50px;
    margin: 0 10px;
  }

  .step-label {
    font-size: 12px;
  }

  .step-content h2 {
    font-size: 24px;
  }

  .assessment-form {
    padding: 0;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .gender-selector {
    grid-template-columns: 1fr 1fr;
  }

  .gender-option {
    padding: 12px 10px;
  }

  .gender-icon {
    font-size: 24px;
    margin-bottom: 3px;
  }

  .gender-text {
    font-size: 12px;
  }

  .calendar-option {
    padding: 12px 14px;
  }

  .calendar-icon {
    font-size: 24px;
  }

  .calendar-title {
    font-size: 13px;
  }

  .calendar-desc {
    font-size: 11px;
  }

  .simple-date-picker {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .date-select {
    padding: 12px;
    font-size: 14px;
  }

  .date-input-group {
    padding: 10px 12px;
  }

  .date-field-input {
    font-size: 16px;
  }

  .date-field-label {
    font-size: 13px;
  }

  .date-divider {
    font-size: 16px;
  }

  .date-picker-modern {
    flex-direction: column;
    gap: 10px;
  }

  .date-input-wrapper {
    width: 100%;
  }

  .date-input {
    font-size: 16px;
  }

  .year-input,
  .month-input,
  .day-input {
    max-width: none;
  }

  .time-accuracy-selector {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .accuracy-option {
    flex-direction: row;
    justify-content: flex-start;
    padding: 14px 16px;
  }

  .accuracy-icon {
    font-size: 24px;
    margin-bottom: 0;
  }

  .accuracy-label {
    text-align: left;
  }

  .calendar-selector {
    grid-template-columns: 1fr;
  }

  .calendar-option {
    padding: 16px;
  }

  .topics-grid {
    grid-template-columns: 1fr;
  }

  .button-group {
    flex-direction: column;
  }

  .btn-submit {
    flex: 1;
  }

  .form-label {
    font-size: 15px;
  }

  .label-icon {
    font-size: 18px;
  }
}
</style>
