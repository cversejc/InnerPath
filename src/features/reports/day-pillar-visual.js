const pillarsByTheme = {
  wood: ['戊辰', '己巳', '壬午', '癸未', '庚寅', '辛卯', '戊戌', '己亥', '壬子', '癸丑', '庚申', '辛酉'],
  fire: ['丙寅', '丁卯', '甲戌', '乙亥', '戊子', '己丑', '丙申', '丁酉', '甲辰', '乙巳', '戊午', '己未'],
  earth: ['庚午', '辛未', '戊寅', '己卯', '丙戌', '丁亥', '庚子', '辛丑', '戊申', '己酉', '丙辰', '丁巳'],
  metal: ['甲子', '乙丑', '壬申', '癸酉', '庚辰', '辛巳', '甲午', '乙未', '庚戌', '辛亥', '壬寅', '癸卯'],
  water: ['丙子', '丁丑', '甲申', '乙酉', '壬辰', '癸巳', '丙午', '丁未', '甲寅', '乙卯', '壬戌', '癸亥']
}

const themeByPillar = Object.fromEntries(
  Object.entries(pillarsByTheme).flatMap(([theme, pillars]) => pillars.map(pillar => [pillar, theme]))
)

export function getReportCoverTheme(dayPillar) {
  const normalized = String(dayPillar || '').replace(/\s+/g, '')
  return themeByPillar[normalized] || ''
}
