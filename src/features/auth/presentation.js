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
    ? '您好，欢迎登录辰鉴'
    : mode === 'invite'
      ? '接受工作邀请'
      : mode === 'reset'
        ? '找回密码'
        : '注册'
}

export function authSubtitle(mode) {
  if (mode === 'invite') return '设置账号后进入工作台'
  if (mode === 'register') return '验证手机号后创建账号'
  if (mode === 'reset') return '验证手机号后设置新密码'
  return '请使用手机号和密码登录'
}

export function authSubmitLabel(mode) {
  return mode === 'login'
    ? '登录'
    : mode === 'invite'
      ? '完成账号设置'
      : mode === 'reset'
        ? '重置密码'
        : '注册'
}
