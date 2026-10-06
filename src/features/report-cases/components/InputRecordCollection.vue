<template>
  <div class="input-records">
    <nav
      v-if="items.length > 1"
      class="reading-modes"
      aria-label="资料阅读方式"
    >
      <VanButton
        plain
        native-type="button"
        :aria-pressed="mode === 'overview'"
        @click="mode = 'overview'"
        >集中概览</VanButton
      >
      <VanButton
        plain
        native-type="button"
        :aria-pressed="mode === 'detail'"
        @click="mode = 'detail'"
        >逐项细读</VanButton
      >
      <VanButton
        v-if="continuous"
        plain
        native-type="button"
        :aria-pressed="mode === 'reading'"
        @click="mode = 'reading'"
        >全文通读</VanButton
      >
    </nav>
    <WorkbenchRecordPicker
      v-if="mode === 'detail' && items.length > 1"
      v-model="selectedKey"
      :items="items"
      label="选择输入"
    />
    <div
      v-if="mode === 'overview' && items.length > 1"
      class="input-overview"
      :aria-label="`${label}概览`"
    >
      <label v-if="origins.length > 1" class="origin-filter"
        >筛选来源节点<select v-model="originFilter">
          <option value="">全部节点 · {{ items.length }} 项</option>
          <option v-for="origin in origins" :key="origin" :value="origin">
            {{ origin }}
          </option>
        </select></label
      >
      <article
        v-for="(item, index) in overviewItems"
        :key="item.key || item.title"
        class="overview-row"
      >
        <span class="row-number">{{ index + 1 }}</span>
        <div>
          <p class="record-meta">
            {{ [item.origin, item.meta].filter(Boolean).join(" · ") }}
          </p>
          <h4>{{ preview(item.title) }}</h4>
          <p v-if="item.body" class="record-excerpt">
            {{ preview(item.body) }}
          </p>
        </div>
        <VanButton
          plain
          native-type="button"
          :aria-label="`细读第 ${index + 1} 项`"
          @click="openItem(item)"
          >查看详情</VanButton
        >
      </article>
    </div>
    <div
      v-else
      class="input-reading"
      :aria-label="mode === 'reading' ? `${label}全文` : `${label}详情`"
    >
      <article
        v-for="item in readingItems"
        :key="item.key || item.title"
        class="input-detail"
      >
        <header v-if="!item.calculation">
          <h4>{{ item.title }}</h4>
          <span>{{
            [item.origin, item.meta].filter(Boolean).join(" · ")
          }}</span>
        </header>
        <FoundationEvidence
          v-if="item.calculation"
          :value="item.calculation"
          :fallback="item.body"
        />
        <WorkbenchProse
          v-else-if="continuous"
          :text="item.body"
          :label="item.title"
        />
        <p v-else class="record-body">{{ item.body }}</p>
        <details v-if="item.source && continuous" class="source-disclosure">
          <summary>查看依据与来源</summary>
          <p class="record-source">{{ item.source }}</p>
        </details>
        <p v-else-if="item.source" class="record-source">{{ item.source }}</p>
      </article>
    </div>
  </div>
</template>
<script>
import { Button as VanButton } from "vant";
import WorkbenchRecordPicker from "./WorkbenchRecordPicker.vue";
import FoundationEvidence from "./FoundationEvidence.vue";
import WorkbenchProse from "./WorkbenchProse.vue";
export default {
  components: {
    VanButton,
    WorkbenchRecordPicker,
    FoundationEvidence,
    WorkbenchProse,
  },
  props: {
    items: { type: Array, default: () => [] },
    label: String,
    continuous: Boolean,
  },
  data: () => ({ mode: "overview", selectedKey: "", originFilter: "" }),
  watch: {
    mode() {
      this.$nextTick(() =>
        this.$el.closest(".node-workspace-body")?.scrollTo({ top: 0 }),
      );
    },
  },
  computed: {
    origins() {
      return [
        ...new Set(this.items.map((item) => item.origin).filter(Boolean)),
      ];
    },
    overviewItems() {
      return this.items.filter(
        (item) => !this.originFilter || item.origin === this.originFilter,
      );
    },
    selectedItem() {
      return (
        this.items.find(
          (item) => String(item.key || item.title) === this.selectedKey,
        ) || this.items[0]
      );
    },
    readingItems() {
      return this.mode === "reading"
        ? this.items
        : this.selectedItem
          ? [this.selectedItem]
          : [];
    },
  },
  methods: {
    preview(value) {
      const text = String(value).replace(/\s+/g, " ");
      return text.length > 150 ? `${text.slice(0, 150)}…` : text;
    },
    openItem(item) {
      this.selectedKey = String(item.key || item.title);
      this.mode = "detail";
    },
  },
};
</script>
<style scoped>
.reading-modes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.reading-modes :deep([aria-pressed="true"]) {
  color: var(--cinnabar-deep);
  border-color: var(--cinnabar);
}
.input-overview,
.input-reading {
  display: grid;
  gap: var(--space-3);
}
.overview-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-4);
  background: var(--paper-soft);
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
}
.row-number {
  color: var(--muted);
  padding-top: var(--space-1);
}
.origin-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.origin-filter select {
  min-height: var(--touch-target);
  font: inherit;
  font-size: var(--text-body);
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
  padding: var(--space-2) var(--space-3);
  color: var(--ink);
  background: var(--paper-soft);
}
h4 {
  margin: 0;
  font-size: var(--text-body);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
.record-meta {
  margin: 0 0 var(--space-1);
  color: var(--muted);
  font-size: var(--text-body-sm);
}
.record-excerpt,
.record-source {
  color: var(--ink-soft);
  font-size: var(--text-body-sm);
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
  margin-bottom: 0;
}
.input-detail {
  padding: var(--space-4);
  background: var(--paper-soft);
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
}
.input-detail header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.input-detail header span {
  color: var(--muted);
  font-size: var(--text-body-sm);
}
.record-body {
  line-height: var(--leading-prose);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.source-disclosure summary {
  min-height: var(--touch-target);
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--cinnabar-deep);
  font-size: var(--text-body-sm);
}
@media (max-width: 600px) {
  .overview-row {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .overview-row :deep(button) {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
