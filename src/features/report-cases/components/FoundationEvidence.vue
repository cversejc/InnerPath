<template>
  <section class="foundation-evidence" :class="{ 'is-editable': editable, 'is-disabled': disabled }" :aria-disabled="disabled ? 'true' : null" :inert="disabled" aria-label="系统测算可视化">
    <p v-if="editable" class="calculation-edit-guidance">
      直接在命盘和对应页签中修订。四柱干支会同步到结构记录；日主信息、十神、五行、藏干、干支关系、大运和紫微不会自动重新排算，请逐项核对后保存。
    </p>
    <aside
      v-if="chart.assumptions.length"
      class="calculation-assumptions"
      aria-label="测算资料前提"
    >
      <strong>{{
        chart.assumptions.some((note) => /演示|假设/.test(note))
          ? "演示测算，出生资料须本人确认"
          : "本次测算采用了资料前提"
      }}</strong>
      <details>
        <summary>查看 {{ chart.assumptions.length }} 项前提</summary>
        <ul>
          <li v-for="note in chart.assumptions" :key="note">{{ note }}</li>
        </ul>
      </details>
    </aside>
    <p v-if="chart.limitations.length" class="calculation-limitations">
      待核对：{{ chart.limitations.join("；") }}
    </p>
    <template v-if="chart.hasChart">
      <nav class="foundation-tabs" aria-label="测算内容分类">
        <VanButton
          v-for="tab in tabs"
          :key="tab.id"
          plain
          native-type="button"
          :aria-pressed="section === tab.id"
          @click="section = tab.id"
          >{{ tab.label }}</VanButton
        >
      </nav>
      <div
        v-if="section === 'overview' || section === 'bazi'"
        class="foundation-section"
      >
        <div class="chart-heading">
          <h4>四柱对照</h4>
          <span v-if="chart.master && !editable">日主：{{ chart.master }}</span>
          <span v-else-if="editable">按柱位核对天干、地支与十神</span>
        </div>
        <div class="pillar-grid">
          <article
            v-for="pillar in chart.pillars"
            :key="pillar.key"
            class="pillar-card"
            :class="{ 'day-master': pillar.key === 'day' }"
          >
            <h5>{{ pillar.label }}</h5>
            <template v-if="editable">
              <div class="pillar-edit-pair">
                <label>
                  天干
                  <select :value="pillar.stem" :aria-label="`${pillar.label}天干`" @change="setPillarField(pillar.key, 'stem', $event.target.value)">
                    <option value="">选择天干</option>
                    <option v-for="stem in stems" :key="stem" :value="stem">{{ stem }}</option>
                  </select>
                </label>
                <label>
                  地支
                  <select :value="pillar.branch" :aria-label="`${pillar.label}地支`" @change="setPillarField(pillar.key, 'branch', $event.target.value)">
                    <option value="">选择地支</option>
                    <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
                  </select>
                </label>
              </div>
              <strong v-if="pillar.stem || pillar.branch" class="pillar-symbol">{{ pillar.stem }}{{ pillar.branch }}</strong>
              <label v-if="pillar.key !== 'day'">
                天干十神
                <select :value="pillar.ten_god" :aria-label="`${pillar.label}十神`" @change="setPillarField(pillar.key, 'ten_god', $event.target.value)">
                  <option value="">选择十神</option>
                  <option v-for="god in tenGods" :key="god" :value="god">{{ god }}</option>
                </select>
              </label>
              <p v-else class="chart-note">日柱天干为日主，请同时核对下方日主五行与阴阳</p>
            </template>
            <template v-else-if="pillar.available">
              <strong class="pillar-symbol">{{ pillar.stem }}{{ pillar.branch }}</strong>
              <p>{{ pillar.key === "day" ? "日主" : pillar.ten_god || "十神未记录" }}</p>
            </template>
            <p v-else>未计算</p>
            <div v-if="editable" class="pillar-edit-pair">
              <label>
                天干五行
                <select :value="pillar.stem_element" :aria-label="`${pillar.label}天干五行`" @change="setPillarField(pillar.key, 'stem_element', $event.target.value)">
                  <option value="">选择五行</option>
                  <option v-for="element in elements" :key="element" :value="element">{{ element }}</option>
                </select>
              </label>
              <label>
                地支五行
                <select :value="pillar.branch_element" :aria-label="`${pillar.label}地支五行`" @change="setPillarField(pillar.key, 'branch_element', $event.target.value)">
                  <option value="">选择五行</option>
                  <option v-for="element in elements" :key="element" :value="element">{{ element }}</option>
                </select>
              </label>
            </div>
            <p v-else-if="pillar.stem_element || pillar.branch_element">
              天干 {{ pillar.stem_element || "未记录" }} · 地支 {{ pillar.branch_element || "未记录" }}
            </p>
            <template v-if="section === 'bazi'">
              <h5 class="detail-heading">{{ pillar.label }}藏干</h5>
              <ul v-if="pillar.hidden_stems.length" class="hidden-stems">
                <li v-for="(hidden, index) in pillar.hidden_stems" :key="`${pillar.key}-${index}`">
                  <template v-if="editable">
                    <label>
                      天干
                      <select :value="hidden.stem" :aria-label="`${pillar.label}第${index + 1}个藏干`" @change="setHiddenStemField(pillar.key, index, 'stem', $event.target.value)">
                        <option value="">选择天干</option>
                        <option v-for="stem in stems" :key="stem" :value="stem">{{ stem }}</option>
                      </select>
                    </label>
                    <label>
                      五行
                      <select :value="hidden.element" :aria-label="`${pillar.label}第${index + 1}个藏干五行`" @change="setHiddenStemField(pillar.key, index, 'element', $event.target.value)">
                        <option value="">选择五行</option>
                        <option v-for="element in elements" :key="element" :value="element">{{ element }}</option>
                      </select>
                    </label>
                    <label>
                      十神
                      <select :value="hidden.ten_god" :aria-label="`${pillar.label}第${index + 1}个藏干十神`" @change="setHiddenStemField(pillar.key, index, 'ten_god', $event.target.value)">
                        <option value="">选择十神</option>
                        <option v-for="god in tenGods" :key="god" :value="god">{{ god }}</option>
                      </select>
                    </label>
                    <VanButton class="inline-remove" plain size="small" native-type="button" @click="removeHiddenStem(pillar.key, index)">移除</VanButton>
                  </template>
                  <template v-else>{{ hidden.stem }} · {{ hidden.element }} · {{ hidden.ten_god }}</template>
                </li>
              </ul>
              <p v-else-if="!editable">未记录藏干明细</p>
              <VanButton v-if="editable" class="inline-add" plain size="small" native-type="button" @click="addHiddenStem(pillar.key)">添加藏干</VanButton>
            </template>
          </article>
        </div>
        <dl v-if="!editable && chart.dates.length" class="chart-facts">
          <div v-for="[label, text] in chart.dates" :key="label">
            <dt>{{ label }}</dt>
            <dd>{{ text }}</dd>
          </div>
        </dl>
        <div v-else-if="editable" class="date-edit-grid">
          <label v-for="field in dateFields" :key="field.key">
            {{ field.label }}
            <input :value="value?.[field.key] || ''" :aria-label="field.label" @change="setDateField(field.key, $event.target.value)" />
          </label>
        </div>
        <div v-if="editable && section === 'bazi'" class="day-master-edit">
          <h4>日主信息</h4>
          <div class="pillar-edit-pair">
            <label>日主五行<select :value="value?.bazi_facts?.day_master?.element || ''" @change="setDayMasterField('element', $event.target.value)"><option value="">选择五行</option><option v-for="element in elements" :key="element" :value="element">{{ element }}</option></select></label>
            <label>日主阴阳<select :value="value?.bazi_facts?.day_master?.polarity || ''" @change="setDayMasterField('polarity', $event.target.value)"><option value="">选择阴阳</option><option value="阳">阳</option><option value="阴">阴</option></select></label>
          </div>
        </div>
        <template v-if="section === 'bazi' && chart.counts.length">
          <h4>十神出现次数</h4>
          <p class="chart-note">{{ chart.countNote }}（由当前录入的透干与藏干汇总）</p>
          <div class="chart-table-wrap">
            <table>
              <caption>透干与藏干对照</caption>
              <thead><tr><th scope="col">十神</th><th scope="col">透干</th><th scope="col">藏干</th></tr></thead>
              <tbody>
                <tr v-for="count in chart.counts" :key="count.name">
                  <th scope="row">{{ count.name }}</th><td>{{ count.visible }}</td><td>{{ count.hidden }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-if="section === 'overview' && chart.keyPalaces.length">
          <h4>紫微关键宫位</h4>
          <div class="palace-summary-grid">
            <article v-for="palace in chart.keyPalaces" :key="palace.label">
              <h5>{{ palace.label }} · {{ palace.branch }}</h5>
              <p>{{ palace.main_stars?.join("、") || "无主星" }}</p>
            </article>
          </div>
        </template>
      </div>
      <section v-else-if="section === 'relations'" class="foundation-section" aria-label="干支关系">
        <h4>干支关系对照</h4>
        <p>合与合化分开核对，解释结论在判断审核中确认。</p>
        <div v-if="chart.interactions.length" class="relation-list">
          <article v-for="(relation, index) in chart.interactions" :key="index">
            <template v-if="editable">
              <label>关系类型<select :value="relation.type" @change="setRelationField(index, 'type', $event.target.value)"><option value="">选择关系</option><option v-for="kind in relationTypes" :key="kind" :value="kind">{{ kind }}</option></select></label>
              <label>涉及干支<input :value="relation.symbols" @change="setRelationField(index, 'symbols', $event.target.value)" /></label>
              <fieldset class="position-editor"><legend>涉及柱位</legend><label v-for="item in pillarPositions" :key="item.key"><input type="checkbox" :checked="relation.pillars?.includes(item.key)" @change="setRelationPosition(index, item.key, $event.target.checked)" />{{ item.label }}</label></fieldset>
              <label class="relation-note-edit">备注<input :value="relation.note || ''" @change="setRelationField(index, 'note', $event.target.value)" placeholder="可留空" /></label>
              <VanButton class="inline-remove" plain size="small" native-type="button" @click="removeRelation(index)">移除此条</VanButton>
            </template>
            <template v-else>
              <strong>{{ relation.symbols }} · {{ relation.type }}</strong><span>{{ relation.positions }}</span>
              <p v-if="relation.note">{{ relation.note }}</p>
            </template>
          </article>
        </div>
        <p v-else>这份测算未记录干支关系。</p>
        <VanButton v-if="editable" class="inline-add" plain native-type="button" @click="addRelation">添加干支关系</VanButton>
      </section>
      <section v-else-if="section === 'dayun'" class="foundation-section" aria-label="大运时间轴">
        <h4>大运时间轴</h4>
        <p>按存储的测算年份排列，年龄沿用测算规则。阶段含义由咨询师另行判断。</p>
        <ol v-if="chart.dayun.length" class="dayun-timeline">
          <li v-for="(period, index) in chart.dayun" :key="index">
            <template v-if="editable">
              <label>大运干支<select :value="period.pillar" @change="setDayunField(index, 'pillar', $event.target.value)"><option value="">选择干支</option><option v-for="pillar in ganzhiOptions" :key="pillar" :value="pillar">{{ pillar }}</option></select></label>
              <strong>{{ period.pillar || '待填写' }}</strong>
              <label>十神<select :value="period.ten_god" @change="setDayunField(index, 'ten_god', $event.target.value)"><option value="">选择十神</option><option v-for="god in tenGods" :key="god" :value="god">{{ god }}</option></select></label>
              <div class="pillar-edit-pair"><label>天干五行<select :value="period.stem_element" @change="setDayunField(index, 'stem_element', $event.target.value)"><option value="">选择五行</option><option v-for="element in elements" :key="element" :value="element">{{ element }}</option></select></label><label>地支五行<select :value="period.branch_element" @change="setDayunField(index, 'branch_element', $event.target.value)"><option value="">选择五行</option><option v-for="element in elements" :key="element" :value="element">{{ element }}</option></select></label></div>
              <div class="period-number-grid"><label>开始年份<input type="number" :value="period.start_year" @change="setDayunField(index, 'start_year', $event.target.value)" /></label><label>结束年份<input type="number" :value="period.end_year" @change="setDayunField(index, 'end_year', $event.target.value)" /></label><label>开始年龄<input type="number" :value="period.start_age" @change="setDayunField(index, 'start_age', $event.target.value)" /></label><label>结束年龄<input type="number" :value="period.end_age" @change="setDayunField(index, 'end_age', $event.target.value)" /></label></div>
              <VanButton class="inline-remove" plain size="small" native-type="button" @click="removeDayun(index)">移除此步大运</VanButton>
            </template>
            <template v-else>
              <span>{{ period.start_year }}–{{ period.end_year }}</span><strong>{{ period.pillar }}</strong>
              <span>{{ period.ten_god }} · {{ period.stem_element }}/{{ period.branch_element }}</span><small>{{ period.start_age }}–{{ period.end_age }} 岁</small>
            </template>
          </li>
        </ol>
        <p v-else-if="!editable">这份测算未提供大运数据，请核对出生时间和性别等资料。</p>
        <VanButton v-if="editable" class="inline-add" plain native-type="button" @click="addDayun">添加大运阶段</VanButton>
      </section>
      <FoundationZiwei
        v-else-if="section === 'ziwei'"
        :chart="chart"
        :ziwei="value?.ziwei || {}"
        :editable="editable"
        @update:ziwei="setTopLevel('ziwei', $event)"
      />
      <section v-else class="foundation-section" aria-label="测算规则说明">
        <h4>计算规则与解释分工</h4>
        <dl class="convention-list">
          <div v-for="item in chart.conventions" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.text }}</dd></div>
        </dl>
        <p v-if="chart.note">{{ chart.note }}</p>
        <p>这里展示程序记录的排盘事实。格局、旺衰、喜忌和心理含义在相应分析与审核界面中处理。</p>
      </section>
    </template>
    <p v-else class="chart-fallback">{{ fallback || "当前测算没有可识别的命盘结构，可展开原始数据核对。" }}</p>
    <details v-if="!editable" class="calculation-raw">
      <summary>测算原始数据与技术标识（只读）</summary>
      <pre>{{ JSON.stringify(value, null, 2) }}</pre>
    </details>
  </section>
</template>

<script>
import { Button as VanButton } from "vant";
import { buildFoundationView } from "../foundation-presentation.js";
import FoundationZiwei from "./FoundationZiwei.vue";

const STEMS = [..."甲乙丙丁戊己庚辛壬癸"];
const BRANCHES = [..."子丑寅卯辰巳午未申酉戌亥"];
const TEN_GODS = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"];
const ELEMENTS = ["木", "火", "土", "金", "水"];
const RELATION_TYPES = ["六冲", "六合", "六害", "相刑", "自刑", "天干五合", "天干相克", "三合", "三会", "三刑"];
const PILLAR_POSITIONS = [{ key: "year", label: "年柱" }, { key: "month", label: "月柱" }, { key: "day", label: "日柱" }, { key: "hour", label: "时柱" }];
const DATE_FIELDS = [{ key: "solar_date", label: "公历" }, { key: "lunar_date", label: "农历" }, { key: "zodiac", label: "生肖" }, { key: "nayin", label: "纳音" }];

function clone(value) { return JSON.parse(JSON.stringify(value || {})); }
export default {
  components: { VanButton, FoundationZiwei },
  props: {
    value: { default: null },
    fallback: String,
    editable: Boolean,
    disabled: Boolean,
  },
  emits: ["update:value"],
  data: () => ({ section: "overview", stems: STEMS, branches: BRANCHES, tenGods: TEN_GODS, elements: ELEMENTS, relationTypes: RELATION_TYPES, pillarPositions: PILLAR_POSITIONS, dateFields: DATE_FIELDS }),
  computed: {
    chart() { return buildFoundationView(this.value); },
    tabs() {
      return [
        { id: "overview", label: "测算总览" }, { id: "bazi", label: "四柱与十神" },
        { id: "relations", label: "干支关系" }, { id: "dayun", label: "大运时间轴" },
        { id: "ziwei", label: "紫微宫位" }, { id: "notes", label: "测算说明" },
      ];
    },
    ganzhiOptions() {
      return Array.from({ length: 60 }, (_, index) => STEMS[index % 10] + BRANCHES[index % 12]);
    },
  },
  methods: {
    commit(mutator) {
      const next = clone(this.value);
      mutator(next);
      this.$emit("update:value", next);
    },
    setTopLevel(field, value) { this.commit((next) => { next[field] = value; }); },
    setDateField(field, value) { this.setTopLevel(field, value); },
    setPillarField(key, field, value) {
      this.commit((next) => {
        const bazi = next.bazi || next;
        const facts = next.bazi_facts || (next.bazi_facts = {});
        facts.pillars = facts.pillars || {};
        if (field === "stem" || field === "branch") {
          bazi[key] = { ...(bazi[key] || {}), [field]: value };
          if (facts.pillars[key]) facts.pillars[key][field] = value;
          this.syncPillarStructure(next);
          return;
        }
        bazi[key] = { ...(bazi[key] || {}) };
        const fact = facts.pillars[key] || (facts.pillars[key] = { ...bazi[key], hidden_stems: [] });
        fact[field] = value;
        if (field === "ten_god") bazi[key].ten_god = value;
        if (key === "day" && field === "stem_element") this.setDayMasterInRecord(next, "element", value);
        if (field === "ten_god") {
          this.updateTenGodCounts(next);
          return;
        }
        this.updateTenGodCounts(next);
      });
    },
    setDayMasterField(field, value) { this.commit((next) => { this.setDayMasterInRecord(next, field, value); }); },
    setDayMasterInRecord(next, field, value) {
      const facts = next.bazi_facts || (next.bazi_facts = {});
      facts.day_master = { ...(facts.day_master || {}), [field]: value };
    },
    syncPillarStructure(next) {
      const bazi = next.bazi || next;
      const facts = next.bazi_facts || (next.bazi_facts = {});
      facts.pillars = facts.pillars || {};
      const master = bazi.day?.stem || bazi.day_master || "";
      if (bazi.day) bazi.day_master = master;
      if (!facts.day_master || typeof facts.day_master !== "object") facts.day_master = {};
      if (master) facts.day_master.stem = master;
      for (const { key } of PILLAR_POSITIONS) {
        const chartPillar = bazi[key];
        let fact = facts.pillars[key];
        if (!chartPillar && !fact) continue;
        const stem = chartPillar?.stem ?? fact?.stem ?? "";
        const branch = chartPillar?.branch ?? fact?.branch ?? "";
        if (!fact && chartPillar && stem && branch) {
          fact = facts.pillars[key] = { ...chartPillar, hidden_stems: [] };
        }
        if (chartPillar) {
          chartPillar.stem = stem;
          chartPillar.branch = branch;
          chartPillar.pillar = `${stem}${branch}`;
        }
        if (fact) {
          fact.stem = stem;
          fact.branch = branch;
          fact.pillar = `${stem}${branch}`;
        }
      }
      next.bazi_facts = facts;
      this.updateTenGodCounts(next);
    },
    updateTenGodCounts(next) {
      const facts = next.bazi_facts || (next.bazi_facts = {});
      const visible = {};
      const hidden = {};
      for (const { key } of PILLAR_POSITIONS) {
        if (key !== "day") {
          const god = facts.pillars?.[key]?.ten_god || (next.bazi || next)[key]?.ten_god;
          if (god) visible[god] = (visible[god] || 0) + 1;
        }
        for (const item of facts.pillars?.[key]?.hidden_stems || []) {
          if (item.ten_god) hidden[item.ten_god] = (hidden[item.ten_god] || 0) + 1;
        }
      }
      facts.ten_god_counts = { ...(facts.ten_god_counts || {}), visible, hidden, absent: TEN_GODS.filter((god) => !visible[god] && !hidden[god]) };
    },
    setHiddenStemField(key, index, field, value) {
      this.commit((next) => {
        const items = next.bazi_facts?.pillars?.[key]?.hidden_stems;
        if (!items?.[index]) return;
        items[index][field] = value;
        if (index === 0) next.bazi_facts.pillars[key].branch_ten_god = items[index].ten_god;
        this.updateTenGodCounts(next);
      });
    },
    addHiddenStem(key) {
      this.commit((next) => {
        const pillar = next.bazi_facts?.pillars?.[key];
        if (pillar) pillar.hidden_stems = [...(pillar.hidden_stems || []), { stem: "", element: "", ten_god: "" }];
      });
    },
    removeHiddenStem(key, index) {
      this.commit((next) => {
        const pillar = next.bazi_facts?.pillars?.[key];
        if (!pillar) return;
        pillar.hidden_stems = (pillar.hidden_stems || []).filter((_, itemIndex) => itemIndex !== index);
        pillar.branch_ten_god = pillar.hidden_stems[0]?.ten_god || "";
        this.updateTenGodCounts(next);
      });
    },
    setRelationField(index, field, value) {
      this.commit((next) => { if (next.bazi_facts?.interactions?.[index]) next.bazi_facts.interactions[index][field] = value; });
    },
    setRelationPosition(index, key, checked) {
      this.commit((next) => {
        const relation = next.bazi_facts?.interactions?.[index];
        if (!relation) return;
        const positions = new Set(relation.pillars || []);
        checked ? positions.add(key) : positions.delete(key);
        relation.pillars = PILLAR_POSITIONS.map((item) => item.key).filter((item) => positions.has(item));
      });
    },
    addRelation() {
      this.commit((next) => { const facts = next.bazi_facts || (next.bazi_facts = {}); facts.interactions = [...(facts.interactions || []), { type: "", symbols: "", pillars: [], note: "" }]; });
    },
    removeRelation(index) {
      this.commit((next) => { if (next.bazi_facts) next.bazi_facts.interactions = (next.bazi_facts.interactions || []).filter((_, itemIndex) => itemIndex !== index); });
    },
    setDayunField(index, field, rawValue) {
      this.commit((next) => {
        const period = next.bazi_facts?.dayun?.[index];
        if (!period) return;
        const value = ["start_year", "end_year", "start_age", "end_age"].includes(field) && rawValue !== "" ? Number(rawValue) : rawValue;
        period[field] = value;
      });
    },
    addDayun() {
      this.commit((next) => { const facts = next.bazi_facts || (next.bazi_facts = {}); facts.dayun = [...(facts.dayun || []), { pillar: "", start_year: "", end_year: "", start_age: "", end_age: "", ten_god: "", stem_element: "", branch_element: "" }]; });
    },
    removeDayun(index) {
      this.commit((next) => { if (next.bazi_facts) next.bazi_facts.dayun = (next.bazi_facts.dayun || []).filter((_, itemIndex) => itemIndex !== index); });
    },
  },
};
</script>
<style src="./FoundationEvidence.css"></style>
