const AUTH_MODES = ['login', 'register', 'reset', 'invite']

export function resolveAuthMode(queryMode, path) {
  const pathMode = path.includes('/register')
    ? 'register'
    : path.includes('/forgot-password')
      ? 'reset'
      : path.includes('/invite')
        ? 'invite'
        : 'login'
  return AUTH_MODES.includes(queryMode) ? queryMode : pathMode
}

export function authTitle(mode) {
  return mode === 'login'
    ? '欢迎回来'
    : mode === 'invite'
      ? '接受工作邀请'
      : mode === 'reset'
        ? '重设密码'
        : '创建你的账号'
}

export function authSubtitle(mode) {
  return mode === 'invite' ? '设置账号后进入工作台。' : '进入报告书与决策日历。'
}

export function authSubmitLabel(mode) {
  return mode === 'login'
    ? '登录辰鉴'
    : mode === 'invite'
      ? '完成账号设置'
      : mode === 'reset'
        ? '重设并登录'
        : '注册并进入'
}
