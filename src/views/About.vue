<template>
  <div class="page-shell about">
    <BrandNav />

    <section class="page-header about-header">
      <div class="container header-inner">
        <p class="section-kicker">ABOUT CHENJIAN</p>
        <h1>星辰引路，镜子照见</h1>
        <p>辰鉴不是替你算出答案，而是帮你看见：你是谁、你正处在哪个时序，以及下一步如何把主动权留在自己手里。</p>
      </div>
    </section>

    <section class="section-band about-story">
      <div class="container about-story-grid">
        <div>
          <p class="section-kicker">OUR STARTING POINT</p>
          <h2 class="section-title">我们不想再给人一张“应该怎样”的答卷</h2>
        </div>
        <div class="paper-card story-card">
          <p>当一个人遇到就业、关系、家庭或人生方向的困惑时，社会往往很快给出评价：你不够努力、太理想化、想得太多，或者应该立刻改变。</p>
          <p>辰鉴选择从另一条路开始。我们先肯定一个人的真实能力、感受和独特性，再把所谓的“错误”拆成阶段、环境与能量堵点。</p>
          <p class="emphasis">反者道之动：在功利和短效之外，长期地把人放回中心。</p>
        </div>
      </div>
    </section>

    <section class="section-band alt">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">THE PRODUCT SPINE</p>
          <h2 class="section-title">fi 端与 te 端，先照见再行动</h2>
          <p class="section-desc">一端写给“理解自己”的需要，一端写给“把理解带回生活”的需要。它们共同指向：见自己，知其序，行其路。</p>
        </div>
        <div class="axis-grid">
          <article class="paper-card axis-card axis-fi">
            <span class="axis-label">FI / INNER MAP</span>
            <h3>人生说明书</h3>
            <p>人生地图、宇宙坐标、人生时序解读，回答“我是谁，我卡在哪，我为什么反复遇到这道题”。</p>
            <ul>
              <li>性格密码：天赋、弱点与暗面天赋</li>
              <li>能量通路：充电点、耗电点与环境适配</li>
              <li>关系模式：在亲密关系、家庭与职场中如何互动</li>
              <li>核心矛盾：想要与恐惧、旧循环与内在小孩</li>
            </ul>
          </article>
          <article class="paper-card axis-card axis-te">
            <span class="axis-label">TE / OUTER MOVE</span>
            <h3>行动与决策</h3>
            <p>回答“我现在怎么做”。不是社会化建议，而是结合个人属性与环境时序的选择支持。</p>
            <ul>
              <li>下周就能做的 3 件最小可行行动</li>
              <li>未来 6—12 个月的能力建设方向</li>
              <li>用舍由时，行藏在我</li>
              <li>决策日历、记录、打卡与陪伴</li>
            </ul>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band principles-section">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">OUR BOUNDARIES</p>
          <h2 class="section-title">我们明确不做什么</h2>
        </div>
        <div class="boundary-grid">
          <article class="paper-card boundary-card">
            <span>01</span>
            <h3>不算命</h3>
            <p>不把命盘写成判决书，不替你决定人生层次与唯一答案。</p>
          </article>
          <article class="paper-card boundary-card">
            <span>02</span>
            <h3>不做等级评判</h3>
            <p>不点评财富等级、能力高低，也不把古代社会角色原样套在今天的人身上。</p>
          </article>
          <article class="paper-card boundary-card">
            <span>03</span>
            <h3>不做因果预言</h3>
            <p>可以给希望，但不预测客户未来的具体走向，更不制造恐惧与依赖。</p>
          </article>
          <article class="paper-card boundary-card">
            <span>04</span>
            <h3>不审判个性</h3>
            <p>社会属性的批评，回到个人属性的肯定；建议服务于你的选择，而不是要求你变成别人。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band alt translation-section">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">THREE LENSES</p>
          <h2 class="section-title">三种知识，各自负责一件事</h2>
        </div>
        <div class="lens-grid">
          <article class="paper-card lens-card">
            <span>玄学 / 八维</span>
            <h3>看见属性与能量流动</h3>
            <p>读取先天结构与变化环境，帮助我们把古老经验翻译成当代的个人能力、工作方式和选择条件。</p>
          </article>
          <article class="paper-card lens-card">
            <span>心理学</span>
            <h3>理解旧循环与可执行行动</h3>
            <p>借助潜意识、认知与行为模型，找到命运反复出题的地方，并设计新的答案。</p>
          </article>
          <article class="paper-card lens-card">
            <span>哲学</span>
            <h3>提供人生的脉络</h3>
            <p>不急着追求短效正确，而是理解“我从哪里来、现在处在哪、要怎样走自己的路”。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band about-cta">
      <div class="container cta-panel paper-card">
        <p class="section-kicker">START WITH YOURSELF</p>
        <h2>任何人，都有能力把自己的生活过好</h2>
        <p>如果你正在寻找一张不审判你的地图，辰鉴从“我是谁”开始。</p>
        <button class="primary-button" @click="goToAssessment">生成我的人生说明书</button>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
export default {
  name: 'About',
  methods: {
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    }
  }
}
</script>

<style scoped>
.about-header {
  padding: 96px 0 78px;
  text-align: center;
}

.about-header .header-inner {
  max-width: 780px;
}

.about-header h1 {
  font-size: clamp(42px, 8vw, 76px);
  line-height: 1.08;
}

.about-header p:not(.section-kicker) {
  max-width: 680px;
  margin: 22px auto 0;
  color: var(--ink-soft);
  font-size: 18px;
  line-height: 1.85;
}

.about-story-grid {
  display: grid;
  grid-template-columns: 0.86fr 1.14fr;
  gap: 38px;
  align-items: start;
}

.story-card {
  padding: clamp(26px, 4vw, 42px);
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1.9;
}

.story-card p + p {
  margin-top: 15px;
}

.story-card .emphasis {
  color: var(--cinnabar-deep);
  font-weight: 800;
}

.axis-grid,
.boundary-grid,
.lens-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.axis-card,
.boundary-card,
.lens-card {
  padding: 28px;
}

.axis-card {
  min-height: 350px;
}

.axis-card.axis-fi {
  border-top: 3px solid var(--cinnabar);
}

.axis-card.axis-te {
  border-top: 3px solid var(--jade);
}

.axis-label,
.lens-card > span {
  color: var(--gold-deep);
  font-family: "Manrope", "PingFang SC", sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.axis-card h3,
.boundary-card h3,
.lens-card h3 {
  margin-top: 14px;
  color: var(--ink);
  font-size: 24px;
}

.axis-card p,
.boundary-card p,
.lens-card p {
  margin-top: 12px;
  color: var(--ink-soft);
  line-height: 1.75;
}

.axis-card ul {
  display: grid;
  gap: 10px;
  margin-top: 22px;
  color: var(--ink-soft);
  line-height: 1.65;
}

.axis-card li {
  position: relative;
  padding-left: 18px;
}

.axis-card li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.7em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
}

.boundary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.boundary-card span {
  color: rgba(184, 92, 80, 0.38);
  font-family: "Manrope", sans-serif;
  font-size: 34px;
  font-weight: 900;
}

.boundary-card h3 {
  font-size: 20px;
}

.lens-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.about-cta {
  padding-top: 20px;
}

.cta-panel {
  padding: clamp(30px, 6vw, 70px);
  text-align: center;
}

.cta-panel h2 {
  max-width: 760px;
  margin: 15px auto 0;
  font-size: clamp(30px, 6vw, 52px);
  line-height: 1.2;
}

.cta-panel p:not(.section-kicker) {
  margin: 18px auto 26px;
  color: var(--ink-soft);
  font-size: 17px;
}

@media (max-width: 900px) {
  .about-story-grid,
  .axis-grid,
  .lens-grid {
    grid-template-columns: 1fr;
  }

  .boundary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .boundary-grid {
    grid-template-columns: 1fr;
  }

  .axis-card,
  .boundary-card,
  .lens-card {
    padding: 23px;
  }
}
</style>
