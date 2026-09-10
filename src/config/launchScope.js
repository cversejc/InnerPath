// 当前用户可用范围只包含个人报告书与决策日历。
// 课程、预约和服务页保留在代码中，方便后续恢复，但暂不进入用户流程。
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
