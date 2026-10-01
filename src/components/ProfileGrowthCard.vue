<template>
  <section class="profile-growth-card paper-card" aria-labelledby="profile-growth-title">
    <div class="growth-card-head">
      <div>
        <p class="section-kicker">YOUR PROFILE / LONG-TERM CONTEXT</p>
        <h2 id="profile-growth-title">{{ safeCompletion >= 100 ? '你的个人档案已准备好' : '让辰鉴逐渐了解你' }}</h2>
      </div>
      <strong class="growth-percent" :aria-label="`档案完整度 ${safeCompletion}%`">{{ safeCompletion }}%</strong>
    </div>

    <div
      class="growth-progress"
      role="progressbar"
      aria-label="个人档案完整度"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="safeCompletion"
    >
      <span :style="{ width: `${safeCompletion}%` }"></span>
    </div>

    <div class="growth-card-body">
      <p>
        {{ safeCompletion >= 100
          ? '以后只在信息发生变化时更新，每次申请都会使用当时的资料快照，历史报告不会被改写'
          : '这不是一次性问卷，每次愿意补充一小点，之后的报告和日历就会更贴近你' }}
      </p>
      <ul v-if="suggestions.length" class="growth-suggestions" aria-label="可以继续完善的内容">
        <li v-for="suggestion in suggestions" :key="suggestion">{{ suggestion }}</li>
      </ul>
    </div>

    <div class="growth-card-foot">
      <button type="button" class="secondary-button growth-action" @click="$emit('edit')">
        {{ safeCompletion >= 100 ? '查看 / 更新档案' : '继续完善档案' }}
      </button>
      <span v-if="lastConfirmedAt" class="growth-meta">最近确认：{{ formatDate(lastConfirmedAt) }}</span>
      <span v-else class="growth-meta">核心资料确认后即可跨场景复用</span>
    </div>
  </section>
</template>

<script>
export default {
  name: 'ProfileGrowthCard',
  props: {
    profile: {
      type: Object,
      default: () => ({})
    },
    completion: {
      type: [Number, String],
      default: 0
    },
    lastConfirmedAt: {
      type: [String, Date, null],
      default: null
    }
  },
  emits: ['edit'],
  computed: {
    safeCompletion() {
      const value = Number(this.completion)
      if (!Number.isFinite(value)) return 0
      return Math.min(100, Math.max(0, Math.round(value)))
    },
    suggestions() {
      if (this.safeCompletion >= 100) return []
      const profile = this.profile || {}
      const hints = []
      if (!String(profile.birth_place || '').trim()) hints.push('补充到省 / 市出生地，可帮助做真太阳时校正')
      if (!profile.birth_time_precision || profile.birth_time_precision === 'unknown') hints.push('出生时间不确定没关系，以后想起来时再补充')
      if (!profile.current_residence && !profile.occupation_status) hints.push('补充一条当前近况，让建议更贴近你的现实')
      if (!profile.preferred_content_depth) hints.push('告诉我们你喜欢简洁还是深入的内容')
      return hints.slice(0, 2)
    }
  },
  methods: {
    formatDate(value) {
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return '—'
      return date.toLocaleDateString('zh-CN')
    }
  }
}
</script>

<style scoped>
.profile-growth-card {
  display: grid;
  gap: 18px;
  padding: clamp(20px, 3vw, 30px);
  border-color: rgba(139, 90, 20, .18);
  background:
    linear-gradient(135deg, rgba(255, 250, 240, .96), rgba(250, 238, 215, .74)),
    var(--surface-strong, #fffaf0);
}

.growth-card-head,
.growth-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.growth-card-head h2 {
  margin-top: 6px;
  color: var(--ink, #2f241b);
  font-family: var(--font-display, Georgia, serif);
  font-size: clamp(22px, 3vw, 32px);
  line-height: 1.2;
}

.growth-percent {
  flex: 0 0 auto;
  color: var(--cinnabar-deep, #9e3f35);
  font-family: var(--font-display, Georgia, serif);
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1;
}

.growth-progress {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(181, 87, 76, .12);
}

.growth-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--cinnabar, #b5574c), var(--gold, #d9ba62));
  transition: width 420ms var(--ease-out, ease);
}

.growth-card-body {
  display: grid;
  gap: 10px;
  color: var(--ink-soft, #614d3d);
  line-height: 1.75;
}

.growth-card-body p {
  max-width: 760px;
}

.growth-suggestions {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--gold-deep, #8b5a14);
  font-size: 14px;
}

.growth-suggestions li {
  position: relative;
  padding-left: 18px;
}

.growth-suggestions li::before {
  position: absolute;
  left: 0;
  top: .75em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold, #d9ba62);
  content: '';
}

.growth-action {
  min-width: 148px;
}

.growth-meta {
  color: var(--muted, #7d6653);
  font-size: 13px;
  line-height: 1.5;
  text-align: right;
}

@media (max-width: 560px) {
  .profile-growth-card {
    gap: 15px;
    padding: 18px 16px;
  }

  .growth-card-head {
    align-items: flex-start;
  }

  .growth-card-head h2 {
    font-size: 24px;
  }

  .growth-card-foot {
    align-items: stretch;
    flex-direction: column;
  }

  .growth-action {
    width: 100%;
  }

  .growth-meta {
    text-align: left;
  }
}
</style>
