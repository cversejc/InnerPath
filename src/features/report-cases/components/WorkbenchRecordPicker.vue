<template>
  <div v-if="items.length" class="record-picker">
    <label
      ><span>{{ label }} · {{ items.length }} 项</span
      ><select
        :value="activeKey"
        @change="$emit('update:modelValue', $event.target.value)"
      >
        <option
          v-for="(item, index) in items"
          :key="itemKey(item)"
          :value="itemKey(item)"
        >
          {{ index + 1 }}. {{ itemLabel(item) }}
        </option>
      </select></label
    >
    <div class="record-picker-actions">
      <VanButton
        plain
        native-type="button"
        :disabled="activeIndex <= 0"
        @click="move(-1)"
        >上一项</VanButton
      >
      <span>{{ activeIndex + 1 }} / {{ items.length }}</span>
      <VanButton
        plain
        native-type="button"
        :disabled="activeIndex >= items.length - 1"
        @click="move(1)"
        >下一项</VanButton
      >
    </div>
  </div>
</template>
<script>
import { Button as VanButton } from "vant";
export default {
  components: { VanButton },
  props: {
    items: { type: Array, default: () => [] },
    modelValue: { type: String, default: "" },
    label: { type: String, default: "选择条目" },
    keyField: { type: String, default: "key" },
    titleField: { type: String, default: "title" },
  },
  emits: ["update:modelValue"],
  computed: {
    activeIndex() {
      const index = this.items.findIndex(
        (item) => this.itemKey(item) === this.modelValue,
      );
      return Math.max(0, index);
    },
    activeKey() {
      return this.items[this.activeIndex]
        ? this.itemKey(this.items[this.activeIndex])
        : "";
    },
  },
  methods: {
    itemKey(item) {
      return String(item[this.keyField] ?? item.id ?? item.title);
    },
    itemLabel(item) {
      return String(item[this.titleField] || "未命名条目").slice(0, 85);
    },
    move(direction) {
      const item = this.items[this.activeIndex + direction];
      if (item) this.$emit("update:modelValue", this.itemKey(item));
    },
  },
};
</script>
<style scoped>
.record-picker {
  display: flex;
  align-items: end;
  gap: var(--space-4);
  margin: var(--space-4) 0;
  min-width: 0;
}
label {
  display: grid;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
  font-size: var(--text-body-sm);
  color: var(--ink-soft);
}
select {
  width: 100%;
  min-width: 0;
  min-height: var(--touch-target);
  padding: var(--space-2);
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
  background: var(--paper-soft);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
}
.record-picker-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
}
.record-picker-actions span {
  font-size: var(--text-body-sm);
  color: var(--muted);
}
.record-picker-actions :deep(button) {
  min-height: var(--touch-target);
}
@media (max-width: 600px) {
  .record-picker {
    align-items: stretch;
    flex-direction: column;
  }
  .record-picker-actions {
    justify-content: flex-end;
  }
}
</style>
