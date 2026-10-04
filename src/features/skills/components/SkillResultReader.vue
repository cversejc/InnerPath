<template>
  <section class="skill-result-reader" aria-label="技能结果阅读">
    <div v-if="sections.length" class="result-selectors">
      <label
        >内容分类<select v-model="sectionKey" @change="itemIndex = 0">
          <option v-for="entry in sections" :key="entry.key" :value="entry.key">
            {{ entry.label
            }}{{
              Array.isArray(entry.value) ? ` · ${entry.value.length} 项` : ""
            }}
          </option>
        </select></label
      >
      <label v-if="Array.isArray(active?.value) && active.value.length"
        >选择条目<select v-model.number="itemIndex">
          <option
            v-for="(item, index) in active.value"
            :key="index"
            :value="index"
          >
            {{ index + 1 }}. {{ itemTitle(item) }}
          </option>
        </select></label
      >
    </div>
    <ReadableData
      v-if="active"
      :value="
        Array.isArray(active.value)
          ? (active.value[itemIndex] ?? [])
          : active.value
      "
    />
    <p v-else>此结果包含技术数据，可展开原始结构查看。</p>
    <details>
      <summary>查看完整原始结构</summary>
      <pre>{{ JSON.stringify(value, null, 2) }}</pre>
    </details>
  </section>
</template>
<script>
import { readableEntries, displayText } from "../presentation.js";
import ReadableData from "./ReadableData.vue";
export default {
  components: { ReadableData },
  props: { value: Object },
  data: () => ({ sectionKey: "", itemIndex: 0 }),
  computed: {
    sections() {
      return readableEntries(this.value);
    },
    active() {
      return (
        this.sections.find((item) => item.key === this.sectionKey) ||
        this.sections[0]
      );
    },
  },
  mounted() {
    this.sectionKey = this.sections[0]?.key || "";
  },
  methods: {
    itemTitle(item) {
      return displayText(
        typeof item === "object" && item
          ? item.title || item.claim || item.theme || item.message || "查看内容"
          : item,
      ).slice(0, 70);
    },
  },
};
</script>
<style scoped>
.result-selectors {
  display: grid;
  gap: var(--space-3);
  margin: var(--space-3) 0;
}
label {
  display: grid;
  gap: var(--space-2);
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
summary {
  display: flex;
  align-items: center;
  min-height: var(--touch-target);
  color: var(--cinnabar-deep);
  cursor: pointer;
}
pre {
  padding: var(--space-3);
  background: var(--surface);
  font-family: var(--font-mono);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
