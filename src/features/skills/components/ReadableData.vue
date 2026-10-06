<template>
  <div class="readable-data">
    <template v-if="Array.isArray(value)">
      <ol v-if="value.length">
        <li v-for="(item, index) in value" :key="index">
          <ReadableData :value="item" />
        </li>
      </ol>
      <p v-else class="muted">暂无条目</p>
    </template>
    <dl v-else-if="value && typeof value === 'object'">
      <div v-for="entry in entries" :key="entry.key">
        <dt>{{ entry.label }}</dt>
        <dd><ReadableData :value="entry.value" :field="entry.key" /></dd>
      </div>
      <p v-if="!entries.length" class="muted">
        此项为技术数据，可展开原始结构查看。
      </p>
    </dl>
    <p v-else>{{ displayText(value, field) }}</p>
  </div>
</template>
<script>
import { readableEntries, displayText } from "../presentation.js";
export default {
  name: "ReadableData",
  props: { value: { default: null }, field: { type: String, default: "" } },
  computed: {
    entries() {
      return readableEntries(this.value);
    },
  },
  methods: { displayText },
};
</script>
<style scoped>
.readable-data {
  min-width: 0;
  font-size: var(--text-body);
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
p {
  margin: var(--space-2) 0;
  white-space: pre-wrap;
}
dl {
  margin: 0;
}
dl > div {
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--line);
}
dt {
  color: var(--muted);
  font-size: var(--text-body-sm);
}
dd {
  margin: 0;
}
ol {
  padding-left: var(--space-5);
  margin: var(--space-2) 0;
}
li {
  margin-bottom: var(--space-3);
}
.muted {
  color: var(--muted);
}
</style>
