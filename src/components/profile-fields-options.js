export function createProfileFieldOptions() {
  return {
    genderOptions: [
      { value: 'male', label: '男', mark: '乾' },
      { value: 'female', label: '女', mark: '坤' }
    ],
    calendarOptions: [
      { value: 'solar', label: '公历', hint: '身份证日期', mark: '日' },
      { value: 'lunar', label: '农历', hint: '传统阴历', mark: '月' }
    ],
    timeOptions: [
      { value: 'unknown', label: '不知道' },
      { value: 'approximate', label: '大概时间' },
      { value: 'exact', label: '精确时间' }
    ],
    maritalOptions: [
      { value: 'single', label: '单身' },
      { value: 'dating', label: '恋爱中' },
      { value: 'married', label: '已婚' },
      { value: 'divorced', label: '离异' },
      { value: 'other', label: '其他' }
    ],
    occupationOptions: [
      { value: 'full_time', label: '全职工作' },
      { value: 'freelance', label: '自由职业' },
      { value: 'entrepreneur', label: '创业者' },
      { value: 'student', label: '学生' },
      { value: 'unemployed', label: '待业' },
      { value: 'job_seeking', label: '求职中' },
      { value: 'other', label: '其他' }
    ],
    educationOptions: [
      { value: 'high_school_or_below', label: '高中及以下' },
      { value: 'college', label: '大专' },
      { value: 'bachelor', label: '本科' },
      { value: 'master', label: '硕士' },
      { value: 'doctorate_or_above', label: '博士及以上' }
    ],
    experienceOptions: [
      { value: 'bazi_ziwei', label: '八字 / 紫微斗数命理咨询' },
      { value: 'astrology', label: '星座 / 星盘分析' },
      { value: 'tarot', label: '塔罗牌占卜' },
      { value: 'ai_divination', label: '在线 AI 占卜 / 命理工具' },
      { value: 'feng_shui', label: '风水咨询' },
      { value: 'never', label: '从未接触过' },
      { value: 'other', label: '其他' }
    ],
    attitudeOptions: [
      { value: 'strongly_believe', label: '非常相信' },
      { value: 'reference', label: '比较相信，作为参考' },
      { value: 'uncertain', label: '半信半疑' },
      { value: 'curious', label: '不太相信，但感兴趣' },
      { value: 'disbelieve', label: '完全不相信' }
    ],
    depthOptions: [
      { value: 'concise', label: '简洁明了，给核心结论即可' },
      { value: 'balanced', label: '中等深度，有解释和背景' },
      { value: 'deep', label: '深入详细，希望了解完整的命理逻辑' }
    ],
    usageOptions: [
      { value: 'morning_planning', label: '每天早上规划一天' },
      { value: 'evening_review', label: '每天晚上复盘反思' },
      { value: 'when_confused', label: '遇到困惑时查找指引' },
      { value: 'before_decision', label: '做重要决策前参考' },
      { value: 'emotional_support', label: '情绪低落时寻求安慰' },
      { value: 'other', label: '其他' }
    ]
  }
}
