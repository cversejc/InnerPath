<template>
  <div class="requests-page">
    <BrandNav />

    <main class="requests-main">
      <BrandPageHeader class="requests-hero" contained eyebrow="MY REQUESTS" title="我的申请" description="让每一次探索，都有回音。在这里查看申请进度，交付后即可阅读报告或打开日历。" seal="有信">
        <template #actions>
          <router-link class="secondary-button" to="/pages/assessment/assessment">申请人生说明书</router-link>
          <router-link class="primary-button" :to="calendarActionPath">{{ calendarActionLabel }}</router-link>
        </template>
      </BrandPageHeader>

      <p v-if="message" class="page-message" :class="{ error: messageType === 'error' }" role="status" aria-live="polite">{{ message }}</p>

      <section class="request-toolbar paper-card" aria-label="申请筛选">
        <div class="filter-copy">
          <span class="eyebrow">REQUEST LEDGER</span>
          <strong>申请记录</strong>
          <small>{{ filteredRequests.length }} 项记录</small>
        </div>
        <div class="request-filters" role="group" aria-label="按类型筛选">
          <VanButton v-for="filter in filters" :key="filter.id" type="default" plain native-type="button" :class="{ active: activeFilter === filter.id }" :aria-pressed="activeFilter === filter.id" @click="activeFilter = filter.id">{{ filter.label }}</VanButton>
        </div>
      </section>

      <section v-if="loading" class="request-loading" aria-label="正在加载申请">
        <i v-for="index in 3" :key="index"></i>
      </section>

      <section v-else-if="!filteredRequests.length" class="empty-request paper-card">
        <span class="empty-seal" aria-hidden="true">申</span>
        <div>
          <p class="eyebrow">A QUIET START</p>
          <h2>还没有申请记录</h2>
          <p>先申请并获得咨询师交付的报告，再以报告为基础生成 30 天决策日历。</p>
        </div>
        <div class="empty-actions">
          <router-link class="primary-button" to="/pages/assessment/assessment">申请报告</router-link>
          <router-link class="secondary-button" :to="calendarActionPath">{{ calendarActionLabel }}</router-link>
        </div>
      </section>

      <section v-else class="request-list" aria-label="我的申请列表">
        <article v-for="item in filteredRequests" :key="`${item.workflow_type || item.service_type}:${item.id}`" class="request-card paper-card" :class="`status-${item.status}`">
          <div class="request-card-head">
            <div class="request-type-mark" :class="`type-${item.service_type}`" aria-hidden="true"><IconMark :name="item.service_type === 'report' ? 'reports' : 'calendar'" /></div>
            <div class="request-card-title">
              <div class="request-kicker"><span>{{ serviceTypeLabel(item) }}</span><span>申请 #{{ item.id }}</span></div>
              <h2>{{ item.service_type === 'report' ? '人生说明书' : '决策日历' }}</h2>
              <p>提交于 {{ formatDateTime(item.created_at) }}<span v-if="item.service_type === 'calendar' && payload(item).start_date"> · {{ payload(item).start_date }} 起 30 天</span></p>
            </div>
            <span class="status-badge request-status" :class="`request-status-${item.status}`">{{ statusLabel(item.status) }}</span>
          </div>

          <div class="request-card-body">
            <p v-if="item.service_type === 'report'" class="request-summary">关注议题：{{ topicLabel(payload(item).selected_topics) }}</p>
            <p v-else class="request-summary">关注目标：{{ payload(item).calendar_goal || '尚未填写具体目标' }}</p>
            <p v-if="item.workflow_type === 'calendar_generation' && item.status === 'ai_processing'" class="request-note">正在依据报告生成日历{{ item.progress ? ` · ${item.progress}%` : '' }}，成功后会自动开放使用。</p>
            <div v-if="item.workflow_type === 'calendar_legacy' && ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing', 'pending', 'reviewing'].includes(item.status)" class="needs-info-note">
              <strong>日历流程已调整</strong>
              <p>日历现在需要基于已交付报告生成。请先申请报告，咨询师交付后再启动日历生成。</p>
            </div>
            <p v-if="payload(item).additional_info" class="request-note">补充说明：{{ payload(item).additional_info }}</p>
            <div v-if="item.status === 'needs_info'" class="needs-info-note" role="alert">
              <strong>请补充资料</strong>
              <p>{{ item.needs_info_reason || '咨询师希望进一步了解你的需求。' }}</p>
            </div>
            <div v-if="item.status === 'failed'" class="needs-info-note failed-note" role="alert">
              <strong>{{ item.workflow_type === 'calendar_generation' ? '日历生成暂未完成' : '初步分析暂未完成' }}</strong>
              <p>{{ item.workflow_type === 'calendar_generation' ? '可以重新尝试生成；已有日历不会被覆盖，直到新日历成功开放。' : '申请仍可继续跟进。' }}</p>
            </div>
          </div>

          <footer class="request-card-actions">
            <router-link v-if="item.status === 'delivered' && item.result_type === 'report'" class="primary-button compact-button" :to="`/pages/report/detail?id=${item.result_id}`">查看报告</router-link>
            <router-link v-else-if="item.status === 'delivered' && item.result_type === 'calendar'" class="primary-button compact-button" to="/pages/calendar/calendar">打开日历</router-link>
            <router-link v-if="item.workflow_type === 'calendar_legacy' && item.status !== 'delivered' && item.status !== 'rejected' && item.status !== 'withdrawn'" class="secondary-button compact-button" to="/pages/calendar/calendar?generate=1">重新开始</router-link>
            <VanButton v-if="item.workflow_type === 'calendar_generation' && item.status === 'failed'" type="primary" native-type="button" class="primary-button compact-button" :disabled="retryingCalendarId === item.id" :loading="retryingCalendarId === item.id" @click="retryCalendar(item)">{{ retryingCalendarId === item.id ? '重新生成中…' : '重试生成' }}</VanButton>
            <router-link v-if="item.status === 'needs_info'" class="secondary-button compact-button" :to="editPath(item)">补充资料</router-link>
            <VanButton v-if="canWithdraw(item.status)" type="default" plain native-type="button" class="text-button danger-text" :disabled="withdrawnId === item.id" @click="withdraw(item)">{{ withdrawnId === item.id ? '撤回中…' : '撤回申请' }}</VanButton>
            <span v-if="item.status === 'delivered'" class="delivered-stamp">{{ item.workflow_type === 'calendar_generation' ? '日历已自动开放' : '已由咨询师交付' }}</span>
          </footer>
        </article>
      </section>
    </main>

    <BrandFooter />
  </div>
</template>

<script src="../features/service-requests/customer-requests.js"></script>

<style scoped src="../features/service-requests/customer-requests.css"></style>
