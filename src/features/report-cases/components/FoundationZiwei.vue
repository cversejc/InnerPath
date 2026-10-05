<template>
  <section class="foundation-section" aria-label="紫微宫位与四化">
    <h4>紫微宫位对照</h4>
    <dl v-if="chart.ziweiSummary.length" class="chart-facts">
      <div v-for="[label, text] in chart.ziweiSummary" :key="label">
        <dt>{{ label }}</dt>
        <dd>{{ text }}</dd>
      </div>
    </dl>
    <div v-if="chart.palaces.length" class="palace-grid">
      <article
        v-for="palace in chart.palaces"
        :key="palace.name"
        :class="{
          'key-palace': chart.keyPalaces.some(
            (item) => item.branch === palace.branch,
          ),
        }"
      >
        <h5>{{ palace.name }} · {{ palace.stem }}{{ palace.branch }}</h5>
        <span
          v-if="
            chart.keyPalaces.some(
              (item) => item.label === '身宫' && item.branch === palace.branch,
            )
          "
          class="chart-note"
          >身宫所在</span
        >
        <p>{{ palace.main_stars?.join("、") || "无主星" }}</p>
        <p v-if="palace.aux_stars?.length" class="chart-note">
          辅星：{{ palace.aux_stars.join("、") }}
        </p>
        <details
          v-if="
            Object.keys(palace.brightness || {}).length ||
            Object.keys(palace.sihua || {}).length
          "
        >
          <summary>亮度与生年四化</summary>
          <p v-for="(value, star) in palace.brightness" :key="star">
            {{ star }} · {{ value
            }}<span v-if="palace.sihua?.[star]">
              · 化{{ palace.sihua[star] }}</span
            >
          </p>
          <p
            v-for="(value, star) in palace.sihua"
            v-show="!palace.brightness?.[star]"
            :key="`sihua-${star}`"
          >
            {{ star }} · 化{{ value }}
          </p>
        </details>
      </article>
    </div>
    <div v-else-if="chart.keyPalaces.length" class="palace-summary-grid">
      <article v-for="palace in chart.keyPalaces" :key="palace.label">
        <h5>{{ palace.label }} · {{ palace.branch }}</h5>
        <p>{{ palace.main_stars?.join("、") || "无主星" }}</p>
      </article>
    </div>
    <p v-else>这份测算未提供紫微宫位，不补造星曜。</p>
    <p v-if="chart.sanfang.length" class="chart-note">
      命宫三方四正：{{ chart.sanfang.join("、") }}
    </p>
    <template v-if="chart.yearTransformations.length"
      ><h4>生年四化</h4>
      <div class="year-transformations">
        <span v-for="item in chart.yearTransformations" :key="item.star"
          >{{ item.star }} · 化{{ item.type }}</span
        >
      </div></template
    >
    <template v-if="chart.transformations.length">
      <div class="chart-heading">
        <h4>宫干飞化去向</h4>
        <label
          >来源宫位<select v-model="source">
            <option value="">
              全部宫位 · {{ chart.transformations.length }} 条
            </option>
            <option
              v-for="name in chart.palaceSources"
              :key="name"
              :value="name"
            >
              {{ name }}
            </option>
          </select></label
        >
      </div>
      <p class="chart-note">
        {{ paths.length }} 条记录 · 宫干飞化与生年四化分别呈现
      </p>
      <div class="transformation-list">
        <article v-for="(path, index) in paths" :key="index">
          <span>{{ path.source }} · {{ path.source_stem }}</span
          ><strong>化{{ path.transformation }} · {{ path.star }}</strong
          ><span>→ {{ path.targets }}</span>
        </article>
      </div>
    </template>
  </section>
</template>
<script>
export default {
  props: { chart: { type: Object, required: true } },
  data() {
    return {
      source:
        this.chart.palaceSources.find((name) => name === "命宫") ||
        this.chart.palaceSources[0] ||
        "",
    };
  },
  computed: {
    paths() {
      return this.chart.transformations.filter(
        (item) => !this.source || item.source === this.source,
      );
    },
  },
};
</script>
