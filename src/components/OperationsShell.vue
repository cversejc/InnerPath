<template>
  <div
    :class="['operations-shell', shellClass, { 'is-mobile-nav-open': mobileNavOpen }]"
  >
    <aside
      class="operations-rail"
      :class="{ 'is-open': mobileNavOpen }"
      :aria-label="`${brandSubtitle}导航`"
    >
      <div class="operations-rail-brand">
        <router-link
          class="operations-brand-lockup"
          :to="brandTo"
          :aria-label="`返回${brandSubtitle}`"
          @click="closeMobileNav"
        >
          <picture>
            <source srcset="/brand-emblem.webp" type="image/webp">
            <img src="/brand-emblem.png" alt="" width="430" height="574" decoding="async">
          </picture>
          <span>
            <strong>辰鉴</strong>
            <small>{{ brandSubtitle }}</small>
          </span>
        </router-link>
        <span class="operations-rail-status"><i></i>{{ statusLabel }}</span>
      </div>

      <nav class="operations-rail-nav" aria-label="运营中心导航">
        <div v-for="group in navGroups" :key="group.id" class="operations-nav-group">
          <p class="operations-nav-group-label">{{ group.label }}</p>
          <template v-for="item in group.items" :key="item.id">
            <router-link
              v-if="item.to"
              class="operations-rail-item"
              :class="{ active: item.active }"
              :to="item.to"
              :aria-current="item.active ? 'page' : undefined"
              @click="closeMobileNav"
            >
              <IconMark :name="item.icon || 'compass'" />
              <span>{{ item.label }}</span>
              <b v-if="item.index" class="operations-rail-item-index">{{ item.index }}</b>
            </router-link>
            <button
              v-else
              type="button"
              class="operations-rail-item"
              :class="{ active: item.active }"
              :aria-current="item.active ? 'page' : undefined"
              @click="selectItem(item)"
            >
              <IconMark :name="item.icon || 'compass'" />
              <span>{{ item.label }}</span>
              <b v-if="item.index" class="operations-rail-item-index">{{ item.index }}</b>
            </button>
          </template>
        </div>
      </nav>

      <div class="operations-rail-footer">
        <div class="operations-operator">
          <span class="operations-operator-avatar">{{ operatorInitial }}</span>
          <span>
            <strong>{{ operatorName }}</strong>
            <small>{{ operatorRole }}</small>
          </span>
        </div>
        <VanButton
          class="operations-rail-logout"
          type="default"
          plain
          native-type="button"
          :disabled="loggingOut"
          :loading="loggingOut"
          :aria-busy="loggingOut"
          @click="$emit('logout')"
        >
          <template #icon><IconMark name="logout" /></template>
          退出登录
        </VanButton>
      </div>
    </aside>

    <button
      v-if="mobileNavOpen"
      type="button"
      class="operations-rail-scrim"
      :aria-label="`关闭${brandSubtitle}导航`"
      @click="closeMobileNav"
    ></button>

    <div :class="['operations-app', appClass]">
      <header class="operations-topbar">
        <div class="operations-topbar-leading">
          <VanButton
            class="operations-menu-toggle"
            type="default"
            plain
            native-type="button"
            :aria-label="`打开${brandSubtitle}导航`"
            :aria-expanded="mobileNavOpen"
            @click="toggleMobileNav"
          >
            <template #icon><IconMark name="settings" /></template>
          </VanButton>
          <div class="operations-breadcrumb" aria-label="当前位置">
            <span>{{ sectionLabel }}</span>
            <IconMark v-if="currentLabel" name="arrow" />
            <strong v-if="currentLabel">{{ currentLabel }}</strong>
          </div>
        </div>
        <div class="operations-topbar-actions">
          <slot name="topbar-actions"></slot>
        </div>
      </header>

      <slot></slot>
    </div>
  </div>
</template>

<script>
import { Button as VanButton } from 'vant'
import IconMark from './IconMark.vue'

export default {
  name: 'OperationsShell',
  components: { IconMark, VanButton },
  emits: ['select', 'logout'],
  props: {
    appClass: { type: String, default: '' },
    brandSubtitle: { type: String, default: '运营中心' },
    brandTo: { type: [String, Object], default: '/admin' },
    currentLabel: { type: String, default: '' },
    loggingOut: { type: Boolean, default: false },
    navGroups: { type: Array, default: () => [] },
    operatorName: { type: String, default: '操作员' },
    operatorRole: { type: String, default: '内部成员' },
    sectionLabel: { type: String, default: '运营中心' },
    shellClass: { type: [String, Array, Object], default: '' },
    statusLabel: { type: String, default: 'OPERATIONS CENTER' }
  },
  computed: {
    operatorInitial() {
      return this.operatorName.slice(0, 1).toUpperCase()
    }
  },
  methods: {
    toggleMobileNav() {
      this.mobileNavOpen = !this.mobileNavOpen
    },
    closeMobileNav() {
      this.mobileNavOpen = false
    },
    selectItem(item) {
      this.closeMobileNav()
      this.$emit('select', item.id)
    }
  },
  data() {
    return { mobileNavOpen: false }
  }
}
</script>

<style src="./OperationsShell.css"></style>
