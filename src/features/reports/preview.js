export function createReportPreview() {
  const energyProfile = {
    type: '敏锐探索型',
    core_traits: '温和、有主见、容易感受到环境',
    description: '你是一个好奇、敏锐、有独立判断，又很容易感受到环境的人。你的天赋在于看见可能、理解人、产生连接。'
  }
  const careerGuidance = {
    suitable_paths: ['研究型工作', '创意型工作', '内容与表达'],
    work_style: '在独立判断与真实协作之间找到自己的节奏，把脑中的想法逐步变成作品。',
    development_suggestions: ['把兴趣收束成一个可以完成的最小版本', '让作品、表达和行动成为你的现实反馈']
  }
  const relationshipPattern = {
    style: '你渴望深度连接，但不想在关系里失去自己。',
    strengths: ['真诚', '理解', '能够给出情绪价值'],
    challenges: ['容易先照顾别人，再想起自己的需要', '边界与表达仍在练习'],
    growth_direction: '既保持自我，也真正打开与世界的连接。'
  }
  const personalGrowth = {
    current_issues: ['表达与创造', '关系边界'],
    action_plan: [
      { area: '一页纸收尾练习', action: '为一个真正重要的方向，完成一个最小版本并记录反馈。', timeline: '本周' },
      { area: '外部锚点练习', action: '为持续的行动安排一个固定时间和一个可以看见进度的人。', timeline: '本月' }
    ],
    resources: ['记录', '作品', '真实反馈']
  }
  const summary = '你不需要先成为一个“好人”，你需要的是一个完整的人。让真实的你被看见，也让你的心灵知道路。'

  return {
    id: 'preview',
    title: '辰鉴·人生说明书',
    basic_info: {
      name: '青鸟',
      report_date: '2026-10-03'
    },
    energy_profile: energyProfile,
    career_guidance: careerGuidance,
    relationship_pattern: relationshipPattern,
    personal_growth: personalGrowth,
    summary,
    structured_sections: {
      energy: {
        title: '能量特质',
        type: 'energy',
        content: energyProfile.description,
        subsections: [{ title: '核心特质', content: energyProfile.core_traits }]
      },
      topics: [
        {
          title: '关系模式',
          type: 'topic',
          subsections: [
            { title: '关系风格', content: relationshipPattern.style },
            { title: '优势', items: relationshipPattern.strengths },
            { title: '挑战', items: relationshipPattern.challenges },
            { title: '成长方向', content: relationshipPattern.growth_direction }
          ]
        },
        {
          title: '方向与节奏',
          type: 'topic',
          subsections: [
            { title: '适合方向', items: careerGuidance.suitable_paths },
            { title: '工作风格', content: careerGuidance.work_style },
            { title: '发展建议', items: careerGuidance.development_suggestions }
          ]
        },
        {
          title: '成长行动',
          type: 'topic',
          subsections: [
            { title: '关注议题', items: personalGrowth.current_issues },
            { title: '行动方案', items: personalGrowth.action_plan },
            { title: '支持资源', items: personalGrowth.resources }
          ]
        }
      ],
      summary: { title: '总结与寄语', type: 'summary', content: summary }
    }
  }
}
