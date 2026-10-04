<template>
  <div class="requests-page">
    <BrandNav />

    <main class="requests-main">
      <header class="requests-hero">
        <div>
          <p class="section-kicker">MY REQUESTS / SERVICE FLOW</p>
          <h1>我的申请</h1>
          <p>人生说明书申请由咨询师处理；收到交付报告后，你可以直接生成决策日历。</p>
        </div>
        <div class="hero-actions">
          <router-link class="secondary-button" to="/pages/assessment/assessment">申请人生说明书</router-link>
          <router-link class="primary-button" to="/pages/user/user?tab=reports">从已交付报告生成日历</router-link>
        </div>
      </header>

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
          <p>先申请人生说明书；交付后可从报告详情直接生成决策日历。</p>
        </div>
        <div class="empty-actions">
          <router-link class="primary-button" to="/pages/assessment/assessment">申请报告</router-link>
          <router-link class="secondary-button" to="/pages/user/user?tab=reports">查看我的报告</router-link>
        </div>
      </section>

      <section v-else class="request-list" aria-label="我的申请列表">
        <article v-for="item in filteredRequests" :id="`request-${item.id}`" :key="item.id" class="request-card paper-card" :class="`status-${item.status}`">
          <div class="request-card-head">
            <div class="request-type-mark" :class="`type-${item.service_type}`" aria-hidden="true"><IconMark :name="item.service_type === 'report' ? 'reports' : 'calendar'" /></div>
            <div class="request-card-title">
              <div class="request-kicker"><span>{{ serviceTypeLabel(item.service_type) }}</span><span>申请 #{{ item.id }}</span></div>
              <h2>{{ item.service_type === 'report' ? '人生说明书' : '决策日历' }}</h2>
              <p>提交于 {{ formatDateTime(item.created_at) }}<span v-if="item.service_type === 'calendar' && payload(item).start_date"> · {{ payload(item).start_date }} 起 30 天</span></p>
            </div>
            <span class="status-badge request-status" :class="`request-status-${item.status}`">{{ statusLabel(item.status) }}</span>
          </div>

          <div class="request-card-body">
            <p v-if="item.service_type === 'report'" class="request-summary">关注议题：{{ topicLabel(payload(item).selected_topics) }}</p>
            <p v-else class="request-summary">关注目标：{{ payload(item).calendar_goal || '尚未填写具体目标' }}</p>
            <p v-if="payload(item).additional_info" class="request-note">补充说明：{{ payload(item).additional_info }}</p>
            <div v-if="item.status === 'needs_info'" class="needs-info-note" role="alert">
              <strong>请补充资料</strong>
              <p>{{ item.needs_info_reason || '咨询师希望进一步了解你的需求。' }}</p>
            </div>
            <form
              v-if="item.status === 'needs_info' && item.service_type === 'report' && item.report_case_id"
              :id="`request-${item.id}-supplement`"
              class="report-supplement-form"
              @submit.prevent="submitReportSupplement(item)"
            >
              <label :for="`request-${item.id}-answer`">回复咨询师</label>
              <textarea
                :id="`request-${item.id}-answer`"
                v-model="followUpAnswers[item.id]"
                rows="4"
                maxlength="4000"
                required
                placeholder="补充与问题相关的实际情况；不确定的部分可以直接说明。"
              ></textarea>
              <p>回复会作为新的用户资料进入当前审核节点。</p>
              <VanButton
                class="primary-button compact-button"
                type="primary"
                native-type="submit"
                :disabled="supplementSubmittingId === item.id || !String(followUpAnswers[item.id] || '').trim()"
                :loading="supplementSubmittingId === item.id"
              >{{ supplementSubmittingId === item.id ? '提交中…' : '提交补充资料' }}</VanButton>
            </form>
            <div v-if="item.status === 'failed'" class="needs-info-note failed-note" role="alert">
              <strong>初步分析暂未完成</strong>
              <p>咨询师会在工作台中重试，当前申请仍可继续跟进。</p>
            </div>
          </div>

          <footer class="request-card-actions">
            <router-link v-if="item.status === 'delivered' && item.result_type === 'report'" class="primary-button compact-button" :to="`/pages/report/detail?id=${item.result_id}`">查看报告</router-link>
            <router-link v-else-if="item.status === 'delivered' && item.result_type === 'calendar'" class="primary-button compact-button" to="/pages/calendar/calendar">打开日历</router-link>
            <router-link v-if="item.status === 'needs_info' && !(item.service_type === 'report' && item.report_case_id)" class="secondary-button compact-button" :to="editPath(item)">补充资料</router-link>
            <VanButton v-if="canWithdraw(item.status)" type="default" plain native-type="button" class="text-button danger-text" :disabled="withdrawnId === item.id" @click="withdraw(item)">{{ withdrawnId === item.id ? '撤回中…' : '撤回申请' }}</VanButton>
            <span v-if="item.status === 'delivered'" class="delivered-stamp">已由咨询师交付</span>
          </footer>
        </article>
      </section>
    </main>

    <BrandFooter />
  </div>
</template>

<script src="../features/service-requests/customer-requests.js"></script>

<style scoped src="../features/service-requests/customer-requests.css"></style>
