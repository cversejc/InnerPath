import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import feedbackMethods from './feedback.js'

test('service quality summary loads the requested period and keeps the server range', async () => {
  const originalGet = apiClient.get
  const calls = []
  apiClient.get = async (url, options) => {
    calls.push({ url, params: options.params })
    return { data: { period_days: 90, totals: { feedback_count: 8 }, by_service: [] } }
  }
  const context = {
    serviceQualitySummary: null,
    serviceQualityPeriodDays: 30,
    serviceQualityLoading: false,
    serviceQualityError: '',
    loadServiceQualitySummary: feedbackMethods.loadServiceQualitySummary,
    errorText: error => error.message
  }

  try {
    await feedbackMethods.changeServiceQualityPeriod.call(context, 90)
  } finally {
    apiClient.get = originalGet
  }

  assert.deepEqual(calls, [{ url: '/admin/service-feedback/summary', params: { period_days: 90 } }])
  assert.equal(context.serviceQualityPeriodDays, 90)
  assert.equal(context.serviceQualitySummary.totals.feedback_count, 8)
  assert.equal(context.serviceQualityLoading, false)
})

test('failed service quality refresh retains the last successful data and period', async () => {
  const originalGet = apiClient.get
  apiClient.get = async () => { throw new Error('summary unavailable') }
  const previous = { totals: { feedback_count: 3 } }
  const context = {
    serviceQualitySummary: previous,
    serviceQualityPeriodDays: 30,
    serviceQualityLoading: false,
    serviceQualityError: '',
    loadServiceQualitySummary: feedbackMethods.loadServiceQualitySummary,
    errorText: error => error.message
  }

  try {
    await feedbackMethods.changeServiceQualityPeriod.call(context, 7)
  } finally {
    apiClient.get = originalGet
  }

  assert.equal(context.serviceQualitySummary, previous)
  assert.equal(context.serviceQualityPeriodDays, 30)
  assert.equal(context.serviceQualityError, 'summary unavailable')
  assert.equal(context.serviceQualityLoading, false)
})
