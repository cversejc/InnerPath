<template>
  <section class="foundation-evidence" aria-label="系统测算可视化">
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
          <span v-if="chart.master">日主：{{ chart.master }}</span>
        </div>
        <div class="pillar-grid">
          <article
            v-for="pillar in chart.pillars"
            :key="pillar.key"
            class="pillar-card"
            :class="{ 'day-master': pillar.key === 'day' }"
          >
            <h5>{{ pillar.label }}</h5>
            <template v-if="pillar.available"
              ><strong class="pillar-symbol"
                >{{ pillar.stem }}{{ pillar.branch }}</strong
              >
              <p>
                {{
                  pillar.key === "day" ? "日主" : pillar.ten_god || "十神未记录"
                }}
              </p>
              <p v-if="pillar.stem_element || pillar.branch_element">
                天干 {{ pillar.stem_element || "未记录" }} · 地支
                {{ pillar.branch_element || "未记录" }}
              </p>
              <ul
                v-if="section === 'bazi' && pillar.hidden_stems.length"
                class="hidden-stems"
              >
                <li v-for="stem in pillar.hidden_stems" :key="stem.stem">
                  {{ stem.stem }} · {{ stem.element }} · {{ stem.ten_god }}
                </li>
              </ul>
              <p v-else-if="section === 'bazi'">未记录藏干明细</p></template
            >
            <p v-else>未计算</p>
          </article>
        </div>
        <dl v-if="chart.dates.length" class="chart-facts">
          <div v-for="[label, text] in chart.dates" :key="label">
            <dt>{{ label }}</dt>
            <dd>{{ text }}</dd>
          </div>
        </dl>
        <template v-if="section === 'bazi' && chart.counts.length"
          ><h4>十神出现次数</h4>
          <p class="chart-note">{{ chart.countNote }}</p>
          <div class="chart-table-wrap">
            <table>
              <caption>
                透干与藏干对照
              </caption>
              <thead>
                <tr>
                  <th scope="col">十神</th>
                  <th scope="col">透干</th>
                  <th scope="col">藏干</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="count in chart.counts" :key="count.name">
                  <th scope="row">{{ count.name }}</th>
                  <td>{{ count.visible }}</td>
                  <td>{{ count.hidden }}</td>
                </tr>
              </tbody>
            </table>
          </div></template
        >
        <template v-if="section === 'overview' && chart.keyPalaces.length"
          ><h4>紫微关键宫位</h4>
          <div class="palace-summary-grid">
            <article v-for="palace in chart.keyPalaces" :key="palace.label">
              <h5>{{ palace.label }} · {{ palace.branch }}</h5>
              <p>{{ palace.main_stars?.join("、") || "无主星" }}</p>
            </article>
          </div></template
        >
      </div>
      <section
        v-else-if="section === 'relations'"
        class="foundation-section"
        aria-label="干支关系"
      >
        <h4>干支关系对照</h4>
        <p>合与合化分开核对，解释结论在判断审核中确认。</p>
        <div v-if="chart.interactions.length" class="relation-list">
          <article v-for="(relation, index) in chart.interactions" :key="index">
            <strong>{{ relation.symbols }} · {{ relation.type }}</strong
            ><span>{{ relation.positions }}</span>
            <p v-if="relation.note">{{ relation.note }}</p>
          </article>
        </div>
        <p v-else>这份测算未记录干支关系。</p>
      </section>
      <section
        v-else-if="section === 'dayun'"
        class="foundation-section"
        aria-label="大运时间轴"
      >
        <h4>大运时间轴</h4>
        <p>
          按存储的测算年份排列，年龄沿用测算规则。阶段含义由咨询师另行判断。
        </p>
        <ol v-if="chart.dayun.length" class="dayun-timeline">
          <li v-for="(period, index) in chart.dayun" :key="index">
            <span>{{ period.start_year }}–{{ period.end_year }}</span
            ><strong>{{ period.pillar }}</strong
            ><span
              >{{ period.ten_god }} · {{ period.stem_element }}/{{
                period.branch_element
              }}</span
            ><small>{{ period.start_age }}–{{ period.end_age }} 岁</small>
          </li>
        </ol>
        <p v-else>这份测算未提供大运数据，请核对出生时间和性别等资料。</p>
      </section>
      <FoundationZiwei v-else-if="section === 'ziwei'" :chart="chart" />
      <section v-else class="foundation-section" aria-label="测算规则说明">
        <h4>计算规则与解释分工</h4>
        <dl class="convention-list">
          <div v-for="item in chart.conventions" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.text }}</dd>
          </div>
        </dl>
        <p v-if="chart.note">{{ chart.note }}</p>
        <p>
          这里展示程序记录的排盘事实。格局、旺衰、喜忌和心理含义在相应分析与审核界面中处理。
        </p>
      </section>
    </template>
    <p v-else class="chart-fallback">
      {{ fallback || "当前测算没有可识别的命盘结构，可展开原始数据核对。" }}
    </p>
    <details class="calculation-raw">
      <summary>测算原始数据与技术标识</summary>
      <pre>{{ JSON.stringify(value, null, 2) }}</pre>
    </details>
  </section>
</template>
<script>
import { Button as VanButton } from "vant";
import { buildFoundationView } from "../foundation-presentation.js";
import FoundationZiwei from "./FoundationZiwei.vue";
export default {
  components: { VanButton, FoundationZiwei },
  props: { value: { default: null }, fallback: String },
  data: () => ({ section: "overview" }),
  computed: {
    chart() {
      return buildFoundationView(this.value);
    },
    tabs() {
      return [
        { id: "overview", label: "测算总览" },
        { id: "bazi", label: "四柱与十神" },
        { id: "relations", label: "干支关系" },
        { id: "dayun", label: "大运时间轴" },
        { id: "ziwei", label: "紫微宫位" },
        { id: "notes", label: "测算说明" },
      ];
    },
  },
};
</script>
<style src="./FoundationEvidence.css"></style>
