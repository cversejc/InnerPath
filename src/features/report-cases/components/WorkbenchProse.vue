<template>
  <div class="workbench-prose">
    <template v-for="(block, index) in blocks" :key="index">
      <div
        v-if="block.type === 'table'"
        class="prose-table"
        tabindex="0"
        role="region"
        :aria-label="`${label || '正文'}表格`"
      >
        <table>
          <caption>
            {{
              label || "正文"
            }}
            · 内容对照
          </caption>
          <thead>
            <tr>
              <th
                v-for="(header, column) in block.headers"
                :key="column"
                scope="col"
              >
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
              <td v-for="(cell, column) in row" :key="column">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else>{{ block.text }}</p>
    </template>
  </div>
</template>
<script>
import { proseBlocks } from "../prose-blocks.js";
export default {
  props: { text: String, label: String },
  computed: {
    blocks() {
      return proseBlocks(this.text);
    },
  },
};
</script>
<style scoped>
.workbench-prose {
  line-height: var(--leading-prose);
  overflow-wrap: anywhere;
}
p {
  white-space: pre-wrap;
  margin: var(--space-4) 0;
}
.prose-table {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
  background: var(--surface);
}
table {
  border-collapse: collapse;
  width: 100%;
  min-width: 540px;
}
caption {
  text-align: left;
  padding: var(--space-3);
  color: var(--ink-soft);
  font-size: var(--text-body-sm);
}
th,
td {
  text-align: left;
  vertical-align: top;
  padding: var(--space-3);
  border-top: 1px solid var(--line);
  min-width: 120px;
}
th {
  font-weight: var(--weight-semibold);
  background: var(--paper);
}
</style>
