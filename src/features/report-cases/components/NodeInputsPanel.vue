<template>
  <section class="node-input-panel" aria-label="本节点输入资料">
    <h3>本节点输入</h3>
    <p>{{ guidance }}</p>
    <div class="input-group-buttons" aria-label="输入分类">
      <VanButton
        v-for="group in groups"
        :key="group.key"
        plain
        native-type="button"
        :aria-pressed="activeGroup?.key === group.key"
        :class="{ active: activeGroup?.key === group.key }"
        @click="selectGroup(group.key)"
        >{{ group.title }} · {{ group.items.length }}</VanButton
      >
    </div>
    <template v-if="activeGroup">
      <p class="input-reason">{{ activeGroup.reason }}</p>
      <WorkbenchRecordPicker
        v-model="selectedKey"
        :items="activeGroup.items"
        label="选择输入"
      />
      <article v-if="selectedItem" class="input-detail">
        <header>
          <h4>{{ selectedItem.title }}</h4>
          <span>{{ selectedItem.meta }}</span>
        </header>
        <p>{{ selectedItem.body }}</p>
        <small v-if="selectedItem.source">{{ selectedItem.source }}</small>
      </article>
      <p v-else class="input-empty">{{ activeGroup.empty }}</p>
    </template>
  </section>
</template>
<script>
import { Button as VanButton } from "vant";
import WorkbenchRecordPicker from "./WorkbenchRecordPicker.vue";
export default {
  components: { VanButton, WorkbenchRecordPicker },
  props: {
    groups: { type: Array, default: () => [] },
    guidance: { type: String, default: "" },
  },
  data: () => ({ groupKey: "", selectedKey: "" }),
  computed: {
    activeGroup() {
      return (
        this.groups.find((group) => group.key === this.groupKey) ||
        this.groups[0]
      );
    },
    selectedItem() {
      return (
        this.activeGroup?.items.find(
          (item) => String(item.key || item.title) === this.selectedKey,
        ) || this.activeGroup?.items[0]
      );
    },
  },
  methods: {
    selectGroup(key) {
      this.groupKey = key;
      this.selectedKey = "";
    },
  },
};
</script>
<style scoped>
.node-input-panel {
  padding: var(--space-5);
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--surface);
}
h3,
h4 {
  margin: 0;
  font-size: var(--text-h4);
  font-weight: var(--weight-semibold);
}
p {
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
.input-group-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.input-group-buttons :deep(button) {
  min-height: var(--touch-target);
  white-space: normal;
  height: auto;
  padding: var(--space-3);
}
.input-group-buttons :deep(.active) {
  color: var(--cinnabar-deep);
  border-color: var(--cinnabar);
}
.input-reason,
.input-empty {
  color: var(--muted);
}
.input-detail {
  padding: var(--space-5);
  background: var(--paper-soft);
  border-radius: var(--button-radius);
}
.input-detail header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.input-detail header span,
small {
  color: var(--muted);
  font-size: var(--text-body-sm);
}
.input-detail p {
  white-space: pre-wrap;
}
@media (max-width: 600px) {
  .node-input-panel,
  .input-detail {
    padding: var(--space-4);
  }
}
</style>
