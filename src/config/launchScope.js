// 当前用户可用范围只包含个人报告书与决策日历。
// 暂停的商业页面隔离在 paused-commerce feature 中，默认不进入用户流程。
export const launchScope = Object.freeze({
  reports: true,
  decisionCalendar: true,
  services: false,
  booking: false,
  courses: false
})

export function isLaunchFeatureEnabled(feature) {
  return launchScope[feature] !== false
}
