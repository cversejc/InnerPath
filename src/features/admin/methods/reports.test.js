import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import reportsMethods from './reports.js'

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

async function withDocument(callback) {
  const originalDocument = globalThis.document
  globalThis.document = { activeElement: null }
  try {
    await callback()
  } finally {
    if (originalDocument === undefined) delete globalThis.document
    else globalThis.document = originalDocument
  }
}

test('late report list responses do not overwrite the newest filter result', async () => {
  const originalGet = apiClient.get
  const firstReports = deferred()
  apiClient.get = async (url, options) => {
    if (url !== '/admin/reports') throw new Error(`unexpected request: ${url}`)
    if (options.params.search === 'first') return firstReports.promise
    return { data: { total: 1, items: [{ id: 22, title: '最新报告' }] } }
  }
  const context = {
    cleanParams: params => params,
    errorText: error => error.message,
    message: '',
    reportFilters: { search: 'first' },
    reportListRequestId: 0,
    reportPage: 1,
    reportPageSize: 12,
    reports: { total: 0, items: [] },
    reportsLoading: false
  }

  try {
    const firstLoad = reportsMethods.loadReports.call(context)
    context.reportFilters.search = 'latest'
    await reportsMethods.loadReports.call(context)
    firstReports.resolve({ data: { total: 1, items: [{ id: 11, title: '过期报告' }] } })
    await firstLoad
  } finally {
    apiClient.get = originalGet
  }

  assert.deepEqual(context.reports.items, [{ id: 22, title: '最新报告' }])
  assert.equal(context.reportsLoading, false)
  assert.equal(context.message, '')
})

test('late report detail responses cannot replace the selected report', async () => {
  const originalGet = apiClient.get
  const firstReport = deferred()
  apiClient.get = async url => {
    if (url === '/admin/reports/11') return firstReport.promise
    if (url === '/admin/reports/22') return { data: { id: 22, title: '当前报告' } }
    throw new Error(`unexpected request: ${url}`)
  }
  let focused = 0
  const context = {
    drawerTrigger: null,
    focusDrawer() { focused += 1 },
    message: '',
    reportDetail: null,
    reportDetailRequestId: 0,
    errorText: error => error.message
  }

  try {
    await withDocument(async () => {
      const firstLoad = reportsMethods.openReport.call(context, { id: 11 })
      await reportsMethods.openReport.call(context, { id: 22 })
      firstReport.resolve({ data: { id: 11, title: '过期报告' } })
      await firstLoad
    })
  } finally {
    apiClient.get = originalGet
  }

  assert.equal(context.reportDetail.id, 22)
  assert.equal(focused, 1)
})

test('closing the report drawer invalidates its pending detail request', async () => {
  const originalGet = apiClient.get
  const pendingReport = deferred()
  apiClient.get = async () => pendingReport.promise
  let restored = 0
  const context = {
    drawerTrigger: null,
    focusDrawer() {},
    message: '',
    reportDetail: null,
    reportDetailRequestId: 0,
    restoreDrawerFocus() { restored += 1 },
    errorText: error => error.message
  }

  try {
    await withDocument(async () => {
      const pendingLoad = reportsMethods.openReport.call(context, { id: 11 })
      reportsMethods.closeReportDetail.call(context)
      pendingReport.resolve({ data: { id: 11, title: '已关闭的报告' } })
      await pendingLoad
    })
  } finally {
    apiClient.get = originalGet
  }

  assert.equal(context.reportDetail, null)
  assert.equal(restored, 1)
})
