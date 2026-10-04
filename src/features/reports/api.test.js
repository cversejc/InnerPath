import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../utils/apiClient.js'
import {
  deleteReport,
  getLatestReportContext,
  getReportDetail,
  getReportTask,
  getUserReports
} from './api.js'

test('user report endpoints stay within the reports API module', async () => {
  const originalGet = apiClient.get
  const originalDelete = apiClient.delete
  const requests = []
  apiClient.get = async (url, config) => {
    requests.push(['get', url, config])
    return { data: { url } }
  }
  apiClient.delete = async url => {
    requests.push(['delete', url])
    return { data: { deleted: true } }
  }

  try {
    assert.deepEqual(await getReportTask('legacy-task-21'), { url: '/reports/tasks/legacy-task-21' })
    assert.deepEqual(await getReportDetail(42), { url: '/reports/42' })
    assert.deepEqual(await getUserReports(2, 5), { url: '/reports' })
    assert.deepEqual(await getLatestReportContext(), { url: '/reports/latest/context' })
    assert.deepEqual(await deleteReport(42), { deleted: true })
    assert.deepEqual(requests, [
      ['get', '/reports/tasks/legacy-task-21', undefined],
      ['get', '/reports/42', undefined],
      ['get', '/reports', { params: { page: 2, size: 5 } }],
      ['get', '/reports/latest/context', undefined],
      ['delete', '/reports/42']
    ])
  } finally {
    apiClient.get = originalGet
    apiClient.delete = originalDelete
  }
})
