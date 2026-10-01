import assert from 'node:assert/strict'
import test from 'node:test'
import {
  authSubmitLabel,
  authSubtitle,
  authTitle,
  resolveAuthMode
} from './presentation.js'

test('auth route query mode takes precedence over the path', () => {
  assert.equal(resolveAuthMode('invite', '/auth/login'), 'invite')
  assert.equal(resolveAuthMode('unknown', '/auth/register'), 'register')
})

test('auth route paths select login, registration, password reset, and invite modes', () => {
  assert.equal(resolveAuthMode(undefined, '/auth/login'), 'login')
  assert.equal(resolveAuthMode(undefined, '/auth/register'), 'register')
  assert.equal(resolveAuthMode(undefined, '/auth/forgot-password'), 'reset')
  assert.equal(resolveAuthMode(undefined, '/auth/invite'), 'invite')
})

test('auth mode presentation keeps titles, subtitles, and submit labels', () => {
  assert.equal(authTitle('login'), '您好，欢迎登录辰鉴')
  assert.equal(authTitle('invite'), '接受工作邀请')
  assert.equal(authTitle('reset'), '找回密码')
  assert.equal(authTitle('register'), '注册')
  assert.equal(authSubtitle('invite'), '设置账号后进入工作台')
  assert.equal(authSubtitle('register'), '验证手机号后创建账号')
  assert.equal(authSubtitle('reset'), '验证手机号后设置新密码')
  assert.equal(authSubtitle('login'), '请使用手机号和密码登录')
  assert.equal(authSubmitLabel('login'), '登录')
  assert.equal(authSubmitLabel('invite'), '完成账号设置')
  assert.equal(authSubmitLabel('reset'), '重置密码')
  assert.equal(authSubmitLabel('register'), '注册')
})
