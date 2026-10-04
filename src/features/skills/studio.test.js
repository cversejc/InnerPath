import test from 'node:test'
import assert from 'node:assert/strict'
import { formatTrace, parseSpecification, sampleInput } from './studio.js'

test('specification editor reports malformed and non-object JSON', () => {
  assert.match(parseSpecification('{').error, /JSON 格式错误/)
  assert.match(parseSpecification('[]').error, /JSON 对象/)
  assert.deepEqual(parseSpecification('{"identity":{}}'), {
    value: { identity: {} },
    error: ''
  })
})

test('trace view omits absent fields and includes provider metadata', () => {
  assert.deepEqual(formatTrace({ provider: 'deepseek', latency_ms: 23 }), [
    ['模型服务', 'deepseek'],
    ['耗时', '23 ms']
  ])
})

test('debug sample contains profile and application context', () => {
  const sample = sampleInput()
  assert.equal(sample.profile.birth_year, 1992)
  assert.deepEqual(sample.context.focus_topics, ['career', 'growth'])
})
