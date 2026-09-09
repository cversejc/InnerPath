<template>
  <div class="admin-shell">
    <BrandNav />
    <main class="admin-main">
      <header class="admin-hero">
        <div>
          <p class="section-kicker">CHENJIAN / OPERATIONS ROOM</p>
          <h1>辰鉴运营中枢</h1>
          <p class="hero-caption">把每一个用户、时机与行动，整理成可以被照看的全局。</p>
        </div>
        <div class="hero-actions">
          <span class="sync-state"><i :class="{ live: dashboardLoading }"></i>{{ dashboardLoading ? '正在同步' : lastUpdated ? `更新于 ${lastUpdated}` : '等待同步' }}</span>
          <button class="secondary-button compact-button" type="button" :disabled="activeLoading" @click="refreshActive">↻ 刷新</button>
        </div>
      </header>

      <nav class="admin-tabs" aria-label="管理后台导航">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          :class="['admin-tab', { active: activeTab === tab.id }]"
          @click="switchTab(tab.id)">
          <span class="tab-index">{{ tab.index }}</span>
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <div v-if="message" class="console-message" role="status">
        <span>{{ message }}</span>
        <button type="button" aria-label="关闭提示" @click="message = ''">×</button>
      </div>

      <section v-if="activeTab === 'overview'" class="dashboard-view">
        <div class="dashboard-toolbar">
          <div>
            <p class="eyebrow">GLOBAL SIGNALS</p>
            <h2>全局数据</h2>
            <p v-if="dashboard">{{ formatDate(dashboard.start_date) }} — {{ formatDate(dashboard.end_date) }} · {{ dashboard.timezone }}</p>
          </div>
          <div class="toolbar-controls">
            <div class="range-switch" aria-label="数据范围">
              <button v-for="range in dashboardRanges" :key="range.id" type="button" :class="{ active: dashboardRange === range.id }" @click="changeDashboardRange(range.id)">{{ range.label }}</button>
            </div>
            <label class="auto-refresh"><input v-model="autoRefresh" type="checkbox" @change="syncAutoRefresh"> <span>60 秒自动刷新</span></label>
          </div>
        </div>

        <div v-if="dashboardLoading && !dashboard" class="dashboard-skeleton">
          <div v-for="index in 6" :key="index" class="skeleton-block"></div>
        </div>

        <template v-else-if="dashboard">
          <div class="metric-grid">
            <article v-for="metric in metricCards" :key="metric.key" class="metric-card" :class="`metric-${metric.tone}`">
              <div class="metric-top"><span>{{ metric.label }}</span><b>{{ metric.mark }}</b></div>
              <strong>{{ metric.value }}</strong>
              <small>{{ metric.caption }}</small>
            </article>
          </div>

          <div class="dashboard-grid">
            <article class="dashboard-panel trend-panel">
              <div class="panel-heading"><div><p class="eyebrow">RHYTHM / {{ dashboardRange.toUpperCase() }}</p><h3>业务流入趋势</h3></div><span class="panel-note">按上海时区聚合</span></div>
              <div class="trend-legend"><span v-for="series in trendSeries" :key="series.key"><i :style="{ background: series.color }"></i>{{ series.label }}</span></div>
              <div class="trend-chart" aria-label="业务流入趋势图">
                <svg viewBox="0 0 760 250" role="img" aria-labelledby="trend-title">
                  <title id="trend-title">用户、报告、预约和行动记录趋势</title>
                  <line v-for="line in chartGridLines" :key="line" x1="28" :x2="736" :y1="line" :y2="line" class="chart-grid-line" />
                  <polyline v-for="series in trendSeries" :key="series.key" :points="series.points" :stroke="series.color" class="trend-line" />
                  <g v-for="tick in trendTicks" :key="tick.index">
                    <line :x1="tick.x" :x2="tick.x" y1="214" y2="220" class="chart-tick" />
                    <text :x="tick.x" y="241" text-anchor="middle" class="chart-label">{{ tick.label }}</text>
                  </g>
                </svg>
              </div>
            </article>

            <article class="dashboard-panel alert-panel">
              <div class="panel-heading"><div><p class="eyebrow">ATTENTION REQUIRED</p><h3>待处理事项</h3></div><span class="alert-count">{{ dashboard.alerts.length }}</span></div>
              <div v-if="dashboard.alerts.length" class="alert-list">
                <button v-for="alert in dashboard.alerts" :key="alert.key" type="button" class="alert-item" @click="goFromAlert(alert)">
                  <span :class="['alert-mark', `alert-${alert.level}`]"></span><span><strong>{{ alert.label }}</strong><small>{{ alert.count }} 项需要关注</small></span><b>→</b>
                </button>
              </div>
              <div v-else class="quiet-state"><span>✦</span><p>目前没有需要立即处理的事项。</p></div>
            </article>

            <article class="dashboard-panel distribution-panel">
              <div class="panel-heading"><div><p class="eyebrow">COMPOSITION</p><h3>结构分布</h3></div></div>
              <div class="distribution-columns">
                <div v-for="group in distributionGroups" :key="group.key" class="distribution-group">
                  <div class="distribution-title"><span>{{ group.label }}</span><small>{{ distributionTotal(group.items) }}</small></div>
                  <div v-for="item in group.items" :key="item.key" class="distribution-row">
                    <div><span>{{ item.label }}</span><b>{{ item.value }}</b></div><span class="distribution-track"><i :style="{ width: `${distributionWidth(item, group.items)}%` }"></i></span>
                  </div>
                </div>
              </div>
            </article>

            <article class="dashboard-panel activity-panel">
              <div class="panel-heading"><div><p class="eyebrow">TRACE / LATEST 8</p><h3>最近活动</h3></div><button type="button" class="panel-link" @click="switchTab('logs')">查看日志 →</button></div>
              <div v-if="dashboard.recent_activity.length" class="activity-list">
                <div v-for="activity in dashboard.recent_activity" :key="activity.id" class="activity-item"><span class="activity-dot"></span><div><strong>{{ actionLabel(activity.action) }}</strong><p>{{ activity.target_user_name || activity.actor_name || '系统' }} · {{ resourceLabel(activity.resource_type) }}</p></div><time>{{ formatDateTime(activity.created_at) }}</time></div>
              </div>
              <div v-else class="quiet-state"><span>⌁</span><p>还没有可展示的活动记录。</p></div>
            </article>

            <article class="dashboard-panel course-panel">
              <div class="panel-heading"><div><p class="eyebrow">LEARNING / COURSE HEALTH</p><h3>课程学习概况</h3></div><span>按课程</span></div>
              <div v-if="dashboard.course_stats?.length" class="course-stats-list">
                <div v-for="course in dashboard.course_stats" :key="course.course_id" class="course-stat-row">
                  <div><strong>{{ course.title }}</strong><small>{{ course.enrolled_count }} 人参与 · {{ course.active_count }} 人学习中</small></div>
                  <div class="course-stat-numbers"><b>{{ course.completion_rate }}%</b><span>完成</span><small>均值 {{ course.average_progress }}%</small></div>
                </div>
              </div>
              <div v-else class="quiet-state"><span>⌁</span><p>暂无线课程参与数据。</p></div>
            </article>
          </div>
        </template>
      </section>

      <section v-else-if="activeTab === 'users'" class="content-view">
        <div class="view-heading"><div><p class="eyebrow">PEOPLE / DIRECTORY</p><h2>用户运营</h2><p>从账户状态到成长轨迹，统一查看和维护。</p></div><button class="secondary-button" type="button" @click="exportResource('users')">↓ 导出用户 CSV</button></div>
        <div class="filter-bar">
          <input v-model.trim="userFilters.search" placeholder="搜索姓名或手机号" @keyup.enter="searchUsers">
          <select v-model="userFilters.role"><option value="">全部角色</option><option value="user">用户</option><option value="consultant">咨询师</option><option value="admin">管理员</option></select>
          <select v-model="userFilters.is_active"><option value="">全部状态</option><option :value="true">正常</option><option :value="false">已停用</option></select>
          <label class="date-filter"><span>注册自</span><input v-model="userFilters.created_from" type="date"></label>
          <label class="date-filter"><span>至</span><input v-model="userFilters.created_to" type="date"></label>
          <button class="primary-button compact-button" type="button" @click="searchUsers">查询</button>
          <button class="filter-reset" type="button" @click="resetUserFilters">清空</button>
        </div>
         <div v-if="usersLoading" class="list-loading" aria-label="正在加载用户"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel">
          <div class="table-meta"><span>共 {{ users.total }} 个账号</span><span>管理员可见完整运营资料</span></div>
          <div class="admin-table-wrap">
            <table class="admin-table">
              <thead><tr><th>用户</th><th>角色</th><th>运营概览</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="user in users.items" :key="user.id">
                  <td><div class="person-cell"><span class="avatar-mark">{{ user.name?.slice(0, 1) || '人' }}</span><span><strong>{{ user.name }}</strong><small>#{{ user.id }} · {{ user.phone }}</small></span></div></td>
                  <td><select :value="user.role" @change="changeRole(user, $event.target.value)"><option value="user">用户</option><option value="consultant">咨询师</option><option value="admin">管理员</option></select></td>
                  <td><div class="mini-stats"><span>报 {{ user.report_count }}</span><span>约 {{ user.booking_count }}</span><span>历 {{ user.calendar_count }}</span></div></td>
                  <td><span :class="['status-badge', user.is_active ? 'success' : 'muted']">{{ user.is_active ? '正常' : '已停用' }}</span></td>
                  <td class="muted-text">{{ formatDateTime(user.last_login_at) }}</td>
                  <td><div class="row-actions"><button type="button" @click="openUserDetail(user)">详情</button><button type="button" @click="openCalendarForUser(user)">日历</button><button type="button" @click="resetUserPassword(user)">{{ user.is_active ? '重置密码' : '启用' }}</button><button v-if="user.is_active" type="button" class="danger-action" @click="toggleUser(user)">停用</button><button v-else type="button" @click="toggleUser(user)">启用</button></div></td>
                </tr>
                <tr v-if="!users.items.length"><td colspan="6" class="empty-cell">没有找到符合条件的用户。</td></tr>
              </tbody>
            </table>
          </div>
          <div class="pagination"><span>第 {{ userPage }} / {{ pageCount(users.total, userPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="userPage <= 1" @click="changeUserPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="userPage >= pageCount(users.total, userPageSize)" @click="changeUserPage(1)">下一页</button></div></div>
        </div>
      </section>

      <section v-else-if="activeTab === 'bookings'" class="content-view">
        <div class="view-heading"><div><p class="eyebrow">SERVICE / APPOINTMENTS</p><h2>预约运营</h2><p>从待确认到完成服务，掌握每一次交付节点。</p></div><button class="secondary-button" type="button" @click="exportResource('bookings')">↓ 导出预约 CSV</button></div>
        <div class="filter-bar">
          <input v-model.trim="bookingFilters.search" placeholder="搜索用户、手机号或服务" @keyup.enter="searchBookings">
          <select v-model="bookingFilters.status"><option value="">全部状态</option><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select>
          <select v-model="bookingFilters.consultant_id"><option value="">全部咨询师</option><option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select>
          <label class="date-filter"><span>创建自</span><input v-model="bookingFilters.date_from" type="date"></label><label class="date-filter"><span>至</span><input v-model="bookingFilters.date_to" type="date"></label>
          <button class="primary-button compact-button" type="button" @click="searchBookings">查询</button>
          <button class="filter-reset" type="button" @click="resetBookingFilters">清空</button>
        </div>
         <div v-if="bookingsLoading" class="list-loading" aria-label="正在加载预约"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel">
          <div class="table-meta"><span>共 {{ bookings.total }} 条预约</span><span>点击行查看会议与沟通资料</span></div>
          <div class="admin-table-wrap"><table class="admin-table booking-table"><thead><tr><th>用户</th><th>服务</th><th>期望时间</th><th>状态</th><th>咨询师</th><th>创建时间</th><th>操作</th></tr></thead><tbody>
            <tr v-for="booking in bookings.items" :key="booking.id" @click="openBookingDetail(booking)"><td><strong>{{ booking.user_name || `用户 #${booking.user_id}` }}</strong><small>{{ booking.user_phone || booking.contact_phone }}</small></td><td>{{ booking.service_name }}<small>{{ booking.service_price ? `¥${booking.service_price}` : '—' }}</small></td><td>{{ booking.confirmed_date || booking.preferred_time }}<small v-if="booking.confirmed_time">{{ booking.confirmed_time }}</small></td><td><span :class="['status-badge', `booking-${booking.status}`]">{{ statusText(booking.status) }}</span></td><td>{{ booking.consultant_name || '未分配' }}</td><td class="muted-text">{{ formatDateTime(booking.created_at) }}</td><td><button type="button" class="row-open" @click.stop="openBookingDetail(booking)">查看 →</button></td></tr>
            <tr v-if="!bookings.items.length"><td colspan="7" class="empty-cell">暂无预约记录。</td></tr>
          </tbody></table></div>
          <div class="pagination"><span>第 {{ bookingPage }} / {{ pageCount(bookings.total, bookingPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="bookingPage <= 1" @click="changeBookingPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="bookingPage >= pageCount(bookings.total, bookingPageSize)" @click="changeBookingPage(1)">下一页</button></div></div>
        </div>
      </section>

      <section v-else-if="activeTab === 'calendar'" class="content-view calendar-view">
        <div class="view-heading"><div><p class="eyebrow">PERSONAL TIMEZONE / EDITOR</p><h2>用户日历</h2><p>结构化维护每日节奏，已发布内容通过新版本上线。</p></div><button class="secondary-button" type="button" @click="toggleImportPanel">{{ showCalendarImport ? '收起 JSON 导入' : '批量 JSON 导入' }}</button></div>
        <div v-if="showCalendarImport" class="import-panel"><div><strong>批量导入日历</strong><p>格式支持 `{ title, entries }` 或直接传入条目数组；导入后默认为草稿。</p></div><textarea v-model="calendarImportJson" rows="4" placeholder='{"title":"2026 秋季行动日历","entries":[{"entry_date":"2026-09-07","tone":"yellow","keyword":"观察","summary":"先理清信息","suitable":["整理计划"],"unsuitable":["仓促拍板"]}]}'></textarea><div class="action-row"><button class="primary-button compact-button" type="button" :disabled="calendarSaving" @click="importCalendarJson">导入为草稿</button></div></div>
        <div class="calendar-admin-grid">
          <aside class="user-directory panel-surface"><div class="panel-heading"><div><p class="eyebrow">SELECT USER</p><h3>选择用户</h3></div><span>{{ calendarUsers.length }}</span></div><div class="directory-search"><input v-model.trim="calendarUserSearch" placeholder="搜索用户" @keyup.enter="loadCalendarUsers"><button type="button" @click="loadCalendarUsers">⌕</button></div><div class="directory-list"><button v-for="user in calendarUsers" :key="user.id" type="button" :class="{ selected: selectedCalendarUser?.id === user.id }" @click="selectCalendarUser(user)"><span class="avatar-mark small">{{ user.name?.slice(0, 1) || '人' }}</span><span><strong>{{ user.name }}</strong><small>#{{ user.id }} · {{ user.phone }}</small></span><b>›</b></button><p v-if="!calendarUsers.length" class="empty-cell">请搜索或暂无用户。</p></div></aside>
          <div class="calendar-editor panel-surface"><div class="panel-heading"><div><p class="eyebrow">CALENDAR VERSIONS</p><h3>{{ selectedCalendarUser ? `${selectedCalendarUser.name} 的日历` : '先选择一个用户' }}</h3></div><button v-if="selectedCalendarUser" class="primary-button compact-button" type="button" @click="startNewCalendar">＋ 新建草稿</button></div>
            <div v-if="calendarLoading" class="list-loading" aria-label="正在加载日历"><i v-for="index in 4" :key="index"></i></div><div v-else-if="selectedCalendarUser" class="calendar-list"><article v-for="calendar in calendars" :key="calendar.id" class="calendar-card" :class="{ selected: calendarForm.id === calendar.id }"><div class="calendar-card-top"><div><strong>{{ calendar.title }}</strong><small>v{{ calendar.version_number }} · {{ calendar.entries?.length || 0 }} 天 · 更新于 {{ formatDate(calendar.updated_at) }}</small></div><span :class="['status-badge', `calendar-${calendar.status}`]">{{ calendarStatusText(calendar.status) }}</span></div><div class="calendar-card-preview"><span v-for="entry in (calendar.entries || []).slice(0, 4)" :key="entry.id">{{ formatDate(entry.entry_date) }} · {{ entry.keyword || entry.status_label || '未命名' }}</span></div><div class="row-actions"><button type="button" @click="prepareCalendarEdit(calendar)">{{ calendar.status === 'draft' ? '编辑' : '创建编辑版本' }}</button><button type="button" @click="exportCalendarJson(calendar)">JSON</button><button v-if="calendar.status === 'draft'" type="button" @click="publishCalendar(calendar)">发布</button><button v-if="calendar.status === 'published'" type="button" class="danger-action" @click="archiveCalendar(calendar)">归档</button></div></article><p v-if="!calendars.length" class="empty-cell">暂无日历，可以从右上角创建草稿。</p></div>
            <form v-if="calendarForm.visible" class="calendar-editor-form" @submit.prevent="saveCalendar"><div class="editor-banner"><span>{{ calendarForm.id ? `编辑 v${calendarForm.version_number}` : '新建草稿' }}</span><span v-if="calendarForm.status">{{ calendarStatusText(calendarForm.status) }}</span></div><div class="form-grid two"><label>日历标题<input v-model.trim="calendarForm.title" required maxlength="150"></label><label>开始日期<input v-model="calendarForm.start_date" type="date"></label><label>结束日期<input v-model="calendarForm.end_date" type="date"></label></div><div class="entry-toolbar"><div><strong>每日条目</strong><small>{{ calendarForm.entries.length }} 个日期 · 日期不可重复</small></div><button class="secondary-button compact-button" type="button" @click="addCalendarEntry">＋ 添加日期</button></div><div class="entry-list"><article v-for="(entry, index) in calendarForm.entries" :key="entry._key" class="entry-editor"><div class="entry-editor-head"><span>DAY {{ String(index + 1).padStart(2, '0') }}</span><label>日期<input v-model="entry.entry_date" type="date" required></label><button type="button" aria-label="删除条目" @click="removeCalendarEntry(index)">×</button></div><div class="form-grid three"><label>节奏色调<select v-model="entry.tone"><option value="green">推进</option><option value="green-yellow">先推后收</option><option value="yellow-green">先备后行</option><option value="yellow">观察</option><option value="red-yellow">缓冲</option><option value="red">收气</option><option value="rest">休整</option></select></label><label>日柱<input v-model.trim="entry.day_pillar" placeholder="可选"></label><label>状态标签<input v-model.trim="entry.status_label" placeholder="例如：准备期"></label><label>关键词<input v-model.trim="entry.keyword" placeholder="例如：观察"></label><label class="span-two">摘要<input v-model.trim="entry.summary" placeholder="这一天给用户的行动提示"></label></div><label>适合事项 <input v-model.trim="entry.suitableText" placeholder="用逗号分隔，例如：整理信息，沟通计划"></label><label>先不要做 <input v-model.trim="entry.unsuitableText" placeholder="用逗号分隔"></label><label>时间窗口 <input v-model.trim="entry.time_window" placeholder="例如：上午适合整理，下午适合轻推"></label><label>管理员备注 <textarea v-model.trim="entry.admin_note" rows="2" placeholder="仅后台可见"></textarea></label></article><p v-if="!calendarForm.entries.length" class="empty-cell entry-empty">草稿可以先不填条目；发布前至少需要一条。</p></div><div class="preview-strip"><div><span class="eyebrow">USER PREVIEW</span><strong>{{ calendarForm.title || '未命名日历' }}</strong></div><span>{{ calendarForm.start_date || '起始日期待定' }} — {{ calendarForm.end_date || '结束日期待定' }}</span><span>{{ calendarForm.entries.length }} 天 · 管理员备注不会展示给用户</span></div><div class="action-row editor-actions"><button class="primary-button" type="submit" :disabled="calendarSaving">{{ calendarSaving ? '保存中…' : '保存草稿' }}</button><button class="secondary-button" type="button" @click="cancelCalendarEdit">取消</button></div></form>
            <div v-else-if="selectedCalendarUser" class="editor-empty"><span>◌</span><p>选择一个版本开始编辑，或创建一张新的草稿日历。</p></div><div v-else class="editor-empty"><span>⌁</span><p>从左侧选择用户后，这里会显示其全部日历版本。</p></div>
          </div>
        </div>
      </section>

      <section v-else-if="activeTab === 'reports'" class="content-view">
        <div class="view-heading"><div><p class="eyebrow">AI / REPORT PIPELINE</p><h2>报告与任务</h2><p>查看全局生成状态，失败任务可受控重试。</p></div><button class="secondary-button" type="button" @click="exportResource('reports')">↓ 导出报告 CSV</button></div>
        <div class="section-switch"><button type="button" :class="{ active: reportSection === 'reports' }" @click="reportSection = 'reports'; loadReports()">报告列表</button><button type="button" :class="{ active: reportSection === 'tasks' }" @click="reportSection = 'tasks'; loadReportTasks()">生成任务</button></div>
        <template v-if="reportSection === 'reports'"><div class="filter-bar"><input v-model.trim="reportFilters.search" placeholder="搜索用户或报告标题" @keyup.enter="searchReports"><select v-model="reportFilters.status"><option value="">全部状态</option><option value="completed">已完成</option><option value="processing">生成中</option><option value="failed">失败</option></select><input v-model.trim="reportFilters.ai_model" placeholder="AI 模型，例如 deepseek-chat" @keyup.enter="searchReports"><label class="date-filter"><span>创建自</span><input v-model="reportFilters.date_from" type="date"></label><label class="date-filter"><span>至</span><input v-model="reportFilters.date_to" type="date"></label><button class="primary-button compact-button" type="button" @click="searchReports">查询</button></div><div v-if="reportsLoading" class="list-loading" aria-label="正在加载报告"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel"><div class="table-meta"><span>共 {{ reports.total }} 份报告</span><span>正文只读，生成任务独立追踪</span></div><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>报告</th><th>用户</th><th>状态</th><th>模型/耗时</th><th>创建时间</th><th>操作</th></tr></thead><tbody><tr v-for="report in reports.items" :key="report.id"><td><strong>{{ report.title }}</strong><small>#{{ report.id }} · {{ report.energy_type || '综合型' }}</small></td><td>{{ report.user_name }}<small>{{ report.user_phone }}</small></td><td><span :class="['status-badge', `report-${report.status}`]">{{ reportStatusText(report.status) }}</span></td><td>{{ report.ai_model || '—' }}<small>{{ report.generation_time_ms ? `${report.generation_time_ms} ms` : '—' }}</small></td><td class="muted-text">{{ formatDateTime(report.created_at) }}</td><td><button type="button" class="row-open" @click="openReport(report)">查看 →</button></td></tr><tr v-if="!reports.items.length"><td colspan="6" class="empty-cell">暂无报告记录。</td></tr></tbody></table></div><div class="pagination"><span>第 {{ reportPage }} / {{ pageCount(reports.total, reportPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="reportPage <= 1" @click="changeReportPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="reportPage >= pageCount(reports.total, reportPageSize)" @click="changeReportPage(1)">下一页</button></div></div></div></template>
        <template v-else><div class="filter-bar"><input v-model.trim="taskFilters.search" placeholder="搜索用户或任务 ID" @keyup.enter="searchReportTasks"><select v-model="taskFilters.status"><option value="">全部状态</option><option value="processing">生成中</option><option value="completed">已完成</option><option value="failed">失败</option></select><button class="primary-button compact-button" type="button" @click="searchReportTasks">查询</button></div><div v-if="tasksLoading" class="list-loading" aria-label="正在加载报告任务"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel"><div class="table-meta"><span>共 {{ reportTasks.total }} 个任务</span><span>失败任务最多重试 {{ reportRetryLimit }} 次</span></div><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>任务</th><th>用户</th><th>进度</th><th>状态</th><th>错误</th><th>操作</th></tr></thead><tbody><tr v-for="task in reportTasks.items" :key="task.task_id"><td><strong class="mono-text">{{ task.task_id.slice(0, 12) }}…</strong><small>{{ task.report_id ? `报告 #${task.report_id}` : '尚未生成报告' }} · {{ formatDateTime(task.created_at) }}</small></td><td>{{ task.user_name || `用户 #${task.user_id}` }}</td><td><div class="progress-cell"><span>{{ task.progress }}%</span><i><b :style="{ width: `${task.progress}%` }"></b></i></div></td><td><span :class="['status-badge', `task-${task.status}`]">{{ reportStatusText(task.status) }}</span><small v-if="task.retry_count">第 {{ task.retry_count }} 次重试</small></td><td class="error-cell">{{ task.error || '—' }}</td><td><button v-if="canRetryTask(task)" type="button" class="row-open" @click="retryTask(task)">重试 →</button><span v-else class="muted-text">{{ task.status === 'failed' && !task.has_input_snapshot ? '旧任务不可重试' : task.has_retry ? '已有重试任务' : '—' }}</span></td></tr><tr v-if="!reportTasks.items.length"><td colspan="6" class="empty-cell">暂无报告任务。</td></tr></tbody></table></div><div class="pagination"><span>第 {{ taskPage }} / {{ pageCount(reportTasks.total, taskPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="taskPage <= 1" @click="changeTaskPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="taskPage >= pageCount(reportTasks.total, taskPageSize)" @click="changeTaskPage(1)">下一页</button></div></div></div></template>
      </section>

      <section v-else-if="activeTab === 'logs'" class="content-view">
        <div class="view-heading"><div><p class="eyebrow">TRACE / AUDIT & BEHAVIOR</p><h2>日志中心</h2><p>关键变更、用户行动与任务状态都留下可追溯的痕迹。</p></div><button v-if="logSection !== 'tasks'" class="secondary-button" type="button" @click="exportResource(logSection === 'audit' ? 'audit-logs' : 'decision-logs')">↓ 导出当前 CSV</button></div>
        <div class="section-switch"><button type="button" :class="{ active: logSection === 'audit' }" @click="setLogSection('audit')">审计日志</button><button type="button" :class="{ active: logSection === 'behavior' }" @click="setLogSection('behavior')">用户行动记录</button><button type="button" :class="{ active: logSection === 'tasks' }" @click="setLogSection('tasks')">报告任务日志</button></div>
        <template v-if="logSection === 'audit'"><div class="filter-bar"><input v-model.trim="logFilters.search" placeholder="搜索用户、详情或操作" @keyup.enter="loadAuditLogs"><input v-model.trim="logFilters.action" placeholder="操作类型，例如 user.role.update"><input v-model.trim="logFilters.resource_type" placeholder="资源类型"><select v-model="logFilters.actor_user_id"><option value="">全部操作者</option><option v-for="member in staffUsers" :key="member.id" :value="member.id">{{ member.name }}</option></select><input v-model.trim="logFilters.target_user_id" type="number" min="1" placeholder="目标用户 ID"><label class="date-filter"><span>自</span><input v-model="logFilters.date_from" type="date"></label><label class="date-filter"><span>至</span><input v-model="logFilters.date_to" type="date"></label><button class="primary-button compact-button" type="button" @click="loadAuditLogs">查询</button><button class="filter-reset" type="button" @click="resetLogFilters">清空</button></div><div v-if="auditLoading" class="list-loading" aria-label="正在加载审计日志"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel"><div class="table-meta"><span>共 {{ auditLogs.total }} 条审计记录</span><span>详情不包含密码、令牌或 AI Prompt</span></div><div class="admin-table-wrap"><table class="admin-table audit-table"><thead><tr><th>时间</th><th>操作</th><th>资源</th><th>操作者</th><th>目标</th><th>请求</th><th>详情</th></tr></thead><tbody><tr v-for="log in auditLogs.items" :key="log.id"><td class="muted-text">{{ formatDateTime(log.created_at) }}</td><td><span class="action-code">{{ actionLabel(log.action) }}</span><small>{{ log.action }}</small></td><td>{{ resourceLabel(log.resource_type) }}{{ log.resource_id ? ` #${log.resource_id}` : '' }}</td><td>{{ log.actor_name || log.actor_user_id || '系统' }}</td><td>{{ log.target_user_name || log.target_user_id || '—' }}</td><td><span class="mono-text">{{ log.request_id ? log.request_id.slice(0, 8) : '—' }}</span><small>{{ log.ip_address || '—' }}</small></td><td><button type="button" class="detail-link" @click="openLogDetail(log)">{{ log.details_json ? '查看 JSON' : (log.details || '—') }}</button></td></tr><tr v-if="!auditLogs.items.length"><td colspan="7" class="empty-cell">暂无审计记录。</td></tr></tbody></table></div><div class="pagination"><span>第 {{ logPage }} / {{ pageCount(auditLogs.total, logPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="logPage <= 1" @click="changeLogPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="logPage >= pageCount(auditLogs.total, logPageSize)" @click="changeLogPage(1)">下一页</button></div></div></div></template>
        <template v-else-if="logSection === 'behavior'"><div class="filter-bar"><input v-model.trim="behaviorFilters.search" placeholder="搜索用户或记录内容" @keyup.enter="searchDecisionLogs"><select v-model="behaviorFilters.kind"><option value="">全部类型</option><option value="action">行动</option><option value="decision">决策</option></select><select v-model="behaviorFilters.status"><option value="">全部状态</option><option value="done">已完成</option><option value="doing">进行中</option><option value="skipped">已跳过</option></select><label class="date-filter"><span>自</span><input v-model="behaviorFilters.date_from" type="date"></label><label class="date-filter"><span>至</span><input v-model="behaviorFilters.date_to" type="date"></label><button class="primary-button compact-button" type="button" @click="searchDecisionLogs">查询</button></div><div v-if="decisionLoading" class="list-loading" aria-label="正在加载用户行动记录"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel"><div class="table-meta"><span>共 {{ decisionLogs.total }} 条行动记录</span><span>管理员只读，内容来源于用户本人</span></div><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>日期</th><th>用户</th><th>类型</th><th>状态</th><th>记录内容</th><th>备注</th><th>创建时间</th></tr></thead><tbody><tr v-for="log in decisionLogs.items" :key="log.id"><td>{{ formatDate(log.log_date) }}</td><td>{{ log.user_name }}<small>#{{ log.user_id }}</small></td><td>{{ log.kind === 'decision' ? '决策' : '行动' }}</td><td><span :class="['status-badge', `decision-${log.status}`]">{{ decisionStatusText(log.status) }}</span></td><td class="content-cell">{{ log.content }}</td><td class="content-cell">{{ log.note || '—' }}</td><td class="muted-text">{{ formatDateTime(log.created_at) }}</td></tr><tr v-if="!decisionLogs.items.length"><td colspan="7" class="empty-cell">暂无用户行动记录。</td></tr></tbody></table></div><div class="pagination"><span>第 {{ decisionPage }} / {{ pageCount(decisionLogs.total, decisionPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="decisionPage <= 1" @click="changeDecisionPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="decisionPage >= pageCount(decisionLogs.total, decisionPageSize)" @click="changeDecisionPage(1)">下一页</button></div></div></div></template>
        <template v-else><div class="filter-bar"><input v-model.trim="taskFilters.search" placeholder="搜索用户或任务 ID" @keyup.enter="searchReportTasks"><select v-model="taskFilters.status"><option value="">全部状态</option><option value="processing">生成中</option><option value="completed">已完成</option><option value="failed">失败</option></select><button class="primary-button compact-button" type="button" @click="searchReportTasks">查询</button></div><div v-if="tasksLoading" class="list-loading" aria-label="正在加载报告任务日志"><i v-for="index in 4" :key="index"></i></div><div v-else class="table-panel"><div class="table-meta"><span>共 {{ reportTasks.total }} 个任务</span><span>任务日志只读，失败任务请到报告页重试</span></div><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>任务</th><th>用户</th><th>状态</th><th>进度</th><th>失败原因</th><th>更新时间</th></tr></thead><tbody><tr v-for="task in reportTasks.items" :key="task.task_id"><td><strong class="mono-text">{{ task.task_id.slice(0, 12) }}…</strong><small>{{ task.report_id ? `报告 #${task.report_id}` : '尚未生成报告' }}</small></td><td>{{ task.user_name || `用户 #${task.user_id}` }}</td><td><span :class="['status-badge', `task-${task.status}`]">{{ reportStatusText(task.status) }}</span><small v-if="task.retry_count">第 {{ task.retry_count }} 次重试</small></td><td>{{ task.progress }}%</td><td class="error-cell">{{ task.error || '—' }}</td><td class="muted-text">{{ formatDateTime(task.updated_at) }}</td></tr><tr v-if="!reportTasks.items.length"><td colspan="6" class="empty-cell">暂无报告任务日志。</td></tr></tbody></table></div><div class="pagination"><span>第 {{ taskPage }} / {{ pageCount(reportTasks.total, taskPageSize) }} 页</span><div><button class="secondary-button compact-button" type="button" :disabled="taskPage <= 1" @click="changeTaskPage(-1)">上一页</button><button class="secondary-button compact-button" type="button" :disabled="taskPage >= pageCount(reportTasks.total, taskPageSize)" @click="changeTaskPage(1)">下一页</button></div></div></div></template>
      </section>

      <section v-else-if="activeTab === 'staff'" class="content-view">
        <div class="view-heading"><div><p class="eyebrow">TEAM / ACCESS</p><h2>后台成员</h2><p>维护咨询师与管理员席位，邀请链接只展示一次。</p></div></div>
        <div class="staff-grid"><article class="panel-surface invite-card"><p class="eyebrow">NEW INVITATION</p><h3>邀请后台成员</h3><form class="stack-form" @submit.prevent="inviteStaff"><label>手机号<input v-model.trim="inviteForm.phone" required maxlength="11" placeholder="11 位手机号"></label><label>角色<select v-model="inviteForm.role"><option value="consultant">咨询师</option><option value="admin">管理员</option></select></label><button class="primary-button" type="submit">生成邀请链接</button></form><div v-if="inviteToken" class="invite-result"><span>本次令牌</span><code>{{ inviteToken }}</code><router-link :to="{ path: '/auth/invite', query: { token: inviteToken } }">打开邀请页面 →</router-link></div></article><article class="panel-surface team-card"><div class="panel-heading"><div><p class="eyebrow">CURRENT TEAM</p><h3>当前成员</h3></div><span>{{ staffUsers.length }}</span></div><div class="team-list"><div v-for="member in staffUsers" :key="member.id" class="team-row"><span class="avatar-mark">{{ member.name?.slice(0, 1) || '人' }}</span><div><strong>{{ member.name }}</strong><small>{{ roleText(member.role) }} · {{ member.phone }}</small></div><span :class="['status-badge', member.is_active ? 'success' : 'muted']">{{ member.is_active ? '正常' : '停用' }}</span></div><p v-if="!staffUsers.length" class="empty-cell">暂无后台成员。</p></div></article></div>
      </section>
    </main>

    <div v-if="detailUser" class="drawer-layer" @click.self="closeUserDetail">
      <aside class="drawer user-drawer"><div class="drawer-header"><div class="person-cell"><span class="avatar-mark large">{{ detailUser.name?.slice(0, 1) || '人' }}</span><span><p class="eyebrow">USER #{{ detailUser.id }}</p><h2>{{ detailUser.name }}</h2><small>{{ detailUser.phone }}</small></span></div><button type="button" class="drawer-close" aria-label="关闭用户详情" @click="closeUserDetail">×</button></div><div class="drawer-tabs"><button v-for="tab in userPanelTabs" :key="tab.id" type="button" :class="{ active: userPanelTab === tab.id }" @click="setUserPanelTab(tab.id)">{{ tab.label }}</button></div><div v-if="userPanelLoading" class="drawer-loading">正在整理用户资料…</div><div v-else class="drawer-body">
        <section v-if="userPanelTab === 'profile'" class="drawer-section"><div class="profile-summary"><div><span>报告</span><strong>{{ userSummary?.summary?.report_count ?? '—' }}</strong></div><div><span>预约</span><strong>{{ userSummary?.summary?.booking_count ?? '—' }}</strong></div><div><span>日历</span><strong>{{ userSummary?.summary?.calendar_count ?? '—' }}</strong></div><div><span>学习</span><strong>{{ userSummary?.summary?.average_course_progress ?? 0 }}%</strong></div></div><form class="stack-form" @submit.prevent="saveUserProfile"><div class="form-grid two"><label>姓名<input v-model.trim="userEdit.name" required></label><label>性别<select v-model="userEdit.gender"><option value="">未填写</option><option value="male">男</option><option value="female">女</option></select></label><label>出生年<input v-model="userEdit.birth_year" type="number" min="1900" max="2026"></label><label>出生月<input v-model="userEdit.birth_month" type="number" min="1" max="12"></label><label>出生日<input v-model="userEdit.birth_day" type="number" min="1" max="31"></label><label>出生时<input v-model="userEdit.birth_hour" type="number" min="0" max="23"></label><label>出生分<input v-model="userEdit.birth_minute" type="number" min="0" max="59"></label><label>出生地<input v-model.trim="userEdit.birth_place" placeholder="可选"></label><label class="span-two">头像地址<input v-model.trim="userEdit.avatar_url" type="url" placeholder="可选，填写可访问的头像地址"></label></div><button class="primary-button" type="submit">保存资料</button></form><div class="detail-facts"><p><span>角色</span><strong>{{ roleText(detailUser.role) }}</strong></p><p><span>状态</span><strong>{{ detailUser.is_active ? '正常' : '已停用' }}</strong></p><p><span>注册时间</span><strong>{{ formatDateTime(detailUser.created_at) }}</strong></p><p><span>最近登录</span><strong>{{ formatDateTime(detailUser.last_login_at) }}</strong></p></div></section>
        <section v-else-if="userPanelTab === 'reports'" class="drawer-section"><div class="section-caption"><h3>用户报告</h3><span>{{ userPanelData.reports?.total || 0 }} 份</span></div><div class="drawer-list"><button v-for="report in userPanelData.reports?.items || []" :key="report.id" type="button" class="drawer-list-item" @click="openReport(report)"><span><strong>{{ report.title }}</strong><small>{{ formatDate(report.created_at) }} · {{ report.energy_type || '综合型' }}</small></span><b>查看 →</b></button><p v-if="!userPanelData.reports?.items?.length" class="empty-cell">暂无报告。</p></div></section>
        <section v-else-if="userPanelTab === 'bookings'" class="drawer-section"><div class="section-caption"><h3>用户预约</h3><span>{{ userPanelData.bookings?.total || 0 }} 条</span></div><div class="drawer-list"><button v-for="booking in userPanelData.bookings?.items || []" :key="booking.id" type="button" class="drawer-list-item" @click="openBookingDetail(booking)"><span><strong>{{ booking.service_name }}</strong><small>{{ booking.confirmed_date || booking.preferred_time }} · {{ booking.consultant_name || '未分配' }}</small></span><span :class="['status-badge', `booking-${booking.status}`]">{{ statusText(booking.status) }}</span></button><p v-if="!userPanelData.bookings?.items?.length" class="empty-cell">暂无预约。</p></div></section>
        <section v-else-if="userPanelTab === 'courses'" class="drawer-section"><div class="section-caption"><h3>课程进度</h3><span>{{ userPanelData.courses?.length || 0 }} 门</span></div><div class="course-admin-list"><div v-for="course in userPanelData.courses || []" :key="course.course_id" class="course-admin-row"><div><strong>{{ course.title }}</strong><small>{{ course.completed_lessons }} / {{ course.total_lessons }} 课时</small></div><div class="course-progress-editor"><input v-model.number="course.progress" type="number" min="0" max="100"><span>%</span><button type="button" @click="saveCourseProgress(course)">保存</button></div></div><p v-if="!userPanelData.courses?.length" class="empty-cell">暂无课程。</p></div></section>
        <section v-else-if="userPanelTab === 'calendar'" class="drawer-section"><div class="section-caption"><h3>用户日历</h3><span>{{ userPanelData.calendars?.length || 0 }} 个版本</span></div><div class="drawer-list"><button v-for="calendar in userPanelData.calendars || []" :key="calendar.id" type="button" class="drawer-list-item" @click="openCalendarForUser(detailUser)"><span><strong>{{ calendar.title }}</strong><small>v{{ calendar.version_number }} · {{ calendar.entries?.length || 0 }} 天</small></span><span :class="['status-badge', `calendar-${calendar.status}`]">{{ calendarStatusText(calendar.status) }}</span></button><p v-if="!userPanelData.calendars?.length" class="empty-cell">暂无日历。</p></div><button class="secondary-button full-button" type="button" @click="openCalendarForUser(detailUser)">进入日历编辑器 →</button></section>
        <section v-else-if="userPanelTab === 'decisions'" class="drawer-section"><div class="section-caption"><h3>行动 / 决策记录</h3><span>{{ userPanelData.decisions?.total || 0 }} 条 · 只读</span></div><div class="decision-list"><div v-for="log in userPanelData.decisions?.items || []" :key="log.id"><div><strong>{{ log.content }}</strong><small>{{ formatDate(log.log_date) }} · {{ log.kind === 'decision' ? '决策' : '行动' }}</small></div><span :class="['status-badge', `decision-${log.status}`]">{{ decisionStatusText(log.status) }}</span></div><p v-if="!userPanelData.decisions?.items?.length" class="empty-cell">暂无行动记录。</p></div></section>
        <section v-else class="drawer-section"><div class="section-caption"><h3>最近审计活动</h3><span>{{ userPanelData.activity?.total || 0 }} 条</span></div><div class="activity-list compact"><div v-for="log in userPanelData.activity?.items || []" :key="log.id" class="activity-item"><span class="activity-dot"></span><div><strong>{{ actionLabel(log.action) }}</strong><p>{{ resourceLabel(log.resource_type) }}</p></div><time>{{ formatDateTime(log.created_at) }}</time></div><p v-if="!userPanelData.activity?.items?.length" class="empty-cell">暂无审计活动。</p></div></section>
      </div></aside>
    </div>

    <div v-if="bookingDetail" class="drawer-layer" @click.self="bookingDetail = null"><aside class="drawer booking-drawer"><div class="drawer-header"><div><p class="eyebrow">BOOKING #{{ bookingDetail.id }}</p><h2>{{ bookingDetail.service_name }}</h2><small>{{ bookingDetail.user_name || `用户 #${bookingDetail.user_id}` }} · {{ bookingDetail.user_phone || bookingDetail.contact_phone }}</small></div><button type="button" class="drawer-close" @click="bookingDetail = null">×</button></div><form class="drawer-body stack-form" @submit.prevent="saveBooking"><div class="detail-facts"><p><span>关注议题</span><strong>{{ bookingDetail.topics?.join('、') || '—' }}</strong></p><p><span>用户备注</span><strong>{{ bookingDetail.notes || '—' }}</strong></p><p><span>期望时间</span><strong>{{ bookingDetail.preferred_time }}</strong></p></div><label>预约状态<select v-model="bookingEditor.status"><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></label><div class="form-grid two"><label>确认日期<input v-model="bookingEditor.confirmed_date" type="date"></label><label>确认时间<input v-model="bookingEditor.confirmed_time" type="time"></label></div><label>分配咨询师<select v-model="bookingEditor.consultant_id"><option :value="null">未分配</option><option v-for="consultant in consultants" :key="consultant.id" :value="consultant.id">{{ consultant.name }}</option></select></label><label>会议链接<input v-model.trim="bookingEditor.meeting_url" type="url" placeholder="可选"></label><label>会议备注<textarea v-model.trim="bookingEditor.meeting_notes" rows="4" placeholder="记录会议安排或沟通要点"></textarea></label><label v-if="bookingEditor.status === 'cancelled'">取消原因<textarea v-model.trim="bookingEditor.cancellation_reason" rows="3" placeholder="可选"></textarea></label><button class="primary-button" type="submit">保存预约</button></form></aside></div>

    <div v-if="reportDetail" class="drawer-layer" @click.self="reportDetail = null"><aside class="drawer report-drawer"><div class="drawer-header"><div><p class="eyebrow">REPORT #{{ reportDetail.id }}</p><h2>{{ reportDetail.title }}</h2><small>{{ reportDetail.user_name }} · {{ reportDetail.user_phone }}</small></div><button type="button" class="drawer-close" @click="reportDetail = null">×</button></div><div class="drawer-body report-body"><div class="report-meta-grid"><div><span>状态</span><strong>{{ reportStatusText(reportDetail.status) }}</strong></div><div><span>模型</span><strong>{{ reportDetail.ai_model || '—' }}</strong></div><div><span>耗时</span><strong>{{ reportDetail.generation_time_ms ? `${reportDetail.generation_time_ms} ms` : '—' }}</strong></div><div><span>生成于</span><strong>{{ formatDateTime(reportDetail.created_at) }}</strong></div><div><span>生成来源</span><strong>{{ reportDetail.basic_info?.generated_by || '—' }}</strong></div></div><article class="report-block"><h3>摘要</h3><p>{{ reportDetail.summary || '暂无摘要。' }}</p></article><article class="report-block"><h3>能量画像</h3><pre>{{ prettyJson(reportDetail.energy_profile) }}</pre></article><article class="report-block"><h3>行动建议</h3><pre>{{ prettyJson(reportDetail.career_guidance) }}</pre></article><article class="report-block"><h3>关系模式</h3><pre>{{ prettyJson(reportDetail.relationship_pattern) }}</pre></article><article class="report-block"><h3>个人成长</h3><pre>{{ prettyJson(reportDetail.personal_growth) }}</pre></article></div></aside></div>

    <div v-if="logDetail" class="drawer-layer" @click.self="logDetail = null"><aside class="drawer log-drawer"><div class="drawer-header"><div><p class="eyebrow">AUDIT #{{ logDetail.id }}</p><h2>{{ actionLabel(logDetail.action) }}</h2><small>{{ formatDateTime(logDetail.created_at) }}</small></div><button type="button" class="drawer-close" @click="logDetail = null">×</button></div><div class="drawer-body"><div class="detail-facts"><p><span>操作编码</span><strong class="mono-text">{{ logDetail.action }}</strong></p><p><span>资源</span><strong>{{ resourceLabel(logDetail.resource_type) }} {{ logDetail.resource_id ? `#${logDetail.resource_id}` : '' }}</strong></p><p><span>操作者</span><strong>{{ logDetail.actor_name || logDetail.actor_user_id || '系统' }}</strong></p><p><span>目标用户</span><strong>{{ logDetail.target_user_name || logDetail.target_user_id || '—' }}</strong></p><p><span>请求 ID</span><strong class="mono-text">{{ logDetail.request_id || '—' }}</strong></p><p><span>IP / UA</span><strong>{{ logDetail.ip_address || '—' }}<small>{{ logDetail.user_agent || '' }}</small></strong></p></div><div class="json-view"><span>结构化详情</span><pre>{{ prettyJson(logDetail.details_json || logDetail.details || {}) }}</pre></div></div></aside></div>
  </div>
</template>

<script>
import {
  archiveAdminCalendar,
  createAdminCalendar,
  createAdminCalendarDraft,
  createStaffInvite,
  downloadAdminExport,
  getAdminAuditLogs,
  getAdminBookings,
  getAdminCalendars,
  getAdminDashboard,
  getAdminDecisionLogs,
  getAdminReport,
  getAdminReportTasks,
  getAdminReports,
  getAdminUser,
  getAdminUserBookings,
  getAdminUserCourses,
  getAdminUserDecisionLogs,
  getAdminUserSummary,
  getAllAdminUsers,
  getAdminUsers,
  importAdminCalendar,
  publishAdminCalendar,
  resetAdminUserPassword,
  retryAdminReportTask,
  updateAdminBooking,
  updateAdminCalendar,
  updateAdminUserProfile,
  updateAdminUserRole,
  updateAdminUserStatus,
  updateAdminUserCourseProgress
} from '../utils/businessService'

const EMPTY_PAGE = { total: 0, items: [] }

function todayKey() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function createEntry(date = todayKey()) {
  return {
    _key: `entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    entry_date: date,
    day_pillar: '',
    tone: 'yellow',
    status_label: '',
    keyword: '',
    summary: '',
    suitableText: '',
    unsuitableText: '',
    time_window: '',
    admin_note: ''
  }
}

export default {
  name: 'AdminConsole',
  data() {
    return {
      activeTab: 'overview',
      tabs: [
        { id: 'overview', index: '01', label: '总览' },
        { id: 'users', index: '02', label: '用户' },
        { id: 'bookings', index: '03', label: '预约' },
        { id: 'calendar', index: '04', label: '日历' },
        { id: 'reports', index: '05', label: '报告' },
        { id: 'logs', index: '06', label: '日志' },
        { id: 'staff', index: '07', label: '后台成员' }
      ],
      dashboardRanges: [{ id: '7d', label: '7 天' }, { id: '30d', label: '30 天' }, { id: '90d', label: '90 天' }],
      dashboardRange: '30d',
      dashboard: null,
      dashboardLoading: false,
      lastUpdated: '',
      autoRefresh: true,
      refreshTimer: null,
      users: { ...EMPTY_PAGE },
      usersLoading: false,
      userFilters: { search: '', role: '', is_active: '', created_from: '', created_to: '' },
      userPage: 1,
      userPageSize: 12,
      consultants: [],
      staffUsers: [],
      bookings: { ...EMPTY_PAGE },
      bookingsLoading: false,
      bookingFilters: { search: '', status: '', consultant_id: '', date_from: '', date_to: '' },
      bookingPage: 1,
      bookingPageSize: 12,
      reports: { ...EMPTY_PAGE },
      reportsLoading: false,
      reportFilters: { search: '', status: '', ai_model: '', date_from: '', date_to: '' },
      reportPage: 1,
      reportPageSize: 12,
      reportSection: 'reports',
      reportTasks: { ...EMPTY_PAGE },
      tasksLoading: false,
      taskFilters: { search: '', status: '' },
      taskPage: 1,
      taskPageSize: 12,
      reportRetryLimit: 2,
      auditLogs: { ...EMPTY_PAGE },
      auditLoading: false,
      logFilters: { search: '', action: '', resource_type: '', actor_user_id: '', target_user_id: '', date_from: '', date_to: '' },
      logPage: 1,
      logPageSize: 20,
      decisionLogs: { ...EMPTY_PAGE },
      decisionLoading: false,
      decisionPage: 1,
      decisionPageSize: 20,
      behaviorFilters: { search: '', kind: '', status: '', date_from: '', date_to: '' },
      logSection: 'audit',
      detailUser: null,
      userSummary: null,
      userPanelTab: 'profile',
      userPanelLoading: false,
      userEdit: {},
      userPanelData: { reports: null, bookings: null, courses: [], calendars: null, decisions: null, activity: null },
      bookingDetail: null,
      bookingEditor: {},
      reportDetail: null,
      logDetail: null,
      calendarUsers: [],
      calendarUserSearch: '',
      selectedCalendarUser: null,
      calendars: [],
      calendarLoading: false,
      calendarUsersLoading: false,
      calendarForm: { visible: false, id: null, title: '', note: '', start_date: '', end_date: '', status: '', version_number: 1, entries: [] },
      calendarSaving: false,
      showCalendarImport: false,
      calendarImportJson: '',
      inviteForm: { phone: '', role: 'consultant' },
      inviteToken: '',
      staffLoading: false,
      message: ''
    }
  },
  computed: {
    activeLoading() {
      return this.dashboardLoading || this.calendarSaving || this.userPanelLoading || this.usersLoading || this.bookingsLoading || this.reportsLoading || this.tasksLoading || this.auditLoading || this.decisionLoading || this.calendarLoading || this.calendarUsersLoading || this.staffLoading
    },
    metricCards() {
      const metrics = this.dashboard?.metrics || {}
      return [
        { key: 'users', label: '用户总数', value: metrics.user_total ?? 0, caption: `活跃 ${metrics.active_users ?? 0} · 本期新增 ${metrics.new_users ?? 0}`, mark: '人', tone: 'cinnabar' },
        { key: 'reports', label: '报告总数', value: metrics.report_total ?? 0, caption: `成功率 ${metrics.report_success_rate ?? 0}%`, mark: '笺', tone: 'gold' },
        { key: 'pending', label: '待确认预约', value: metrics.booking_pending ?? 0, caption: `已确认 ${metrics.booking_confirmed ?? 0} · 已完成 ${metrics.booking_completed ?? 0}`, mark: '约', tone: 'jade' },
        { key: 'tasks', label: '报告任务', value: metrics.report_processing ?? 0, caption: `生成中 · 失败 ${metrics.report_failed ?? 0}`, mark: 'AI', tone: 'ink' },
        { key: 'calendars', label: '已发布日历', value: metrics.published_calendars ?? 0, caption: `用户行动记录 ${metrics.decision_logs ?? 0}`, mark: '历', tone: 'jade' },
        { key: 'learners', label: '活跃学习者', value: metrics.active_learners ?? 0, caption: '正在进行中的课程账号', mark: '学', tone: 'gold' }
      ]
    },
    trendMax() {
      const values = (this.dashboard?.trends || []).flatMap(item => [item.new_users, item.reports, item.bookings, item.decision_logs])
      return Math.max(1, ...values)
    },
    chartGridLines() {
      return [18, 67, 116, 165, 214]
    },
    trendSeries() {
      const trends = this.dashboard?.trends || []
      const series = [
        { key: 'new_users', label: '新增用户', color: '#b85c50' },
        { key: 'reports', label: '报告', color: '#c69b42' },
        { key: 'bookings', label: '预约', color: '#5d917e' },
        { key: 'decision_logs', label: '行动记录', color: '#59483d' }
      ]
      return series.map(item => ({
        ...item,
        points: trends.map((point, index) => {
          const x = 28 + (index * 708 / Math.max(1, trends.length - 1))
          const y = 214 - ((point[item.key] || 0) / this.trendMax) * 196
          return `${x.toFixed(1)},${y.toFixed(1)}`
        }).join(' ')
      }))
    },
    trendTicks() {
      const trends = this.dashboard?.trends || []
      if (!trends.length) return []
      const step = Math.max(1, Math.ceil(trends.length / 6))
      return trends.map((point, index) => ({ index, x: 28 + (index * 708 / Math.max(1, trends.length - 1)), label: this.formatShortDate(point.date) })).filter((tick, index) => index % step === 0 || index === trends.length - 1)
    },
    distributionGroups() {
      const distributions = this.dashboard?.distributions || {}
      return [
        { key: 'roles', label: '用户角色', items: distributions.users_by_role || [] },
        { key: 'bookings', label: '预约状态', items: distributions.bookings_by_status || [] },
        { key: 'reports', label: '报告状态', items: distributions.reports_by_status || [] },
        { key: 'calendars', label: '日历状态', items: distributions.calendars_by_status || [] }
      ]
    },
    userPanelTabs() {
      return [
        { id: 'profile', label: '资料' },
        { id: 'reports', label: '报告' },
        { id: 'bookings', label: '预约' },
        { id: 'courses', label: '课程' },
        { id: 'calendar', label: '日历' },
        { id: 'decisions', label: '行动记录' },
        { id: 'activity', label: '审计活动' }
      ]
    }
  },
  async mounted() {
    document.addEventListener('visibilitychange', this.handleVisibilityChange)
    await Promise.all([this.loadDashboard(), this.loadUsers(), this.loadConsultants(), this.loadStaff()])
    this.syncAutoRefresh()
  },
  beforeUnmount() {
    document.removeEventListener('visibilitychange', this.handleVisibilityChange)
    this.clearRefreshTimer()
  },
  methods: {
    async switchTab(tab) {
      this.activeTab = tab
      if (tab === 'overview') await this.loadDashboard()
      if (tab === 'users') await this.loadUsers()
      if (tab === 'bookings') await this.loadBookings()
      if (tab === 'calendar' && !this.calendarUsers.length) await this.loadCalendarUsers()
      if (tab === 'reports') await this.loadReports()
      if (tab === 'logs') await this.loadAuditLogs()
      this.syncAutoRefresh()
    },
    async refreshActive() {
      if (this.activeTab === 'overview') return this.loadDashboard()
      if (this.activeTab === 'users') return this.loadUsers()
      if (this.activeTab === 'bookings') return this.loadBookings()
      if (this.activeTab === 'calendar') return this.selectedCalendarUser ? this.loadCalendars() : this.loadCalendarUsers()
      if (this.activeTab === 'reports') return this.reportSection === 'reports' ? this.loadReports() : this.loadReportTasks()
       if (this.activeTab === 'logs') return this.logSection === 'audit' ? this.loadAuditLogs() : this.logSection === 'behavior' ? this.loadDecisionLogs() : this.loadReportTasks()
      return this.loadStaff()
    },
    async loadDashboard(silent = false) {
      if (!silent) this.dashboardLoading = true
      try {
        this.dashboard = await getAdminDashboard(this.dashboardRange)
        this.lastUpdated = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        this.reportRetryLimit = 2
      } catch (error) {
        if (!silent) this.message = this.errorText(error)
      } finally {
        this.dashboardLoading = false
      }
    },
    async changeDashboardRange(range) {
      if (this.dashboardRange === range) return
      this.dashboardRange = range
      await this.loadDashboard()
    },
    syncAutoRefresh() {
      this.clearRefreshTimer()
      if (this.autoRefresh && this.activeTab === 'overview' && document.visibilityState === 'visible') {
        this.refreshTimer = window.setInterval(() => this.loadDashboard(true), 60000)
      }
    },
    clearRefreshTimer() {
      if (this.refreshTimer) window.clearInterval(this.refreshTimer)
      this.refreshTimer = null
    },
    handleVisibilityChange() {
      this.syncAutoRefresh()
    },
    goFromAlert(alert) {
      const target = alert.route === 'calendar' ? 'calendar' : alert.route === 'reports' ? 'reports' : alert.route === 'logs' ? 'logs' : 'bookings'
      this.switchTab(target)
    },
    async loadUsers() {
      this.usersLoading = true
      try {
        this.users = await getAdminUsers({ ...this.cleanParams(this.userFilters), page: this.userPage, size: this.userPageSize })
      } catch (error) { this.message = this.errorText(error) } finally { this.usersLoading = false }
    },
    async searchUsers() { this.userPage = 1; await this.loadUsers() },
    resetUserFilters() { this.userFilters = { search: '', role: '', is_active: '', created_from: '', created_to: '' }; this.searchUsers() },
    async changeUserPage(offset) { const next = this.userPage + offset; if (next < 1 || next > this.pageCount(this.users.total, this.userPageSize)) return; this.userPage = next; await this.loadUsers() },
    async loadConsultants() {
      try { const response = await getAllAdminUsers({ role: 'consultant', is_active: true, size: 100 }); this.consultants = response.items || [] } catch (error) { this.message = this.errorText(error) }
    },
    async loadStaff() {
      this.staffLoading = true
      try { const [admins, consultants] = await Promise.all([getAllAdminUsers({ role: 'admin', size: 100 }), getAllAdminUsers({ role: 'consultant', size: 100 })]); this.staffUsers = [...(admins.items || []), ...(consultants.items || [])].sort((a, b) => a.id - b.id) } catch (error) { this.message = this.errorText(error) } finally { this.staffLoading = false }
    },
    async openUserDetail(user) {
      this.detailUser = user
      this.userPanelTab = 'profile'
      this.userPanelLoading = true
      try {
        const [detail, summary] = await Promise.all([getAdminUser(user.id), getAdminUserSummary(user.id)])
        this.detailUser = detail
        this.userSummary = summary
        this.userEdit = this.toUserEdit(detail)
        this.userPanelData = { reports: null, bookings: null, courses: [], calendars: null, decisions: null, activity: null }
      } catch (error) { this.message = this.errorText(error); this.detailUser = null } finally { this.userPanelLoading = false }
    },
    closeUserDetail() { this.detailUser = null; this.userSummary = null },
    async setUserPanelTab(tab) {
      this.userPanelTab = tab
      if (!this.detailUser || tab === 'profile') return
      this.userPanelLoading = true
      try {
        const id = this.detailUser.id
        if (tab === 'reports') this.userPanelData.reports = await getAdminReports({ user_id: id, page: 1, size: 100 })
        if (tab === 'bookings') this.userPanelData.bookings = await getAdminUserBookings(id, { page: 1, size: 100 })
        if (tab === 'courses') this.userPanelData.courses = (await getAdminUserCourses(id)).items || []
        if (tab === 'calendar') this.userPanelData.calendars = (await getAdminCalendars(id)).items || []
        if (tab === 'decisions') this.userPanelData.decisions = await getAdminUserDecisionLogs(id, { page: 1, size: 100 })
        if (tab === 'activity') this.userPanelData.activity = await getAdminAuditLogs({ target_user_id: id, page: 1, size: 100 })
      } catch (error) { this.message = this.errorText(error) } finally { this.userPanelLoading = false }
    },
    toUserEdit(user) {
      return { name: user.name || '', gender: user.gender || '', birth_year: user.birth_year ?? '', birth_month: user.birth_month ?? '', birth_day: user.birth_day ?? '', birth_hour: user.birth_hour ?? '', birth_minute: user.birth_minute ?? '', birth_place: user.birth_place || '', avatar_url: user.avatar_url || '' }
    },
    async saveUserProfile() {
      if (!this.detailUser) return
      try {
        const payload = { ...this.userEdit }
        payload.gender = payload.gender || null
        ;['birth_year', 'birth_month', 'birth_day', 'birth_hour', 'birth_minute'].forEach(key => { payload[key] = payload[key] === '' ? null : Number(payload[key]) })
        const updated = await updateAdminUserProfile(this.detailUser.id, payload)
        this.detailUser = updated
        this.userEdit = this.toUserEdit(updated)
        this.message = '用户资料已保存'
        await this.loadUsers()
      } catch (error) { this.message = this.errorText(error) }
    },
    async toggleUser(user) {
      try { const updated = await updateAdminUserStatus(user.id, !user.is_active); Object.assign(user, updated); this.message = '用户状态已更新'; await Promise.all([this.loadConsultants(), this.loadStaff()]) } catch (error) { this.message = this.errorText(error) }
    },
    async changeRole(user, role) {
      try { const updated = await updateAdminUserRole(user.id, role); Object.assign(user, updated); this.message = '用户角色已更新'; await Promise.all([this.loadConsultants(), this.loadStaff()]) } catch (error) { this.message = this.errorText(error); await this.loadUsers() }
    },
    async resetUserPassword(user) {
      if (!user.is_active) { await this.toggleUser(user); return }
      const nextPassword = window.prompt(`为 ${user.name} 设置新密码（至少 8 位）`)
      if (nextPassword === null) return
      if (nextPassword.length < 8) { this.message = '新密码至少需要 8 位'; return }
      try { await resetAdminUserPassword(user.id, nextPassword); this.message = '密码已重置，原会话已失效' } catch (error) { this.message = this.errorText(error) }
    },
    async loadBookings() {
      this.bookingsLoading = true
      try { this.bookings = await getAdminBookings({ ...this.cleanParams(this.bookingFilters), page: this.bookingPage, size: this.bookingPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.bookingsLoading = false }
    },
    async searchBookings() { this.bookingPage = 1; await this.loadBookings() },
    resetBookingFilters() { this.bookingFilters = { search: '', status: '', consultant_id: '', date_from: '', date_to: '' }; this.searchBookings() },
    async changeBookingPage(offset) { const next = this.bookingPage + offset; if (next < 1 || next > this.pageCount(this.bookings.total, this.bookingPageSize)) return; this.bookingPage = next; await this.loadBookings() },
    openBookingDetail(booking) { this.bookingDetail = booking; this.bookingEditor = { status: booking.status, confirmed_date: booking.confirmed_date || '', confirmed_time: booking.confirmed_time || '', consultant_id: booking.consultant_id ?? null, meeting_url: booking.meeting_url || '', meeting_notes: booking.meeting_notes || '', cancellation_reason: booking.cancellation_reason || '' } },
    async saveBooking() {
      if (!this.bookingDetail) return
      try { const updated = await updateAdminBooking(this.bookingDetail.id, { ...this.bookingEditor, consultant_id: this.bookingEditor.consultant_id || null, confirmed_date: this.bookingEditor.confirmed_date || null, confirmed_time: this.bookingEditor.confirmed_time || null, cancellation_reason: this.bookingEditor.cancellation_reason || null }); Object.assign(this.bookingDetail, updated); this.message = '预约已更新'; await this.loadBookings() } catch (error) { this.message = this.errorText(error) }
    },
    async loadCalendarUsers() {
      this.calendarUsersLoading = true
      try { const response = await getAllAdminUsers({ search: this.calendarUserSearch || undefined, size: 100 }); this.calendarUsers = response.items || [] } catch (error) { this.message = this.errorText(error) } finally { this.calendarUsersLoading = false }
    },
    async openCalendarForUser(user) { this.closeUserDetail(); this.activeTab = 'calendar'; this.selectedCalendarUser = user; this.calendarForm.visible = false; await this.loadCalendarUsers(); await this.loadCalendars(); this.syncAutoRefresh() },
    async selectCalendarUser(user) { this.selectedCalendarUser = user; this.cancelCalendarEdit(); await this.loadCalendars() },
    async loadCalendars() {
      if (!this.selectedCalendarUser) return
      this.calendarLoading = true
      try { this.calendars = (await getAdminCalendars(this.selectedCalendarUser.id)).items || [] } catch (error) { this.message = this.errorText(error) } finally { this.calendarLoading = false }
    },
    startNewCalendar() { this.calendarForm = { visible: true, id: null, title: '', note: '', start_date: '', end_date: '', status: 'draft', version_number: 1, entries: [] } },
    async prepareCalendarEdit(calendar) {
      try {
        let target = calendar
        if (calendar.status !== 'draft') { target = await createAdminCalendarDraft(calendar.id); this.calendars = [target, ...this.calendars.filter(item => item.id !== target.id)]; this.message = `已创建 v${target.version_number} 草稿` }
        this.editCalendar(target)
      } catch (error) { this.message = this.errorText(error) }
    },
    editCalendar(calendar) {
      this.calendarForm = { visible: true, id: calendar.id, title: calendar.title, note: '', start_date: calendar.start_date || '', end_date: calendar.end_date || '', status: calendar.status, version_number: calendar.version_number || 1, entries: (calendar.entries || []).map(entry => ({ ...createEntry(entry.entry_date), ...entry, _key: `entry-${entry.id || Date.now()}-${Math.random()}`, suitableText: (entry.suitable || []).join('，'), unsuitableText: (entry.unsuitable || []).join('，') })) }
    },
    cancelCalendarEdit() { this.calendarForm = { visible: false, id: null, title: '', note: '', start_date: '', end_date: '', status: '', version_number: 1, entries: [] } },
    addCalendarEntry() { const last = this.calendarForm.entries[this.calendarForm.entries.length - 1]?.entry_date; let next = this.calendarForm.start_date || todayKey(); if (last) { const date = new Date(`${last}T00:00:00`); date.setDate(date.getDate() + 1); next = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}` } this.calendarForm.entries.push(createEntry(next)) },
    removeCalendarEntry(index) { this.calendarForm.entries.splice(index, 1) },
    splitEntryText(value) { return (value || '').split(/[,，、\n]/).map(item => item.trim()).filter(Boolean) },
    validateCalendarEntries(entries, startDate, endDate) {
      if (startDate && endDate && startDate > endDate) throw new Error('日历开始日期不能晚于结束日期')
      if (entries.some(entry => !entry.entry_date)) throw new Error('每个日历条目都需要填写日期')
      const dates = entries.map(entry => entry.entry_date)
      if (new Set(dates).size !== dates.length) throw new Error('日历条目日期不能重复')
      if (startDate && dates.some(entryDate => entryDate < startDate)) throw new Error('存在早于日历开始日期的条目')
      if (endDate && dates.some(entryDate => entryDate > endDate)) throw new Error('存在晚于日历结束日期的条目')
    },
    async saveCalendar() {
      if (!this.selectedCalendarUser) return
      const entries = this.calendarForm.entries.map(({ _key, id, suitableText, unsuitableText, ...entry }) => ({ ...entry, suitable: this.splitEntryText(suitableText), unsuitable: this.splitEntryText(unsuitableText) }))
      const dates = entries.map(entry => entry.entry_date).filter(Boolean).sort()
      const payload = { title: this.calendarForm.title, start_date: this.calendarForm.start_date || dates[0] || null, end_date: this.calendarForm.end_date || dates[dates.length - 1] || null, entries }
      try {
        if (!payload.title.trim()) throw new Error('请填写日历标题')
        this.validateCalendarEntries(entries, payload.start_date, payload.end_date)
      } catch (error) {
        this.message = error.message
        return
      }
      this.calendarSaving = true
      try { if (this.calendarForm.id) await updateAdminCalendar(this.calendarForm.id, payload); else await createAdminCalendar(this.selectedCalendarUser.id, payload); this.message = '日历草稿已保存'; this.cancelCalendarEdit(); await this.loadCalendars() } catch (error) { this.message = this.errorText(error) } finally { this.calendarSaving = false }
    },
    async publishCalendar(calendar) { if (!window.confirm(`确认发布“${calendar.title}” v${calendar.version_number}？发布后用户端将看到这版内容。`)) return; try { await publishAdminCalendar(calendar.id); this.message = '日历已发布'; await this.loadCalendars() } catch (error) { this.message = this.errorText(error) } },
    async archiveCalendar(calendar) { if (!window.confirm(`确认归档“${calendar.title}” v${calendar.version_number}？`)) return; try { await archiveAdminCalendar(calendar.id); this.message = '日历已归档'; await this.loadCalendars() } catch (error) { this.message = this.errorText(error) } },
    toggleImportPanel() { this.showCalendarImport = !this.showCalendarImport },
    async importCalendarJson() {
      try { const parsed = JSON.parse(this.calendarImportJson); const entries = Array.isArray(parsed) ? parsed : parsed.entries; if (!this.selectedCalendarUser) throw new Error('请先选择用户'); if (!Array.isArray(entries) || !entries.length) throw new Error('导入内容中没有有效条目'); const startDate = Array.isArray(parsed) ? null : (parsed.start_date || null); const endDate = Array.isArray(parsed) ? null : (parsed.end_date || null); this.validateCalendarEntries(entries, startDate, endDate); await importAdminCalendar({ user_id: this.selectedCalendarUser.id, title: Array.isArray(parsed) ? `${this.selectedCalendarUser.name} 的导入日历` : (parsed.title || `${this.selectedCalendarUser.name} 的导入日历`), start_date: startDate, end_date: endDate, entries }); this.calendarImportJson = ''; this.showCalendarImport = false; this.message = 'JSON 日历已导入为草稿'; await this.loadCalendars() } catch (error) { this.message = error instanceof SyntaxError ? 'JSON 格式不正确' : (error.message || this.errorText(error)) }
    },
    exportCalendarJson(calendar) { const blob = new Blob([JSON.stringify({ title: calendar.title, start_date: calendar.start_date, end_date: calendar.end_date, entries: calendar.entries || [] }, null, 2)], { type: 'application/json;charset=utf-8' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `calendar-${calendar.user_id}-v${calendar.version_number}.json`; anchor.click(); URL.revokeObjectURL(url) },
    async loadReports() { this.reportsLoading = true; try { this.reports = await getAdminReports({ ...this.cleanParams(this.reportFilters), page: this.reportPage, size: this.reportPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.reportsLoading = false } },
    async searchReports() { this.reportPage = 1; await this.loadReports() },
    async changeReportPage(offset) { const next = this.reportPage + offset; if (next < 1 || next > this.pageCount(this.reports.total, this.reportPageSize)) return; this.reportPage = next; await this.loadReports() },
     async loadReportTasks() { this.tasksLoading = true; try { this.reportTasks = await getAdminReportTasks({ ...this.cleanParams(this.taskFilters), page: this.taskPage, size: this.taskPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.tasksLoading = false } },
     async searchReportTasks() { this.taskPage = 1; await this.loadReportTasks() },
     async changeTaskPage(offset) { const next = this.taskPage + offset; if (next < 1 || next > this.pageCount(this.reportTasks.total, this.taskPageSize)) return; this.taskPage = next; await this.loadReportTasks() },
     canRetryTask(task) { return task.status === 'failed' && task.has_input_snapshot && !task.has_retry && task.retry_count < this.reportRetryLimit },
    async retryTask(task) { if (!window.confirm('确认重新生成这份报告？这会再次调用 AI 服务。')) return; try { await retryAdminReportTask(task.task_id); this.message = '重试任务已排队'; await this.loadReportTasks() } catch (error) { this.message = this.errorText(error) } },
    async openReport(report) { try { this.reportDetail = await getAdminReport(report.id) } catch (error) { this.message = this.errorText(error) } },
     async setLogSection(section) { this.logSection = section; if (section === 'audit') await this.loadAuditLogs(); else if (section === 'behavior') await this.loadDecisionLogs(); else await this.loadReportTasks() },
     async loadAuditLogs() { this.auditLoading = true; try { this.auditLogs = await getAdminAuditLogs({ ...this.cleanParams(this.logFilters), page: this.logPage, size: this.logPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.auditLoading = false } },
    resetLogFilters() { this.logFilters = { search: '', action: '', resource_type: '', actor_user_id: '', target_user_id: '', date_from: '', date_to: '' }; this.logPage = 1; this.loadAuditLogs() },
    async changeLogPage(offset) { const next = this.logPage + offset; if (next < 1 || next > this.pageCount(this.auditLogs.total, this.logPageSize)) return; this.logPage = next; await this.loadAuditLogs() },
     async loadDecisionLogs() { this.decisionLoading = true; try { this.decisionLogs = await getAdminDecisionLogs({ ...this.cleanParams(this.behaviorFilters), page: this.decisionPage, size: this.decisionPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.decisionLoading = false } },
    async searchDecisionLogs() { this.decisionPage = 1; await this.loadDecisionLogs() },
    async changeDecisionPage(offset) { const next = this.decisionPage + offset; if (next < 1 || next > this.pageCount(this.decisionLogs.total, this.decisionPageSize)) return; this.decisionPage = next; await this.loadDecisionLogs() },
    openLogDetail(log) { this.logDetail = log },
    async inviteStaff() { try { const response = await createStaffInvite(this.inviteForm.phone, this.inviteForm.role); this.inviteToken = response.token; this.message = '邀请链接已生成，请安全发送给对方'; await this.loadStaff() } catch (error) { this.message = this.errorText(error) } },
    async saveCourseProgress(course) { if (!this.detailUser) return; try { await updateAdminUserCourseProgress(this.detailUser.id, course.course_id, { completed_lessons: Math.min(course.completed_lessons, course.total_lessons), progress_percentage: Math.max(0, Math.min(100, Number(course.progress) || 0)), last_lesson_id: course.last_lesson_id || null }); this.message = '课程进度已保存'; await this.setUserPanelTab('courses') } catch (error) { this.message = this.errorText(error) } },
    async exportResource(resource) { try { let params = {}; if (resource === 'users') params = this.cleanParams(this.userFilters); if (resource === 'bookings') params = this.cleanParams(this.bookingFilters); if (resource === 'reports') params = this.cleanParams(this.reportFilters); if (resource === 'audit-logs') params = this.cleanParams(this.logFilters); if (resource === 'decision-logs') params = this.cleanParams(this.behaviorFilters); await downloadAdminExport(resource, params); this.message = '导出已开始' } catch (error) { this.message = this.errorText(error) } },
    cleanParams(params) { return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined)) },
    pageCount(total, size) { return Math.max(1, Math.ceil((total || 0) / size)) },
    distributionTotal(items) { return (items || []).reduce((sum, item) => sum + item.value, 0) },
    distributionWidth(item, items) { const max = Math.max(1, ...(items || []).map(value => value.value)); return (item.value / max) * 100 },
    formatDate(value) { return value ? new Date(`${String(value).slice(0, 10)}T00:00:00`).toLocaleDateString('zh-CN') : '—' },
    formatShortDate(value) { return value ? `${String(value).slice(5, 7)}/${String(value).slice(8, 10)}` : '—' },
    formatDateTime(value) { return value ? new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—' },
    statusText(value) { return { pending: '待确认', confirmed: '已确认', completed: '已完成', cancelled: '已取消' }[value] || value || '—' },
    reportStatusText(value) { return { processing: '生成中', completed: '已完成', failed: '失败' }[value] || value || '—' },
    calendarStatusText(value) { return { draft: '草稿', published: '已发布', archived: '已归档' }[value] || value || '—' },
    decisionStatusText(value) { return { done: '已完成', doing: '进行中', skipped: '已跳过' }[value] || value || '—' },
    roleText(value) { return { user: '用户', consultant: '咨询师', admin: '管理员' }[value] || value || '—' },
    resourceLabel(value) { return { user: '用户', booking: '预约', calendar: '日历', report: '报告', report_task: '报告任务', decision_log: '行动记录', user_course: '课程进度', staff_invite: '成员邀请', auth: '认证' }[value] || value || '—' },
    actionLabel(value) { return { 'auth.register': '注册账号', 'auth.login.success': '登录成功', 'auth.login.failure': '登录失败', 'auth.logout': '退出登录', 'user.profile.update': '更新资料', 'user.profile.update.admin': '管理员更新资料', 'user.status.update': '更新账号状态', 'user.role.update': '更新角色', 'user.password.reset': '重置密码', 'user.password.change': '修改密码', 'booking.create': '创建预约', 'booking.cancel': '取消预约', 'booking.update': '更新预约', 'booking.staff.update': '咨询师更新预约', 'calendar.create': '创建日历', 'calendar.import': '导入日历', 'calendar.update': '更新日历', 'calendar.revision.create': '创建日历版本', 'calendar.publish': '发布日历', 'calendar.archive': '归档日历', 'decision_log.create': '新增行动记录', 'decision_log.delete': '删除行动记录', 'course.progress.update': '更新课程进度', 'report.task.create': '创建报告任务', 'report.task.completed': '报告生成完成', 'report.task.failed': '报告生成失败', 'report.task.retry': '重试报告任务', 'report.delete': '删除报告', 'staff.invite.create': '创建成员邀请', 'staff.invite.accept': '接受成员邀请' }[value] || value || '未知操作' },
    prettyJson(value) { if (value === null || value === undefined || value === '') return '—'; if (typeof value === 'string') { try { return JSON.stringify(JSON.parse(value), null, 2) } catch { return value } } return JSON.stringify(value, null, 2) },
    errorText(error) { return error.response?.data?.detail || error.message || '请求失败，请稍后重试' }
  }
}
</script>

<style scoped>
.admin-shell { min-height: 100vh; background: radial-gradient(circle at 84% 4%, rgba(217, 186, 98, .16), transparent 22%), linear-gradient(135deg, #f7f0e6 0%, #fffaf0 48%, #ead9bf 100%); }
.admin-main { width: min(1440px, calc(100% - 48px)); margin: 0 auto; padding: 58px 0 100px; }
.admin-hero { display: flex; align-items: end; justify-content: space-between; gap: 28px; padding: 30px 0 32px; border-bottom: 1px solid rgba(80, 54, 32, .14); }
.admin-hero h1 { margin: 8px 0 12px; color: #30241b; font-size: clamp(38px, 6vw, 72px); line-height: .98; letter-spacing: -.045em; }
.hero-caption, .view-heading p, .dashboard-toolbar p { color: #786a5f; line-height: 1.7; }
.hero-actions { display: flex; align-items: center; gap: 14px; padding-bottom: 3px; }
.sync-state { display: inline-flex; align-items: center; gap: 8px; color: #786a5f; font-family: Manrope, "PingFang SC", sans-serif; font-size: 11px; letter-spacing: .04em; white-space: nowrap; }
.sync-state i { width: 7px; height: 7px; border-radius: 50%; background: #6f9f93; box-shadow: 0 0 0 4px rgba(111, 159, 147, .14); }
.sync-state i.live { animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .35; transform: scale(.72); } }
.admin-tabs { display: flex; flex-wrap: wrap; gap: 8px; padding: 20px 0 28px; }
.admin-tab { display: inline-flex; align-items: center; gap: 9px; border: 1px solid rgba(80, 54, 32, .14); border-radius: 999px; padding: 10px 15px; color: #786a5f; background: rgba(255, 250, 240, .56); cursor: pointer; transition: .2s ease; }
.admin-tab:hover { border-color: rgba(184, 92, 80, .5); color: #9e3f35; transform: translateY(-1px); }
.admin-tab.active { border-color: #b85c50; background: #fff0df; color: #8f352f; box-shadow: 0 8px 22px -17px rgba(158, 63, 53, .9); }
.tab-index, .eyebrow, .action-code, .mono-text { font-family: Manrope, "PingFang SC", sans-serif; }
.tab-index { font-size: 10px; font-weight: 800; letter-spacing: .08em; opacity: .65; }
.eyebrow { margin-bottom: 7px; color: #996419; font-size: 10px; font-weight: 900; letter-spacing: .19em; text-transform: uppercase; }
.console-message { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 0 0 20px; border-left: 3px solid #b85c50; border-radius: 8px; padding: 10px 13px; background: rgba(255, 240, 223, .8); color: #8f352f; font-size: 13px; }
.console-message button { color: inherit; font-size: 20px; line-height: 1; cursor: pointer; }
.compact-button { min-height: 38px; padding: 0 15px; font-size: 12px; }
.dashboard-toolbar, .view-heading, .panel-heading, .table-meta, .pagination, .calendar-card-top, .editor-banner, .entry-toolbar, .preview-strip { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.dashboard-toolbar { margin-bottom: 22px; }
.dashboard-toolbar h2, .view-heading h2 { margin: 0 0 5px; color: #30241b; font-size: clamp(26px, 3vw, 38px); letter-spacing: -.03em; }
.toolbar-controls { display: flex; align-items: center; gap: 13px; }
.range-switch, .section-switch { display: inline-flex; border: 1px solid rgba(80, 54, 32, .14); border-radius: 999px; padding: 3px; background: rgba(255, 250, 240, .64); }
.range-switch button, .section-switch button { border-radius: 999px; padding: 8px 13px; color: #786a5f; cursor: pointer; font-size: 12px; }
.range-switch button.active, .section-switch button.active { background: #3b2d24; color: #fffaf0; }
.auto-refresh { display: inline-flex; align-items: center; gap: 6px; color: #786a5f; font-size: 11px; white-space: nowrap; }
.auto-refresh input { accent-color: #b85c50; }
.metric-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 11px; margin-bottom: 18px; }
.metric-card, .dashboard-panel, .table-panel, .panel-surface { border: 1px solid rgba(80, 54, 32, .13); background: linear-gradient(145deg, rgba(255, 252, 245, .93), rgba(255, 247, 231, .72)); box-shadow: 0 18px 44px -35px rgba(84, 48, 25, .62), inset 0 1px rgba(255, 255, 255, .74); backdrop-filter: blur(14px); }
.metric-card { position: relative; min-height: 142px; overflow: hidden; border-radius: 15px; padding: 17px; }
.metric-card::after { content: ""; position: absolute; right: -22px; bottom: -35px; width: 110px; height: 110px; border: 1px solid currentColor; border-radius: 50%; opacity: .13; }
.metric-card.metric-cinnabar { color: #b85c50; }.metric-card.metric-gold { color: #9a701c; }.metric-card.metric-jade { color: #4f8875; }.metric-card.metric-ink { color: #59483d; }
.metric-top { display: flex; justify-content: space-between; color: #786a5f; font-size: 11px; }.metric-top b { color: currentColor; font-family: Manrope, sans-serif; font-size: 10px; letter-spacing: .08em; }
.metric-card > strong { display: block; margin: 17px 0 5px; color: #30241b; font-family: Manrope, sans-serif; font-size: 31px; letter-spacing: -.06em; }.metric-card small { color: #786a5f; font-size: 10px; line-height: 1.5; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(300px, .8fr); gap: 18px; }.dashboard-panel { border-radius: 18px; padding: 22px; }.trend-panel, .distribution-panel { min-width: 0; }.trend-panel { grid-row: span 1; }.panel-heading { align-items: flex-start; }.panel-heading h3 { margin: 0; color: #3b2d24; font-size: 18px; }.panel-note, .alert-count, .panel-heading > span { color: #9a8878; font-family: Manrope, sans-serif; font-size: 10px; }.alert-count { display: inline-flex; width: 27px; height: 27px; align-items: center; justify-content: center; border-radius: 50%; background: #fff0df; color: #9e3f35; font-weight: 900; }
.trend-legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 18px 0 4px; color: #786a5f; font-size: 11px; }.trend-legend span { display: inline-flex; align-items: center; gap: 6px; }.trend-legend i { width: 7px; height: 7px; border-radius: 50%; }.trend-chart { min-height: 250px; }.trend-chart svg { width: 100%; height: 250px; overflow: visible; }.chart-grid-line { stroke: rgba(80, 54, 32, .09); stroke-dasharray: 2 5; }.chart-tick { stroke: rgba(80, 54, 32, .2); }.chart-label { fill: #9a8878; font-family: Manrope, sans-serif; font-size: 10px; }.trend-line { fill: none; stroke-width: 2.8; stroke-linecap: round; stroke-linejoin: round; }
.alert-panel { min-height: 330px; }.alert-list { display: grid; gap: 8px; margin-top: 16px; }.alert-item { display: grid; grid-template-columns: 10px 1fr auto; align-items: center; gap: 10px; width: 100%; border: 1px solid rgba(80, 54, 32, .1); border-radius: 11px; padding: 12px; background: rgba(255, 250, 240, .6); text-align: left; cursor: pointer; }.alert-item:hover { border-color: rgba(184, 92, 80, .4); transform: translateX(2px); }.alert-item strong, .alert-item small { display: block; }.alert-item strong { color: #3b2d24; font-size: 13px; }.alert-item small { margin-top: 4px; color: #9a8878; font-size: 10px; }.alert-item > b { color: #b85c50; }.alert-mark { width: 8px; height: 8px; border-radius: 50%; }.alert-warning { background: #c69b42; box-shadow: 0 0 0 4px rgba(198, 155, 66, .14); }.alert-danger { background: #b85c50; box-shadow: 0 0 0 4px rgba(184, 92, 80, .13); }.alert-info { background: #6f9f93; box-shadow: 0 0 0 4px rgba(111, 159, 147, .13); }.quiet-state, .editor-empty { display: grid; place-items: center; gap: 8px; min-height: 210px; color: #9a8878; text-align: center; }.quiet-state span, .editor-empty span { color: #c69b42; font-size: 28px; }.quiet-state p, .editor-empty p { font-size: 12px; }
.distribution-panel { grid-column: 1 / -1; }.distribution-columns { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px; margin-top: 20px; }.distribution-group { min-width: 0; }.distribution-title { display: flex; justify-content: space-between; margin-bottom: 11px; color: #3b2d24; font-size: 12px; font-weight: 800; }.distribution-title small { color: #9a8878; font-family: Manrope, sans-serif; font-size: 10px; }.distribution-row { margin: 9px 0; }.distribution-row > div { display: flex; justify-content: space-between; margin-bottom: 5px; color: #786a5f; font-size: 11px; }.distribution-row b { color: #3b2d24; font-family: Manrope, sans-serif; }.distribution-track { display: block; height: 5px; border-radius: 999px; background: rgba(80, 54, 32, .1); overflow: hidden; }.distribution-track i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #b85c50, #d9ba62); }.activity-panel { min-height: 275px; }.panel-link { color: #9e3f35; font-size: 11px; font-weight: 800; cursor: pointer; }.activity-list { display: grid; gap: 0; margin-top: 12px; }.activity-item { display: grid; grid-template-columns: 10px 1fr auto; align-items: start; gap: 10px; padding: 11px 0; border-bottom: 1px solid rgba(80, 54, 32, .08); }.activity-item:last-child { border-bottom: 0; }.activity-dot { width: 7px; height: 7px; margin-top: 5px; border-radius: 50%; background: #b85c50; box-shadow: 0 0 0 4px rgba(184, 92, 80, .12); }.activity-item strong { color: #3b2d24; font-size: 12px; }.activity-item p, .activity-item time { margin-top: 3px; color: #9a8878; font-size: 10px; }.activity-item time { white-space: nowrap; }.activity-list.compact .activity-item { grid-template-columns: 10px 1fr auto; }
.dashboard-skeleton { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }.skeleton-block { height: 150px; border-radius: 16px; background: linear-gradient(100deg, rgba(255, 255, 255, .34), rgba(234, 217, 191, .6), rgba(255, 255, 255, .34)); background-size: 200% 100%; animation: shimmer 1.5s infinite; } @keyframes shimmer { to { background-position: -200% 0; } }
.content-view { display: grid; gap: 20px; }.view-heading { align-items: end; }.view-heading h2 { margin-bottom: 4px; }.view-heading > p { max-width: 640px; }.filter-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 13px; border: 1px solid rgba(80, 54, 32, .11); border-radius: 14px; background: rgba(255, 250, 240, .52); }.filter-bar input, .filter-bar select, .directory-search input, .calendar-editor-form input, .calendar-editor-form select, .calendar-editor-form textarea, .stack-form input, .stack-form select, .stack-form textarea { min-width: 0; border: 1px solid rgba(80, 54, 32, .15); border-radius: 8px; background: rgba(255, 252, 245, .82); padding: 10px 11px; color: #3b2d24; font: inherit; }.filter-bar > input { flex: 1 1 180px; }.filter-bar > select { flex: 0 1 150px; }.date-filter { display: inline-flex; align-items: center; gap: 5px; border: 1px solid rgba(80, 54, 32, .12); border-radius: 8px; padding-left: 8px; background: rgba(255, 252, 245, .7); }.date-filter span { color: #9a8878; font-size: 10px; white-space: nowrap; }.date-filter input { border: 0; padding-left: 2px; background: transparent; }.filter-reset { padding: 8px; color: #9e3f35; font-size: 12px; cursor: pointer; }.table-panel { border-radius: 17px; overflow: hidden; }.list-loading { display: grid; gap: 8px; border: 1px solid rgba(80, 54, 32, .1); border-radius: 17px; padding: 17px; background: rgba(255, 250, 240, .6); }.list-loading i { display: block; height: 44px; border-radius: 9px; background: linear-gradient(90deg, rgba(234, 217, 191, .34), rgba(255, 240, 223, .8), rgba(234, 217, 191, .34)); background-size: 220% 100%; animation: skeleton-wave 1.35s ease-in-out infinite; }.list-loading i:nth-child(2) { opacity: .8; }.list-loading i:nth-child(3) { opacity: .6; }.list-loading i:nth-child(4) { opacity: .45; }.list-loading[aria-label*="日历"] i { height: 70px; }.list-loading[aria-label*="日志"] i { height: 38px; } @keyframes skeleton-wave { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }.table-meta, .pagination { min-height: 53px; padding: 0 18px; color: #786a5f; font-size: 11px; }.table-meta span:last-child { color: #9a8878; }.admin-table-wrap { overflow-x: auto; }.admin-table { width: 100%; min-width: 920px; border-collapse: collapse; }.admin-table th, .admin-table td { padding: 13px 15px; border-top: 1px solid rgba(80, 54, 32, .09); text-align: left; vertical-align: middle; }.admin-table th { color: #9a701c; font-family: Manrope, "PingFang SC", sans-serif; font-size: 10px; letter-spacing: .12em; text-transform: uppercase; }.admin-table td { color: #4d3e33; font-size: 12px; }.admin-table td small, .person-cell small, .drawer-list-item small, .team-row small, .course-admin-row small { display: block; margin-top: 4px; color: #9a8878; font-size: 10px; }.admin-table tbody tr { transition: background .15s ease; }.admin-table tbody tr:hover { background: rgba(255, 240, 223, .54); }.person-cell { display: inline-flex; align-items: center; gap: 10px; }.person-cell > span:last-child { min-width: 0; }.person-cell strong { color: #30241b; }.avatar-mark { display: inline-flex; flex: 0 0 auto; width: 31px; height: 31px; align-items: center; justify-content: center; border: 1px solid rgba(184, 92, 80, .3); border-radius: 50%; background: #fff0df; color: #9e3f35; font-weight: 900; }.avatar-mark.small { width: 27px; height: 27px; font-size: 12px; }.avatar-mark.large { width: 46px; height: 46px; font-size: 19px; }.admin-table select { max-width: 110px; border: 1px solid rgba(80, 54, 32, .14); border-radius: 7px; padding: 7px; background: #fffaf0; color: #4d3e33; }.mini-stats { display: flex; gap: 6px; color: #786a5f; font-family: Manrope, "PingFang SC", sans-serif; font-size: 10px; }.status-badge { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 8px; background: #eee4d5; color: #786a5f; font-size: 10px; white-space: nowrap; }.status-badge.success, .status-badge.booking-completed, .status-badge.calendar-published, .status-badge.report-completed, .status-badge.task-completed, .status-badge.decision-done { background: #e1f0dc; color: #39724e; }.status-badge.muted, .status-badge.booking-cancelled, .status-badge.calendar-archived, .status-badge.report-failed, .status-badge.task-failed, .status-badge.decision-skipped { background: #f2dddd; color: #8f352f; }.status-badge.booking-pending, .status-badge.calendar-draft, .status-badge.decision-doing { background: #fff0c9; color: #89621a; }.status-badge.booking-confirmed, .status-badge.report-processing, .status-badge.task-processing { background: #dcebe8; color: #39776b; }.muted-text { color: #9a8878 !important; }.row-actions { display: flex; flex-wrap: wrap; gap: 9px; }.row-actions button, .row-open, .detail-link { border: 0; background: transparent; color: #9e3f35; cursor: pointer; font-size: 11px; font-weight: 800; }.row-actions button:hover, .row-open:hover, .detail-link:hover { text-decoration: underline; }.danger-action { color: #b85c50 !important; }.empty-cell { padding: 42px 16px !important; color: #9a8878 !important; text-align: center !important; }.pagination > div { display: flex; gap: 8px; }.pagination .secondary-button:disabled { cursor: not-allowed; opacity: .42; }
.booking-table tbody tr { cursor: pointer; }.booking-table tbody tr:hover { background: rgba(255, 240, 223, .54); }.booking-table td:first-child strong { color: #30241b; }.progress-cell { display: grid; grid-template-columns: 38px minmax(70px, 100px); align-items: center; gap: 7px; color: #4f8875; font-family: Manrope, sans-serif; font-size: 10px; }.progress-cell i { display: block; height: 5px; border-radius: 999px; background: #e4ddd1; overflow: hidden; }.progress-cell b { display: block; height: 100%; border-radius: inherit; background: #6f9f93; }.error-cell { max-width: 200px; color: #9e3f35 !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }.action-code { color: #9e3f35; font-size: 11px; font-weight: 800; }.audit-table td { max-width: 220px; }.content-cell { max-width: 300px; white-space: normal; }
.import-panel { display: grid; grid-template-columns: minmax(180px, .7fr) minmax(0, 1.5fr) auto; align-items: center; gap: 14px; border: 1px dashed rgba(184, 92, 80, .35); border-radius: 14px; padding: 14px; background: rgba(255, 240, 223, .5); }.import-panel strong { color: #8f352f; }.import-panel p { margin-top: 4px; color: #9a8878; font-size: 11px; line-height: 1.5; }.import-panel textarea { width: 100%; resize: vertical; font-family: Consolas, monospace; font-size: 11px; }.calendar-admin-grid { display: grid; grid-template-columns: 290px minmax(0, 1fr); gap: 18px; align-items: start; }.panel-surface { border-radius: 17px; padding: 20px; }.user-directory { min-height: 620px; }.directory-search { display: flex; gap: 6px; margin: 17px 0 12px; }.directory-search input { width: 100%; }.directory-search button { width: 38px; border: 1px solid rgba(80, 54, 32, .14); border-radius: 8px; color: #9e3f35; cursor: pointer; }.directory-list { display: grid; gap: 7px; max-height: 690px; overflow-y: auto; }.directory-list button { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 9px; border: 1px solid rgba(80, 54, 32, .1); border-radius: 10px; padding: 9px; background: rgba(255, 250, 240, .66); text-align: left; cursor: pointer; }.directory-list button.selected { border-color: #b85c50; background: #fff0df; }.directory-list button strong { display: block; color: #3b2d24; font-size: 12px; }.directory-list button small { display: block; margin-top: 3px; color: #9a8878; font-size: 9px; }.directory-list button > b { color: #b85c50; }.calendar-editor { min-width: 0; min-height: 620px; }.calendar-list { display: grid; gap: 8px; margin-top: 17px; }.calendar-card { border: 1px solid rgba(80, 54, 32, .1); border-radius: 11px; padding: 12px; background: rgba(255, 250, 240, .52); }.calendar-card.selected { border-color: rgba(184, 92, 80, .56); background: rgba(255, 240, 223, .55); }.calendar-card-top { align-items: start; }.calendar-card-top strong { display: block; color: #3b2d24; font-size: 13px; }.calendar-card-top small { display: block; margin-top: 5px; color: #9a8878; font-size: 10px; }.calendar-card-preview { display: flex; flex-wrap: wrap; gap: 6px; margin: 11px 0; }.calendar-card-preview span { border-radius: 999px; padding: 4px 7px; background: rgba(234, 217, 191, .55); color: #786a5f; font-size: 9px; }.calendar-card .row-actions { justify-content: end; }.calendar-editor-form { margin-top: 18px; border-top: 1px solid rgba(80, 54, 32, .11); padding-top: 18px; }.editor-banner { margin-bottom: 14px; color: #8f352f; font-size: 12px; font-weight: 900; }.editor-banner span:last-child { color: #9a8878; font-size: 10px; font-weight: 400; }.form-grid { display: grid; gap: 10px; }.form-grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }.form-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }.form-grid label, .stack-form label, .calendar-editor-form > label { display: grid; gap: 5px; color: #786a5f; font-size: 11px; font-weight: 700; }.form-grid input, .form-grid select { width: 100%; }.span-two { grid-column: span 2; }.entry-toolbar { margin: 22px 0 11px; }.entry-toolbar strong, .entry-toolbar small { display: block; }.entry-toolbar strong { color: #3b2d24; font-size: 14px; }.entry-toolbar small { margin-top: 3px; color: #9a8878; font-size: 10px; font-weight: 400; }.entry-list { display: grid; gap: 10px; }.entry-editor { display: grid; gap: 9px; border: 1px solid rgba(80, 54, 32, .12); border-radius: 12px; padding: 12px; background: rgba(255, 250, 240, .54); }.entry-editor-head { display: grid; grid-template-columns: 58px 1fr auto; align-items: end; gap: 9px; }.entry-editor-head > span { align-self: center; color: #b85c50; font-family: Manrope, sans-serif; font-size: 10px; font-weight: 900; }.entry-editor-head label { display: grid; gap: 4px; color: #9a8878; font-size: 10px; }.entry-editor-head button { align-self: center; color: #b85c50; font-size: 22px; cursor: pointer; }.calendar-editor-form textarea { resize: vertical; line-height: 1.5; }.preview-strip { flex-wrap: wrap; align-items: end; margin-top: 16px; border: 1px solid rgba(111, 159, 147, .22); border-radius: 10px; padding: 11px; background: rgba(225, 240, 220, .45); color: #5c786c; font-size: 10px; }.preview-strip strong { display: block; color: #39724e; font-size: 13px; }.preview-strip .eyebrow { margin-bottom: 4px; color: #5c786c; font-size: 8px; }.editor-actions { justify-content: end; margin-top: 16px; }.entry-empty { padding: 25px !important; }.section-switch { justify-self: start; }.section-switch button { min-width: 100px; }.staff-grid { display: grid; grid-template-columns: minmax(260px, .7fr) minmax(0, 1.3fr); gap: 18px; }.invite-card h3, .team-card h3 { margin: 0; color: #3b2d24; font-size: 20px; }.stack-form { display: grid; gap: 13px; margin-top: 18px; }.stack-form .primary-button { justify-self: start; }.invite-result { display: grid; gap: 8px; margin-top: 22px; border: 1px dashed rgba(184, 92, 80, .45); border-radius: 10px; padding: 14px; background: #fff4e9; }.invite-result span { color: #9a8878; font-size: 10px; }.invite-result code { color: #8f352f; overflow-wrap: anywhere; }.invite-result a { color: #8f352f; font-size: 12px; font-weight: 800; }.team-list { display: grid; gap: 8px; margin-top: 18px; }.team-row { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; border-bottom: 1px solid rgba(80, 54, 32, .08); padding: 9px 0; }.team-row strong { color: #3b2d24; font-size: 13px; }.course-admin-list, .decision-list { display: grid; gap: 9px; }.course-admin-row, .decision-list > div { display: flex; align-items: center; justify-content: space-between; gap: 14px; border-bottom: 1px solid rgba(80, 54, 32, .09); padding: 11px 0; }.course-admin-row strong, .decision-list strong { color: #3b2d24; font-size: 12px; }.course-progress-editor { display: flex; align-items: center; gap: 3px; }.course-progress-editor input { width: 55px; padding: 7px; }.course-progress-editor span { color: #9a8878; font-size: 11px; }.course-progress-editor button { color: #9e3f35; font-size: 11px; font-weight: 800; cursor: pointer; }.full-button { width: 100%; margin-top: 17px; }.report-meta-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }.report-meta-grid > div { border-radius: 9px; padding: 10px; background: rgba(234, 217, 191, .35); }.report-meta-grid span, .report-meta-grid strong { display: block; }.report-meta-grid span, .detail-facts span { color: #9a8878; font-size: 10px; }.report-meta-grid strong { margin-top: 5px; color: #3b2d24; font-size: 12px; }.report-block { margin-top: 20px; border-top: 1px solid rgba(80, 54, 32, .1); padding-top: 16px; }.report-block h3 { margin-bottom: 9px; color: #3b2d24; font-size: 14px; }.report-block p { color: #786a5f; font-size: 13px; line-height: 1.8; }.report-block pre, .json-view pre { max-height: 300px; overflow: auto; border-radius: 9px; padding: 12px; background: #342921; color: #f4e8d6; font-family: Consolas, monospace; font-size: 11px; line-height: 1.65; white-space: pre-wrap; }.detail-facts { display: grid; gap: 10px; margin: 5px 0 17px; }.detail-facts p { display: grid; grid-template-columns: 76px 1fr; gap: 10px; margin: 0; }.detail-facts strong { color: #3b2d24; font-size: 12px; font-weight: 700; word-break: break-word; }.detail-facts strong small { display: block; margin-top: 3px; color: #9a8878; font-size: 10px; font-weight: 400; }.json-view { margin-top: 20px; }.json-view > span { display: block; margin-bottom: 8px; color: #9a8878; font-size: 10px; }
.course-panel { grid-column: 1 / -1; }.course-stats-list { display: grid; gap: 0; margin-top: 12px; }.course-stat-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; border-bottom: 1px solid rgba(80, 54, 32, .08); padding: 12px 0; }.course-stat-row:last-child { border-bottom: 0; }.course-stat-row strong, .course-stat-row small { display: block; }.course-stat-row strong { color: #3b2d24; font-size: 13px; }.course-stat-row small { margin-top: 4px; color: #9a8878; font-size: 10px; }.course-stat-numbers { display: grid; grid-template-columns: auto auto; align-items: baseline; column-gap: 5px; min-width: 125px; text-align: right; }.course-stat-numbers b { color: #39724e; font-family: Manrope, sans-serif; font-size: 18px; }.course-stat-numbers span { color: #9a8878; font-size: 10px; }.course-stat-numbers small { grid-column: 1 / -1; }
.drawer-layer { position: fixed; z-index: 1400; inset: 0; display: flex; justify-content: end; background: rgba(47, 36, 27, .24); backdrop-filter: blur(4px); }.drawer { width: min(620px, 100%); height: 100%; overflow-y: auto; border-left: 1px solid rgba(80, 54, 32, .15); background: #fbf4e9; box-shadow: -30px 0 80px -50px rgba(47, 36, 27, .75); animation: drawer-in .25s ease-out; }.user-drawer { width: min(720px, 100%); }.drawer-header { display: flex; align-items: start; justify-content: space-between; gap: 18px; padding: 28px 28px 21px; border-bottom: 1px solid rgba(80, 54, 32, .12); background: linear-gradient(135deg, rgba(255, 250, 240, .94), rgba(255, 240, 223, .7)); }.drawer-header .person-cell { align-items: center; }.drawer-header h2 { margin: 0 0 5px; color: #30241b; font-size: 25px; }.drawer-header small { color: #9a8878; font-size: 11px; }.drawer-close { color: #786a5f; font-size: 27px; cursor: pointer; }.drawer-tabs { display: flex; gap: 2px; overflow-x: auto; padding: 10px 20px 0; border-bottom: 1px solid rgba(80, 54, 32, .12); }.drawer-tabs button { flex: 0 0 auto; border-bottom: 2px solid transparent; padding: 10px 8px; color: #9a8878; font-size: 11px; cursor: pointer; }.drawer-tabs button.active { border-bottom-color: #b85c50; color: #8f352f; font-weight: 800; }.drawer-body { padding: 24px 28px 50px; }.drawer-loading { padding: 60px 28px; color: #9a8878; text-align: center; }.drawer-section { display: grid; gap: 18px; }.profile-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; }.profile-summary div { border-radius: 9px; padding: 10px; background: rgba(234, 217, 191, .42); }.profile-summary span, .profile-summary strong { display: block; }.profile-summary span { color: #9a8878; font-size: 10px; }.profile-summary strong { margin-top: 4px; color: #3b2d24; font-family: Manrope, sans-serif; font-size: 18px; }.detail-facts { border-top: 1px solid rgba(80, 54, 32, .1); padding-top: 16px; }.section-caption { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }.section-caption h3 { margin: 0; color: #3b2d24; font-size: 18px; }.section-caption > span { color: #9a8878; font-size: 10px; }.drawer-list { display: grid; gap: 8px; }.drawer-list-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; border: 1px solid rgba(80, 54, 32, .11); border-radius: 10px; padding: 12px; background: rgba(255, 250, 240, .68); text-align: left; cursor: pointer; }.drawer-list-item:hover { border-color: rgba(184, 92, 80, .42); }.drawer-list-item strong { color: #3b2d24; font-size: 12px; }.drawer-list-item > b { color: #9e3f35; font-size: 10px; }.drawer-list-item > .status-badge { flex: 0 0 auto; }.drawer-body .stack-form { margin-top: 0; }.drawer-body .primary-button { justify-self: stretch; }.booking-drawer, .report-drawer, .log-drawer { width: min(560px, 100%); }.report-body { padding-top: 22px; }
@keyframes drawer-in { from { transform: translateX(24px); opacity: .6; } to { transform: translateX(0); opacity: 1; } }
@media (max-width: 1180px) { .metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }.dashboard-grid { grid-template-columns: 1fr; }.distribution-panel { grid-column: auto; }.distribution-columns { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 820px) { .admin-main { width: min(100% - 28px, 680px); padding-top: 34px; }.admin-hero, .dashboard-toolbar, .view-heading { align-items: flex-start; flex-direction: column; }.hero-actions, .toolbar-controls { width: 100%; justify-content: space-between; }.metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.calendar-admin-grid, .staff-grid { grid-template-columns: 1fr; }.user-directory { min-height: auto; }.directory-list { max-height: 260px; }.import-panel { grid-template-columns: 1fr; }.form-grid.three, .form-grid.two { grid-template-columns: 1fr; }.span-two { grid-column: auto; }.report-meta-grid, .profile-summary { grid-template-columns: repeat(2, 1fr); }.drawer-header, .drawer-body { padding-left: 19px; padding-right: 19px; } }
@media (max-width: 520px) { .admin-main { width: calc(100% - 20px); }.admin-tabs { gap: 6px; }.admin-tab { padding: 9px 11px; font-size: 11px; }.tab-index { display: none; }.metric-grid { gap: 8px; }.metric-card { min-height: 122px; padding: 13px; }.metric-card > strong { margin-top: 12px; font-size: 25px; }.dashboard-panel, .panel-surface { padding: 15px; }.distribution-columns { grid-template-columns: 1fr; }.filter-bar { align-items: stretch; }.filter-bar > input, .filter-bar > select, .filter-bar .date-filter, .filter-bar .primary-button { flex: 1 1 100%; }.date-filter input { width: 100%; }.table-meta, .pagination { align-items: flex-start; flex-direction: column; padding: 14px; }.entry-editor-head { grid-template-columns: 1fr auto; }.entry-editor-head > span { grid-column: 1 / -1; }.entry-editor-head label { grid-column: 1; }.preview-strip { align-items: flex-start; flex-direction: column; }.calendar-card-top { align-items: flex-start; flex-direction: column; gap: 8px; }.drawer-tabs { padding-left: 13px; padding-right: 13px; }.profile-summary strong { font-size: 16px; } }
</style>
