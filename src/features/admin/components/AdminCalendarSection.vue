<script setup>
import { calendarStatusText, formatDate } from '../formatters.js'

defineProps({
  calendarForm: { type: Object, required: true },
  calendarImportJson: { type: String, default: '' },
  calendarLoading: { type: Boolean, default: false },
  calendarSaving: { type: Boolean, default: false },
  calendarUserSearch: { type: String, default: '' },
  calendarUsers: { type: Array, default: () => [] },
  calendars: { type: Array, default: () => [] },
  selectedCalendarUser: { type: Object, default: null },
  showCalendarImport: { type: Boolean, default: false }
})

defineEmits([
  'add-entry',
  'archive-calendar',
  'cancel-edit',
  'export-calendar',
  'import-json',
  'load-users',
  'new-calendar',
  'prepare-edit',
  'publish-calendar',
  'remove-entry',
  'save-calendar',
  'select-user',
  'toggle-import',
  'update:calendar-import-json',
  'update:calendar-user-search'
])
</script>

<template>
  <section class="content-view calendar-view">
    <div class="view-heading"><div><p class="eyebrow">PERSONAL TIMEZONE / EDITOR</p><h2>用户日历</h2><p>结构化维护每日节奏，已发布内容通过新版本上线。</p></div><button class="secondary-button" type="button" @click="$emit('toggle-import')">{{ showCalendarImport ? '收起 JSON 导入' : '批量 JSON 导入' }}</button></div>
    <div v-if="showCalendarImport" class="import-panel">
      <div><strong>批量导入日历</strong><p>格式支持 `{ title, entries }` 或直接传入条目数组；导入后默认为草稿。</p></div>
      <textarea :value="calendarImportJson" rows="4" placeholder='{"title":"2026 秋季行动日历","entries":[{"entry_date":"2026-09-07","tone":"yellow","keyword":"观察","summary":"先理清信息","suitable":["整理计划"],"unsuitable":["仓促拍板"]}]}' @input="$emit('update:calendar-import-json', $event.target.value)"></textarea>
      <div class="action-row"><button class="primary-button compact-button" type="button" :disabled="calendarSaving" @click="$emit('import-json')">导入为草稿</button></div>
    </div>

    <div class="calendar-admin-grid">
      <aside class="user-directory panel-surface">
        <div class="panel-heading"><div><p class="eyebrow">SELECT USER</p><h3>选择用户</h3></div><span>{{ calendarUsers.length }}</span></div>
        <div class="directory-search"><input :value="calendarUserSearch" aria-label="搜索用户" placeholder="搜索用户" @input="$emit('update:calendar-user-search', $event.target.value)" @keyup.enter="$emit('load-users')"><button type="button" aria-label="搜索用户" @click="$emit('load-users')"><IconMark name="search" /></button></div>
        <div class="directory-list">
          <button v-for="user in calendarUsers" :key="user.id" type="button" :class="{ selected: selectedCalendarUser?.id === user.id }" :aria-pressed="selectedCalendarUser?.id === user.id" @click="$emit('select-user', user)"><span class="avatar-mark small">{{ user.name?.slice(0, 1) || '人' }}</span><span><strong>{{ user.name }}</strong><small>#{{ user.id }} · {{ user.phone }}</small></span><IconMark name="arrow" /></button>
          <p v-if="!calendarUsers.length" class="empty-cell">请搜索或暂无用户。</p>
        </div>
      </aside>

      <div class="calendar-editor panel-surface">
        <div class="panel-heading"><div><p class="eyebrow">CALENDAR VERSIONS</p><h3>{{ selectedCalendarUser ? `${selectedCalendarUser.name} 的日历` : '先选择一个用户' }}</h3></div><button v-if="selectedCalendarUser" class="primary-button compact-button" type="button" @click="$emit('new-calendar')"><IconMark name="plus" /> <span>新建草稿</span></button></div>
        <div v-if="calendarLoading" class="list-loading" aria-label="正在加载日历"><i v-for="index in 4" :key="index"></i></div>
        <div v-else-if="selectedCalendarUser" class="calendar-list">
          <article v-for="calendar in calendars" :key="calendar.id" class="calendar-card" :class="{ selected: calendarForm.id === calendar.id }">
            <div class="calendar-card-top"><div><strong>{{ calendar.title }}</strong><small>v{{ calendar.version_number }} · {{ calendar.entries?.length || 0 }} 天 · 更新于 {{ formatDate(calendar.updated_at) }}</small></div><span :class="['status-badge', `calendar-${calendar.status}`]">{{ calendarStatusText(calendar.status) }}</span></div>
            <div class="calendar-card-preview"><span v-for="entry in (calendar.entries || []).slice(0, 4)" :key="entry.id">{{ formatDate(entry.entry_date) }} · {{ entry.keyword || entry.status_label || '未命名' }}</span></div>
            <div class="row-actions"><button type="button" @click="$emit('prepare-edit', calendar)">{{ calendar.status === 'draft' ? '编辑' : '创建编辑版本' }}</button><button type="button" @click="$emit('export-calendar', calendar)">JSON</button><button v-if="calendar.status === 'draft'" type="button" @click="$emit('publish-calendar', calendar)">发布</button><button v-if="calendar.status === 'published'" type="button" class="danger-action" @click="$emit('archive-calendar', calendar)">归档</button></div>
          </article>
          <p v-if="!calendars.length" class="empty-cell">暂无日历，可以从右上角创建草稿。</p>
        </div>

        <form v-if="calendarForm.visible" class="calendar-editor-form" @submit.prevent="$emit('save-calendar')">
          <div class="editor-banner"><span>{{ calendarForm.id ? `编辑 v${calendarForm.version_number}` : '新建草稿' }}</span><span v-if="calendarForm.status">{{ calendarStatusText(calendarForm.status) }}</span></div>
          <div class="form-grid two"><label>日历标题<input v-model.trim="calendarForm.title" required maxlength="150"></label><label>开始日期<input v-model="calendarForm.start_date" type="date"></label><label>结束日期<input v-model="calendarForm.end_date" type="date"></label></div>
          <div class="entry-toolbar"><div><strong>每日条目</strong><small>{{ calendarForm.entries.length }} 个日期 · 日期不可重复</small></div><button class="secondary-button compact-button" type="button" @click="$emit('add-entry')">＋ 添加日期</button></div>
          <div class="entry-list">
            <article v-for="(entry, index) in calendarForm.entries" :key="entry._key" class="entry-editor">
              <div class="entry-editor-head"><span>DAY {{ String(index + 1).padStart(2, '0') }}</span><label>日期<input v-model="entry.entry_date" type="date" required></label><button type="button" aria-label="删除条目" @click="$emit('remove-entry', index)">×</button></div>
              <div class="form-grid three"><label>节奏色调<select v-model="entry.tone"><option value="green">推进</option><option value="green-yellow">先推后收</option><option value="yellow-green">先备后行</option><option value="yellow">观察</option><option value="red-yellow">缓冲</option><option value="red">收气</option><option value="rest">休整</option></select></label><label>日柱<input v-model.trim="entry.day_pillar" placeholder="可选"></label><label>状态标签<input v-model.trim="entry.status_label" placeholder="例如：准备期"></label><label>关键词<input v-model.trim="entry.keyword" placeholder="例如：观察"></label><label class="span-two">摘要<input v-model.trim="entry.summary" placeholder="这一天给用户的行动提示"></label></div>
              <label>适合事项 <input v-model.trim="entry.suitableText" placeholder="用逗号分隔，例如：整理信息，沟通计划"></label>
              <label>先不要做 <input v-model.trim="entry.unsuitableText" placeholder="用逗号分隔"></label>
              <label>时间窗口 <input v-model.trim="entry.time_window" placeholder="例如：上午适合整理，下午适合轻推"></label>
              <label>管理员备注 <textarea v-model.trim="entry.admin_note" rows="2" placeholder="仅后台可见"></textarea></label>
            </article>
            <p v-if="!calendarForm.entries.length" class="empty-cell entry-empty">草稿可以先不填条目；发布前至少需要一条。</p>
          </div>
          <div class="preview-strip"><div><span class="eyebrow">USER PREVIEW</span><strong>{{ calendarForm.title || '未命名日历' }}</strong></div><span>{{ calendarForm.start_date || '起始日期待定' }} — {{ calendarForm.end_date || '结束日期待定' }}</span><span>{{ calendarForm.entries.length }} 天 · 管理员备注不会展示给用户</span></div>
          <div class="action-row editor-actions"><button class="primary-button" type="submit" :disabled="calendarSaving">{{ calendarSaving ? '保存中…' : '保存草稿' }}</button><button class="secondary-button" type="button" @click="$emit('cancel-edit')">取消</button></div>
        </form>
        <div v-else-if="selectedCalendarUser" class="editor-empty"><IconMark name="calendar" /><p>选择一个版本开始编辑，或创建一张新的草稿日历。</p></div>
        <div v-else class="editor-empty"><IconMark name="compass" /><p>从左侧选择用户后，这里会显示其全部日历版本。</p></div>
      </div>
    </div>
  </section>
</template>
