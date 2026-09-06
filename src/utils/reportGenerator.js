// AI报告生成模块
// 将传统命理概念转化为现代心理学语言

/**
 * 能量类型映射
 * 将五行特质转化为心理学人格类型
 */
export const energyTypeMapping = {
  wood: {
    name: '生长驱动型',
    traits: ['创新求变', '积极进取', '富有创造力', '追求成长'],
    description: '你的能量倾向于向外扩展和生长，喜欢探索新事物，具有强烈的成长动力。',
    strengths: ['创新思维', '适应能力强', '富有活力', '目标导向'],
    challenges: ['容易急躁', '缺乏耐心', '过度扩张', '难以坚持'],
    careerPath: ['创业者', '产品经理', '创意设计', '市场开拓'],
    relationshipStyle: '在关系中追求新鲜感和成长空间，需要伴侣理解你的独立性。'
  },
  fire: {
    name: '表达驱动型',
    traits: ['热情洋溢', '善于表达', '富有感染力', '追求认可'],
    description: '你的能量倾向于向外散发和表达，喜欢与人互动，具有强烈的表现欲。',
    strengths: ['沟通能力强', '富有魅力', '乐观积极', '善于激励他人'],
    challenges: ['情绪波动大', '过度消耗', '需要外界认可', '难以独处'],
    careerPath: ['演讲者', '销售', '媒体工作', '公关传播'],
    relationshipStyle: '在关系中需要被看见和认可，渴望热烈的情感表达。'
  },
  earth: {
    name: '稳定承载型',
    traits: ['踏实稳重', '包容接纳', '注重安全', '追求稳定'],
    description: '你的能量倾向于稳定和承载，喜欢建立秩序，具有强烈的责任感。',
    strengths: ['可靠稳定', '善于整合', '耐心细致', '责任心强'],
    challenges: ['过度保守', '难以改变', '容易焦虑', '过度负责'],
    careerPath: ['管理者', '财务会计', '人力资源', '项目协调'],
    relationshipStyle: '在关系中追求稳定和安全感，愿意为关系付出和承担。'
  },
  metal: {
    name: '秩序驱动型',
    traits: ['理性客观', '追求完美', '注重规则', '善于分析'],
    description: '你的能量倾向于收敛和精炼，喜欢建立标准，具有强烈的原则性。',
    strengths: ['逻辑清晰', '执行力强', '追求卓越', '自律性高'],
    challenges: ['过度严苛', '难以变通', '情感压抑', '完美主义'],
    careerPath: ['技术专家', '质量管理', '法律顾问', '研究分析'],
    relationshipStyle: '在关系中追求清晰的界限和规则，需要学习情感表达。'
  },
  water: {
    name: '智慧流动型',
    traits: ['深思熟虑', '善于观察', '灵活变通', '追求智慧'],
    description: '你的能量倾向于向内流动和沉淀，喜欢深度思考，具有强烈的洞察力。',
    strengths: ['洞察力强', '适应性好', '智慧深邃', '善于策略'],
    challenges: ['过度思虑', '缺乏行动', '情绪内敛', '难以信任'],
    careerPath: ['咨询顾问', '心理咨询', '战略规划', '学术研究'],
    relationshipStyle: '在关系中需要深度连接和理解，倾向于观察和等待。'
  }
}

/**
 * 十神心理动力映射
 * 将十神系统转化为心理动力模式
 */
export const tenGodsMapping = {
  bijian: {
    name: '自我认同驱动',
    psychologicalPattern: '强烈的自我意识和独立性',
    behavior: '倾向于依靠自己，不轻易求助他人',
    relationship: '在关系中保持独立，可能显得疏离',
    growth: '学习与他人合作，接纳不同观点'
  },
  jiecai: {
    name: '竞争驱动',
    psychologicalPattern: '强烈的竞争意识和进取心',
    behavior: '喜欢挑战和竞争，追求胜利',
    relationship: '在关系中可能过于强势，需要学习妥协',
    growth: '平衡竞争与合作，培养同理心'
  },
  shishan: {
    name: '表达驱动',
    psychologicalPattern: '强烈的表达欲和创造力',
    behavior: '喜欢展现自己，追求独特性',
    relationship: '在关系中需要被看见和认可',
    growth: '平衡表达与倾听，关注他人需求'
  },
  shangquan: {
    name: '成就驱动',
    psychologicalPattern: '强烈的成就动机和目标导向',
    behavior: '追求成功和财富，注重实际结果',
    relationship: '在关系中可能过于功利，需要学习情感投入',
    growth: '平衡物质与精神，培养内在价值感'
  },
  pianquan: {
    name: '灵活驱动',
    psychologicalPattern: '灵活变通和机会主义',
    behavior: '善于抓住机会，适应能力强',
    relationship: '在关系中可能缺乏稳定性',
    growth: '建立长期承诺，培养责任感'
  },
  zhengguan: {
    name: '责任驱动',
    psychologicalPattern: '强烈的责任感和规则意识',
    behavior: '遵守规则，追求正统和认可',
    relationship: '在关系中可能过于严肃，需要学习放松',
    growth: '平衡责任与自由，接纳不完美'
  },
  qisha: {
    name: '突破驱动',
    psychologicalPattern: '强烈的突破欲和反叛性',
    behavior: '挑战权威，追求自由和改变',
    relationship: '在关系中可能过于强硬，需要学习柔软',
    growth: '平衡突破与稳定，培养耐心'
  },
  zhengyin: {
    name: '学习驱动',
    psychologicalPattern: '强烈的学习欲和求知欲',
    behavior: '喜欢学习和思考，追求知识',
    relationship: '在关系中可能过于理性，需要学习感性',
    growth: '平衡理论与实践，关注现实需求'
  },
  pianyin: {
    name: '独特驱动',
    psychologicalPattern: '强烈的独特性和非主流倾向',
    behavior: '追求与众不同，喜欢小众文化',
    relationship: '在关系中可能显得孤僻，需要学习融入',
    growth: '平衡独特与融入，建立归属感'
  },
  zhengcai: {
    name: '稳定驱动',
    psychologicalPattern: '强烈的安全感需求和稳定性',
    behavior: '追求稳定和可控，注重积累',
    relationship: '在关系中追求长期稳定',
    growth: '平衡稳定与变化，接纳不确定性'
  }
}

/**
 * 生成辰鉴人生说明书
 */
export function generateEnergyReport(userData) {
  const { birthYear, birthMonth, birthDay, birthHour, selectedTopics } = userData

  // 简化的五行分析（实际应用中需要完整的八字排盘算法）
  const dominantElement = analyzeDominantElement(birthYear, birthMonth, birthDay)
  const energyType = energyTypeMapping[dominantElement]

  // 生成报告
  const report = {
    basicInfo: {
      name: userData.name,
      birthDate: `${birthYear}-${birthMonth}-${birthDay}`,
      reportDate: new Date().toISOString().split('T')[0]
    },
    energyProfile: {
      type: energyType.name,
      description: energyType.description,
      coreTraits: energyType.traits.join('、'),
      strengths: energyType.strengths,
      challenges: energyType.challenges
    },
    careerGuidance: {
      suitablePaths: energyType.careerPath,
      workStyle: getWorkStyle(dominantElement),
      developmentSuggestions: getCareerSuggestions(dominantElement, selectedTopics)
    },
    relationshipPattern: {
      style: energyType.relationshipStyle,
      strengths: getRelationshipStrengths(dominantElement),
      challenges: getRelationshipChallenges(dominantElement),
      growthDirection: getRelationshipGrowth(dominantElement)
    },
    personalGrowth: {
      currentIssues: analyzeCurrentIssues(selectedTopics),
      actionPlan: generateActionPlan(dominantElement, selectedTopics),
      resources: getGrowthResources(selectedTopics)
    },
    summary: generateSummary(energyType, selectedTopics)
  }

  return report
}

/**
 * 分析主导五行（简化版）
 */
function analyzeDominantElement(year, month, day) {
  // 这是一个简化的示例，实际应用需要完整的八字排盘算法
  const sum = (year + month + day) % 5
  const elements = ['wood', 'fire', 'earth', 'metal', 'water']
  return elements[sum]
}

/**
 * 获取工作风格
 */
function getWorkStyle(element) {
  const styles = {
    wood: '你适合需要创新和开拓的工作环境，喜欢自主性强的工作方式。',
    fire: '你适合需要沟通和表达的工作环境，喜欢团队协作和互动。',
    earth: '你适合需要稳定和协调的工作环境，喜欢有明确流程的工作方式。',
    metal: '你适合需要专业和精准的工作环境，喜欢有标准和规范的工作方式。',
    water: '你适合需要思考和策略的工作环境，喜欢灵活和自由的工作方式。'
  }
  return styles[element]
}

/**
 * 获取职业建议
 */
function getCareerSuggestions(element, topics) {
  const suggestions = []

  if (topics.includes('career')) {
    suggestions.push('建议先进行职业兴趣测评，明确自己的天赋优势领域')
    suggestions.push('寻找与你能量特质匹配的工作环境和团队文化')
    suggestions.push('制定3-5年的职业发展规划，设定阶段性目标')
  }

  return suggestions.length > 0 ? suggestions : [
    '持续学习和提升专业技能',
    '建立个人品牌和影响力',
    '拓展人际网络和资源'
  ]
}

/**
 * 获取关系优势
 */
function getRelationshipStrengths(element) {
  const strengths = {
    wood: ['积极主动', '富有活力', '能带动对方成长'],
    fire: ['热情温暖', '善于表达', '能营造愉快氛围'],
    earth: ['稳定可靠', '包容接纳', '能提供安全感'],
    metal: ['忠诚专一', '有原则', '能提供清晰边界'],
    water: ['深度理解', '善于倾听', '能提供情感支持']
  }
  return strengths[element]
}

/**
 * 获取关系挑战
 */
function getRelationshipChallenges(element) {
  const challenges = {
    wood: ['可能过于独立', '缺乏耐心倾听', '容易忽视对方感受'],
    fire: ['可能过于热烈', '情绪波动大', '需要过多关注'],
    earth: ['可能过度付出', '难以表达需求', '容易焦虑'],
    metal: ['可能过于严格', '情感表达困难', '难以妥协'],
    water: ['可能过于内敛', '缺乏主动', '难以建立信任']
  }
  return challenges[element]
}

/**
 * 获取关系成长方向
 */
function getRelationshipGrowth(element) {
  const growth = {
    wood: '学习放慢节奏，给予对方更多耐心和关注',
    fire: '学习情绪管理，建立稳定的情感连接',
    earth: '学习表达需求，建立健康的界限',
    metal: '学习情感表达，接纳不完美和变化',
    water: '学习主动表达，建立信任和安全感'
  }
  return growth[element]
}

/**
 * 分析当前议题
 */
function analyzeCurrentIssues(topics) {
  const issueMap = {
    career: '你当前在职业发展上可能面临选择或瓶颈，需要重新审视自己的优势和方向。',
    relationship: '你当前在亲密关系上可能面临模式重复或沟通困难，需要理解自己的关系模式。',
    family: '你当前在家庭议题上可能面临原生家庭影响或代际模式，需要建立新的互动方式。',
    self: '你当前在自我价值上可能面临认同困惑或意义缺失，需要重建内在稳定感。',
    growth: '你当前在个人成长上可能面临突破瓶颈或方向迷茫，需要找到适合的成长路径。',
    stress: '你当前在压力管理上可能面临情绪困扰或能量耗竭，需要建立应对策略。'
  }

  return topics.map(topic => issueMap[topic]).filter(Boolean)
}

/**
 * 生成行动方案
 */
function generateActionPlan(element, topics) {
  const plans = []

  // 基于能量类型的通用建议
  plans.push({
    area: '能量管理',
    action: '每天预留30分钟独处时间，进行自我觉察和能量恢复',
    timeline: '立即开始，持续21天养成习惯'
  })

  // 基于选择议题的具体建议
  if (topics.includes('career')) {
    plans.push({
      area: '职业发展',
      action: '列出你的核心优势和兴趣，寻找两者交集的职业方向',
      timeline: '本周内完成，并与信任的人讨论'
    })
  }

  if (topics.includes('relationship')) {
    plans.push({
      area: '关系改善',
      action: '观察并记录你在关系中的重复模式，识别触发点',
      timeline: '未来两周，每天记录一次'
    })
  }

  return plans
}

/**
 * 获取成长资源
 */
function getGrowthResources(topics) {
  return [
    '推荐书籍：《原生家庭》《亲密关系》《活出生命的意义》',
    '推荐路径：辰鉴《共鉴计划》',
    '推荐实践：决策日志、日记书写、定期复盘'
  ]
}

/**
 * 生成总结
 */
function generateSummary(energyType, topics) {
  return `你的个人属性呈现出${energyType.traits.slice(0, 2).join('、')}的特质。当前你最关注的是${topics.length > 0 ? '现实处境' : '自我探索'}相关议题。辰鉴不替你预测未来，而是邀请你先看见自己的能量通路，再在合适的时机做出属于你的选择。`
}

export default {
  generateEnergyReport,
  energyTypeMapping,
  tenGodsMapping
}
