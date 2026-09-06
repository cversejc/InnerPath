<template>
  <div class="page-shell services">
    <BrandNav />

    <section class="page-header">
      <div class="container header-inner">
        <p class="section-kicker">CHENJIAN / FI + TE</p>
        <h1>把看见自己，变成可使用的方向</h1>
        <p>辰鉴用 fi 端写人生说明书，用 te 端陪你做行动与决策。不是替你判断，而是让你更有依据地选择。</p>
      </div>
    </section>

    <section class="section-band">
      <div class="container services-list">
        <article class="paper-card service-item">
          <div class="service-meta">
            <span class="seal-badge">FI / 人生说明书</span>
            <p class="service-price">¥499 - ¥699</p>
          </div>
          <div class="service-copy">
            <h2>辰鉴·人生说明书</h2>
            <p class="service-intro">一份写给你的个人说明书：从先天属性出发，照见当下的位置与人生重复出现的题目。</p>
            <div class="service-columns">
              <div>
                <h3>服务内容</h3>
                <ul class="service-list">
                  <li>性格密码：天赋、弱点与暗面天赋</li>
                  <li>能量通路：什么让你充电、什么让你耗电</li>
                  <li>关系模式：你如何与重要他人相处</li>
                  <li>核心矛盾与人生重复模式</li>
                </ul>
              </div>
              <div>
                <h3>适合人群</h3>
                <p>想先知道“我是谁、我卡在哪”，再决定下一步怎么走的人。</p>
              </div>
            </div>
            <button class="secondary-button" @click="goToBooking">预约解读</button>
          </div>
        </article>

        <article class="paper-card service-item featured">
          <div class="service-meta">
            <span class="seal-badge">TE / 行动与决策</span>
            <p class="service-price">¥1599 - ¥3599</p>
          </div>
          <div class="service-copy">
            <h2>辰鉴·行动与决策</h2>
            <p class="service-intro">把说明书带回现实：围绕一个具体问题，找到能执行、能复盘、适合你当下时序的行动方案。</p>
            <div class="service-columns">
              <div>
                <h3>服务内容</h3>
                <ul class="service-list">
                  <li>60 分钟聚焦一个现实议题</li>
                  <li>区分个人属性与社会化评价</li>
                  <li>用舍由时，行藏在我</li>
                  <li>个性化日历、陪伴与复盘</li>
                </ul>
              </div>
              <div>
                <h3>适合人群</h3>
                <p>面对就业、关系、家庭或自我价值选择，希望不被“你应该怎样”绑住的人。</p>
              </div>
            </div>
            <button class="primary-button" @click="goToBooking">立即预约</button>
          </div>
        </article>

        <article class="paper-card service-item">
          <div class="service-meta">
            <span class="seal-badge">共鉴 / 理论与实践</span>
            <p class="service-price">¥399 - ¥999</p>
          </div>
          <div class="service-copy">
            <h2>辰鉴·共鉴计划</h2>
            <p class="service-intro">和一群愿意长期理解自己的人，一起学习、记录、实践，让理论在生活里长出答案。</p>
            <div class="service-columns">
              <div>
                <h3>课程内容</h3>
                <ul class="service-list">
                  <li>玄学、心理学、哲学的分工</li>
                  <li>从见自己到知其序、行其路</li>
                  <li>真实案例与决策日志练习</li>
                  <li>社群支持与阶段性打卡</li>
                </ul>
              </div>
              <div>
                <h3>适合人群</h3>
                <p>不满足于短效鸡汤，愿意在长期人本方向上持续练习的人。</p>
              </div>
            </div>
            <button class="secondary-button" @click="goToCourse">查看课程</button>
          </div>
        </article>
      </div>
    </section>

    <section class="section-band alt philosophy-section">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">PRINCIPLES</p>
          <h2 class="section-title">我们坚持的四件事</h2>
        </div>
        <div class="philosophy-grid">
          <article class="paper-card philosophy-item">
            <span>不算命</span>
            <p>命盘是照见个人属性的工具，不是决定人生的判决书。</p>
          </article>
          <article class="paper-card philosophy-item">
            <span>不审判</span>
            <p>不点评财富等级和能力高低，先肯定你已经拥有的个性与能力。</p>
          </article>
          <article class="paper-card philosophy-item">
            <span>不预言</span>
            <p>可以给希望，但不替你预测具体未来，更不制造因果恐惧。</p>
          </article>
          <article class="paper-card philosophy-item">
            <span>顺势而为</span>
            <p>有助推力时冲锋，风浪大时稳住修整，把主动权留在你手里。</p>
          </article>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
export default {
  name: 'Services',
  methods: {
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
.page-header {
  padding: 92px 0 74px;
  text-align: center;
}

.header-inner {
  max-width: 780px;
}

.page-header h1 {
  max-width: 100%;
  color: var(--ink);
  font-size: clamp(42px, 8vw, 76px);
  line-height: 1.08;
}

.page-header p:not(.section-kicker) {
  max-width: 100%;
  margin-top: 20px;
  color: var(--ink-soft);
  font-size: 18px;
  line-height: 1.75;
}

.services-list {
  display: grid;
  gap: 20px;
}

.service-item {
  display: grid;
  min-width: 0;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 28px;
  padding: clamp(22px, 4vw, 34px);
}

.service-item.featured {
  border-color: rgba(184, 92, 80, 0.34);
  background:
    linear-gradient(180deg, rgba(255, 252, 245, 0.96), rgba(255, 239, 222, 0.82));
}

.service-meta {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
  border-right: 1px solid var(--line);
  padding-right: 24px;
}

.service-price {
  color: var(--cinnabar-deep);
  font-family: "Manrope", "PingFang SC", sans-serif;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
}

.service-copy h2 {
  max-width: 100%;
  color: var(--ink);
  font-size: clamp(25px, 4vw, 38px);
  line-height: 1.18;
}

.service-intro {
  max-width: 760px;
  margin-top: 14px;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1.75;
}

.service-columns {
  display: grid;
  min-width: 0;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 28px;
  margin-top: 28px;
}

.service-columns > * {
  min-width: 0;
}

.service-columns h3 {
  margin-bottom: 12px;
  color: var(--gold-deep);
  font-size: 15px;
  letter-spacing: 0.08em;
}

.service-columns p,
.service-list {
  color: var(--ink-soft);
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.service-list {
  display: grid;
  gap: 8px;
}

.service-list li {
  position: relative;
  padding-left: 18px;
}

.service-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
}

.service-copy button {
  min-width: 190px;
  margin-top: 30px;
}

.section-heading {
  margin-bottom: 32px;
  text-align: center;
}

.philosophy-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.philosophy-item {
  padding: 22px;
}

.philosophy-item span {
  color: var(--cinnabar-deep);
  font-size: 18px;
  font-weight: 800;
}

.philosophy-item p {
  margin-top: 12px;
  color: var(--ink-soft);
  line-height: 1.7;
}

.footer {
  padding: 34px 0 calc(34px + var(--safe-bottom));
  text-align: center;
}

@media (max-width: 900px) {
  .service-item,
  .service-columns {
    grid-template-columns: 1fr;
  }

  .service-meta {
    flex-direction: row;
    align-items: center;
    border-right: 0;
    border-bottom: 1px solid var(--line);
    padding-right: 0;
    padding-bottom: 18px;
  }

  .philosophy-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 767px) {
  .page-header {
    padding: 70px 0 48px;
  }

  .page-header p:not(.section-kicker) {
    font-size: 15px;
  }

  .service-item {
    gap: 20px;
  }

  .service-meta {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .service-price {
    font-size: 24px;
  }

  .service-copy button {
    width: 100%;
  }

  .philosophy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
