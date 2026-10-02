<template>
  <section class="profile-summary" aria-labelledby="profile-summary-title">
    <div class="profile-summary-heading">
      <div>
        <p class="section-kicker">PROFILE SNAPSHOT</p>
        <h3 id="profile-summary-title">本次将使用的个人资料</h3>
      </div>
      <VanButton native-type="button" class="secondary-button profile-summary-edit" @click="$emit('edit')">
        修改档案
      </VanButton>
    </div>
    <div class="profile-summary-grid">
      <div>
        <span>称呼</span>
        <strong>{{ profile.name || '—' }}</strong>
      </div>
      <div>
        <span>出生日期</span>
        <strong>{{ birthDateLabel }}</strong>
      </div>
      <div>
        <span>出生时间</span>
        <strong>{{ timeLabel }}</strong>
      </div>
      <div>
        <span>出生地</span>
        <strong>{{ profile.birth_place || '未填写，精度可能受影响' }}</strong>
      </div>
    </div>
    <p class="profile-summary-meta">
      档案版本 v{{ profileVersion || profile.profile_version || 1 }}<span v-if="lastConfirmedAt"> · 最近确认于 {{ formatDate(lastConfirmedAt) }}</span>
      · 之后修改档案不会改变历史报告
    </p>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'

export default {
  name: 'ProfileSummary',
  components: { VanButton },
  emits: ['edit'],
  props: {
    profile: {
      type: Object,
      required: true
    },
    profileVersion: {
      type: [Number, String],
      default: null
    },
    lastConfirmedAt: {
      type: String,
      default: null
    }
  },
  computed: {
    birthDateLabel() {
      const { birth_year: year, birth_month: month, birth_day: day } = this.profile
      if (!year || !month || !day) return '未完成'
      const monthLabel = this.profile.birth_is_leap_month ? `闰${month}月` : `${month}月`
      return `${year}年${monthLabel}${day}日 · ${this.profile.calendar_type === 'lunar' ? '农历' : '公历'}`
    },
    timeLabel() {
      const labels = { unknown: '时辰未知', approximate: '大概时间', exact: '精确时间' }
      const precision = this.profile.birth_time_precision || 'unknown'
      if (precision === 'unknown') return labels.unknown
      if (this.profile.birth_hour === null || this.profile.birth_minute === null || this.profile.birth_hour === undefined || this.profile.birth_minute === undefined) return labels[precision]
      return `${this.profile.birth_hour}时${String(this.profile.birth_minute).padStart(2, '0')}分 · ${labels[precision]}`
    }
  },
  methods: {
    formatDate(value) {
      return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
    }
  }
}
</script>

<style scoped>
.profile-summary {
  display: grid;
  gap: 16px;
  border: 1px solid rgba(184, 92, 80, .2);
  border-radius: 18px;
  padding: 18px;
  background: linear-gradient(135deg, rgba(255, 250, 240, .9), rgba(255, 240, 223, .64));
}

.profile-summary-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.profile-summary-heading h3 {
  margin-top: 4px;
  color: var(--ink);
  font-size: 20px;
}

.profile-summary-edit {
  flex: 0 0 auto;
  min-height: var(--button-height);
  border-radius: var(--button-radius);
  padding: 0 14px;
  font-size: 13px;
  font-weight: var(--weight-semibold);
  white-space: nowrap;
}

.profile-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.profile-summary-grid > div {
  display: grid;
  min-width: 0;
  gap: 4px;
  padding-right: 12px;
  border-right: 1px solid rgba(139, 90, 20, .12);
}

.profile-summary-grid > div:last-child {
  border-right: 0;
}

.profile-summary-grid span {
  color: var(--muted);
  font-size: 11px;
}

.profile-summary-grid strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.5;
  text-overflow: ellipsis;
}

.profile-summary-meta {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 640px) {
  .profile-summary-heading {
    align-items: start;
  }

  .profile-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-summary-grid > div:nth-child(2) {
    border-right: 0;
  }
}
</style>
