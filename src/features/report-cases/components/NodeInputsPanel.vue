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
      <p v-if="!activeGroup.items.length" class="input-empty">
        {{ activeGroup.empty }}
      </p>
      <dl
        v-else-if="activeGroup.display === 'fields'"
        class="input-fields"
        :aria-label="activeGroup.title"
      >
        <div
          v-for="item in activeGroup.items"
          :key="item.key || item.title"
          :class="{
            wide:
              String(item.body).length > 60 ||
              [
                '本次主要困扰',
                '期待获得的帮助',
                '补充说明',
                '选择情况',
                '工作经历补充',
              ].includes(item.title),
          }"
        >
          <dt>{{ item.title }}</dt>
          <dd>{{ item.body }}</dd>
        </div>
      </dl>
      <InputRecordCollection
        v-else
        :key="activeGroup.key"
        :items="activeGroup.items"
        :continuous="activeGroup.continuous"
        :label="activeGroup.title"
      />
    </template>
  </section>
</template>
<script>
import { Button as VanButton } from "vant";
import InputRecordCollection from "./InputRecordCollection.vue";
export default {
  components: { VanButton, InputRecordCollection },
  props: {
    groups: { type: Array, default: () => [] },
    guidance: { type: String, default: "" },
  },
  data: () => ({ groupKey: "" }),
  computed: {
    activeGroup() {
      return (
        this.groups.find((group) => group.key === this.groupKey) ||
        this.groups[0]
      );
    },
  },
  methods: {
    selectGroup(key) {
      this.groupKey = key;
      this.$nextTick(() =>
        this.$el.closest(".node-workspace-body")?.scrollTo({ top: 0 }),
      );
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
.input-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4) var(--space-5);
  margin: 0;
  padding: var(--space-5);
  border-radius: var(--button-radius);
  background: var(--paper-soft);
}
.input-fields > div {
  min-width: 0;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--line);
}
.input-fields > .wide {
  grid-column: 1 / -1;
}
dt {
  color: var(--muted);
  font-size: var(--text-body-sm);
  margin-bottom: var(--space-1);
}
dd {
  margin: 0;
  white-space: pre-wrap;
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
@media (max-width: 1000px) {
  .input-fields {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .input-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 600px) {
  .node-input-panel,
  .input-fields {
    padding: var(--space-4);
  }
}
@media (max-width: 360px) {
  .input-fields {
    grid-template-columns: 1fr;
  }
}
</style>
