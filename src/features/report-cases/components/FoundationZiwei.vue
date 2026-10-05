<template>
  <section class="foundation-section" aria-label="紫微宫位与四化">
    <h4>紫微宫位对照</h4>
    <dl v-if="chart.ziweiSummary.length || editable" class="chart-facts">
      <div v-for="field in summaryFields" :key="field.key">
        <dt>{{ field.label }}</dt>
        <dd v-if="editable"><input :value="ziwei[field.key] || ''" :aria-label="field.label" @change="setSummary(field.key, $event.target.value)" /></dd>
        <dd v-else>{{ ziwei[field.key] || '未记录' }}</dd>
      </div>
    </dl>
    <div v-if="chart.palaces.length" class="palace-grid">
      <article
        v-for="(palace, index) in chart.palaces"
        :key="index"
        :class="{
          'key-palace': chart.keyPalaces.some(
            (item) => item.branch === palace.branch,
          ),
        }"
      >
        <template v-if="editable">
          <label>宫位名称<input :value="palace.name" @change="setPalaceField(index, 'name', $event.target.value)" /></label>
          <div class="pillar-edit-pair">
            <label>宫干<select :value="palace.stem || ''" @change="setPalaceField(index, 'stem', $event.target.value)"><option value="">选择天干</option><option v-for="stem in stems" :key="stem" :value="stem">{{ stem }}</option></select></label>
            <label>宫支<select :value="palace.branch || ''" @change="setPalaceField(index, 'branch', $event.target.value)"><option value="">选择地支</option><option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option></select></label>
          </div>
          <label>主星<input :value="(palace.main_stars || []).join('、')" @change="setPalaceList(index, 'main_stars', $event.target.value)" placeholder="多个星曜用顿号分开" /></label>
          <label>辅星<input :value="(palace.aux_stars || []).join('、')" @change="setPalaceList(index, 'aux_stars', $event.target.value)" placeholder="多个星曜用顿号分开" /></label>
          <details v-if="Object.keys(palace.brightness || {}).length || Object.keys(palace.sihua || {}).length">
            <summary>修订亮度与生年四化</summary>
            <label v-for="(value, star) in palace.brightness" :key="`bright-${star}`">{{ star }}亮度<input :value="value" @change="setPalaceMap(index, 'brightness', star, $event.target.value)" /></label>
            <label v-for="(value, star) in palace.sihua" :key="`sihua-${star}`">{{ star }}四化<select :value="value" @change="setPalaceMap(index, 'sihua', star, $event.target.value)"><option value="">未记录</option><option v-for="type in transformationTypes" :key="type" :value="type">化{{ type }}</option></select></label>
          </details>
        </template>
        <template v-else>
          <h5>{{ palace.name }} · {{ palace.stem }}{{ palace.branch }}</h5>
          <span v-if="chart.keyPalaces.some((item) => item.label === '身宫' && item.branch === palace.branch)" class="chart-note">身宫所在</span>
          <p>{{ palace.main_stars?.join("、") || "无主星" }}</p>
          <p v-if="palace.aux_stars?.length" class="chart-note">辅星：{{ palace.aux_stars.join("、") }}</p>
          <details v-if="Object.keys(palace.brightness || {}).length || Object.keys(palace.sihua || {}).length">
            <summary>亮度与生年四化</summary>
            <p v-for="(value, star) in palace.brightness" :key="star">{{ star }} · {{ value }}<span v-if="palace.sihua?.[star]"> · 化{{ palace.sihua[star] }}</span></p>
            <p v-for="(value, star) in palace.sihua" v-show="!palace.brightness?.[star]" :key="`sihua-${star}`">{{ star }} · 化{{ value }}</p>
          </details>
        </template>
      </article>
    </div>
    <div v-else-if="chart.keyPalaces.length" class="palace-summary-grid">
      <article v-for="palace in chart.keyPalaces" :key="palace.label">
        <template v-if="editable">
          <h5>{{ palace.label }}</h5>
          <label>宫支<select :value="palace.branch || ''" @change="setKeyPalaceField(palace.label, 'branch', $event.target.value)"><option value="">选择地支</option><option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option></select></label>
          <label>主星<input :value="(palace.main_stars || []).join('、')" @change="setKeyPalaceList(palace.label, 'main_stars', $event.target.value)" /></label>
        </template>
        <template v-else><h5>{{ palace.label }} · {{ palace.branch }}</h5><p>{{ palace.main_stars?.join("、") || "无主星" }}</p></template>
      </article>
    </div>
    <p v-else>这份测算未提供紫微宫位，不补造星曜。</p>
    <p v-if="chart.sanfang.length" class="chart-note">命宫三方四正：{{ chart.sanfang.join("、") }}</p>
    <template v-if="chart.yearTransformations.length || editable">
      <h4>生年四化</h4>
      <div class="year-transformations">
        <label v-for="item in chart.yearTransformations" :key="item.star">
          <template v-if="editable">{{ item.star }}<select :value="item.type" @change="setYearTransformation(item.star, $event.target.value)"><option v-for="type in transformationTypes" :key="type" :value="type">化{{ type }}</option></select></template>
          <template v-else>{{ item.star }} · 化{{ item.type }}</template>
        </label>
        <p v-if="editable && !chart.yearTransformations.length" class="chart-note">这份测算未记录生年四化。</p>
      </div>
    </template>
    <template v-if="chart.transformations.length">
      <div class="chart-heading">
        <h4>宫干飞化去向</h4>
        <label>来源宫位<select v-model="source">
          <option value="">全部宫位 · {{ chart.transformations.length }} 条</option>
          <option v-for="name in chart.palaceSources" :key="name" :value="name">{{ name }}</option>
        </select></label>
      </div>
      <p class="chart-note">{{ paths.length }} 条记录 · 宫干飞化与生年四化分别呈现</p>
      <div class="transformation-list">
        <article v-for="(path, index) in paths" :key="index">
          <template v-if="editable">
            <label>来源宫<input :value="path.source_palace" @change="setTransformation(path._sourceIndex, 'source_palace', $event.target.value)" /></label>
            <label>宫干<select :value="path.source_stem" @change="setTransformation(path._sourceIndex, 'source_stem', $event.target.value)"><option value="">选择天干</option><option v-for="stem in stems" :key="stem" :value="stem">{{ stem }}</option></select></label>
            <label>四化<select :value="path.transformation" @change="setTransformation(path._sourceIndex, 'transformation', $event.target.value)"><option v-for="type in transformationTypes" :key="type" :value="type">化{{ type }}</option></select></label>
            <label>星曜<input :value="path.star" @change="setTransformation(path._sourceIndex, 'star', $event.target.value)" /></label>
            <label>落宫<input :value="(path.target_palaces || []).join('、')" @change="setTransformationTargets(path._sourceIndex, $event.target.value)" /></label>
          </template>
          <template v-else><span>{{ path.source }} · {{ path.source_stem }}</span><strong>化{{ path.transformation }} · {{ path.star }}</strong><span>→ {{ path.targets }}</span></template>
        </article>
      </div>
    </template>
  </section>
</template>

<script>
const BRANCHES = [..."子丑寅卯辰巳午未申酉戌亥"];
const STEMS = [..."甲乙丙丁戊己庚辛壬癸"];
const SUMMARY_FIELDS = [{ key: "ming_zhu", label: "命主" }, { key: "shen_zhu", label: "身主" }, { key: "wu_xing_ju", label: "五行局" }];
const ALIASES = { "命宫": "life_palace", "身宫": "body_palace", "福德宫": "wellbeing_palace", "官禄宫": "career_palace", "财帛宫": "wealth_palace", "夫妻宫": "relationship_palace" };
const TRANSFORMATION_TYPES = ["禄", "权", "科", "忌"];
const clone = (value) => JSON.parse(JSON.stringify(value || {}));
const parseList = (value) => value.split(/[、,，\s]+/).map((item) => item.trim()).filter(Boolean);

export default {
  props: { chart: { type: Object, required: true }, ziwei: { type: Object, default: () => ({}) }, editable: Boolean },
  emits: ["update:ziwei"],
  data() {
    return { source: this.chart.palaceSources.find((name) => name === "命宫") || this.chart.palaceSources[0] || "", branches: BRANCHES, stems: STEMS, summaryFields: SUMMARY_FIELDS, transformationTypes: TRANSFORMATION_TYPES };
  },
  watch: {
    editable(value) { if (value) this.source = ""; },
  },
  computed: {
    paths() { return this.chart.transformations.map((item, index) => ({ ...item, _sourceIndex: index })).filter((item) => !this.source || item.source === this.source); },
  },
  methods: {
    commit(mutator) { const next = clone(this.ziwei); mutator(next); this.$emit("update:ziwei", next); },
    setSummary(field, value) { this.commit((next) => { next[field] = value; }); },
    setPalaceField(index, field, value) {
      this.commit((next) => {
        const palace = next.palaces?.[index];
        if (!palace) return;
        const previous = { ...palace };
        palace[field] = value;
        this.syncPalaceAliases(next, previous, palace);
      });
    },
    setPalaceList(index, field, value) { this.setPalaceField(index, field, parseList(value)); },
    setPalaceMap(index, field, star, value) { this.commit((next) => { const palace = next.palaces?.[index]; if (palace) palace[field] = { ...(palace[field] || {}), [star]: value }; }); },
    setKeyPalaceField(label, field, value) { const alias = ALIASES[label]; if (alias) this.commit((next) => { next[alias] = { ...(next[alias] || {}), [field]: value }; }); },
    setKeyPalaceList(label, field, value) { const alias = ALIASES[label]; if (alias) this.commit((next) => { next[alias] = { ...(next[alias] || {}), [field]: parseList(value) }; }); },
    syncPalaceAliases(next, previous, palace) {
      for (const alias of Object.values(ALIASES)) {
        const current = next[alias];
        if (current && (current.branch === previous.branch || current.name === previous.name)) next[alias] = { ...current, ...palace, name: current.name || palace.name };
      }
      if (Array.isArray(next.life_sanfang_sizheng)) {
        next.life_sanfang_sizheng = next.life_sanfang_sizheng.map((item) => item && (item.branch === previous.branch || item.name === previous.name) ? { ...item, ...palace } : item);
      }
    },
    setYearTransformation(star, value) { this.commit((next) => { next.year_transformations = { ...(next.year_transformations || {}), [star]: value }; }); },
    setTransformation(index, field, value) { this.commit((next) => { if (next.flying_transformations?.[index]) next.flying_transformations[index][field] = value; }); },
    setTransformationTargets(index, value) { this.setTransformation(index, "target_palaces", parseList(value)); },
  },
};
</script>
