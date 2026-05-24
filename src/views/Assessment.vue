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
          <h2>请填写你的基本信息</h2>
          <p class="step-desc">我们将基于你的出生时间节律，分析你的能量动力模式</p>

          <form class="assessment-form">
            <div class="form-group">
              <label>姓名 <span class="required">*</span></label>
              <input v-model="formData.name" type="text" placeholder="请输入你的姓名" required>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>性别 <span class="required">*</span></label>
                <div class="radio-group">
                  <label class="radio-label">
                    <input v-model="formData.gender" type="radio" value="male" required>
                    <span>男</span>
                  </label>
                  <label class="radio-label">
                    <input v-model="formData.gender" type="radio" value="female" required>
                    <span>女</span>
                  </label>
                </div>
              </div>

              <div class="form-group">
                <label>联系方式 <span class="required">*</span></label>
                <input v-model="formData.contact" type="text" placeholder="手机号或微信" required>
              </div>
            </div>

            <div class="form-group">
              <label>出生日期 <span class="required">*</span></label>
              <div class="date-inputs">
                <input v-model="formData.birthYear" type="number" placeholder="年" min="1900" max="2026" required>
                <input v-model="formData.birthMonth" type="number" placeholder="月" min="1" max="12" required>
                <input v-model="formData.birthDay" type="number" placeholder="日" min="1" max="31" required>
              </div>
            </div>

            <div class="form-group">
              <label>出生时间 <span class="optional">(选填，更精准)</span></label>
              <div class="time-inputs">
                <input v-model="formData.birthHour" type="number" placeholder="时" min="0" max="23">
                <input v-model="formData.birthMinute" type="number" placeholder="分" min="0" max="59">
              </div>
              <p class="form-hint">如不确定出生时间，可留空</p>
            </div>

            <div class="form-group">
              <label>出生地 <span class="optional">(选填)</span></label>
              <input v-model="formData.birthPlace" type="text" placeholder="省份-城市，如：北京-北京">
            </div>

            <button type="button" @click="nextStep" class="btn-next">下一步</button>
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
        name: '',
        gender: '',
        contact: '',
        birthYear: '',
        birthMonth: '',
        birthDay: '',
        birthHour: '',
        birthMinute: '',
        birthPlace: '',
        selectedTopics: [],
        additionalInfo: ''
      },
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
      if (!this.validateStep1()) {
        alert('请填写必填项')
        return
      }
      this.currentStep = 2
      window.scrollTo(0, 0)
    },
    prevStep() {
      this.currentStep = 1
      window.scrollTo(0, 0)
    },
    validateStep1() {
      const { name, gender, contact, birthYear, birthMonth, birthDay } = this.formData
      return name && gender && contact && birthYear && birthMonth && birthDay
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
      this.currentStep = 3
      this.isGenerating = true
      window.scrollTo(0, 0)

      try {
        // 步骤1: 解析时间节律结构
        this.genStep = 1
        await new Promise(resolve => setTimeout(resolve, 1000))

        // 步骤2: 调用 DeepSeek AI 生成报告
        this.genStep = 2
        this.generatedReport = await generateReportWithAI(this.formData)

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
  background: #f8f9fa;
  padding: 40px;
  border-radius: 15px;
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

.form-hint {
  font-size: 13px;
  color: #999;
  margin-top: 8px;
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
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
  margin-top: 20px;
}

.btn-next:hover,
.btn-submit:hover {
  background: #c0392b;
  transform: translateY(-2px);
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
    padding: 25px 20px;
  }

  .form-row {
    grid-template-columns: 1fr;
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
}
</style>
