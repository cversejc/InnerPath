<template>
  <section class="examples-panel">
    <div class="examples-toolbar">
      <div>
        <h2>{{ admin ? "示例维护与审核" : "已发布参考示例" }}</h2>
        <p>学习分析方法与表达，不把示例中的经历套用到当前用户。</p>
      </div>
      <div v-if="admin" class="examples-filters">
        <label for="example-status">状态</label>
        <select id="example-status" v-model="filter" @change="loadExamples">
          <option value="">全部</option>
          <option value="CANDIDATE">待审核</option>
          <option value="PUBLISHED">已发布</option>
          <option value="RETIRED">已停用</option>
        </select>
        <VanButton
          class="secondary-button compact-button"
          type="default"
          plain
          :disabled="loading"
          @click="loadExamples"
          >刷新</VanButton
        >
      </div>
    </div>

    <p v-if="error" class="examples-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="examples-notice" role="status">{{ notice }}</p>

    <label class="example-selector"
      >选择示例<select
        :value="selected?.id || ''"
        @change="selectExampleById($event.target.value)"
      >
        <option v-if="!selected" value="">暂无选中的示例</option>
        <option
          v-for="example in examples"
          :key="example.id"
          :value="example.id"
        >
          {{ exampleTitle(example) }} · 第 {{ example.version_no }} 版 ·
          {{ statusLabel(example.status) }}
        </option>
      </select></label
    >
    <p v-if="!loading && !examples.length" class="examples-empty">
      {{
        admin
          ? "当前筛选没有示例，可切换状态查看已发布内容。"
          : "该技能暂无已发布示例。"
      }}
    </p>
    <div class="examples-layout">
      <form
        v-if="selected"
        class="example-editor"
        @submit.prevent="saveCandidate"
      >
        <div class="example-editor-heading">
          <div>
            <p class="eyebrow">
              示例 {{ selected.id }} · 第 {{ selected.version_no }} 版
            </p>
            <h3>{{ skillInfo(selected.skill_key).name }}</h3>
          </div>
          <span
            class="version-state"
            :class="`state-${selected.status.toLowerCase()}`"
            >{{ statusLabel(selected.status) }}</span
          >
        </div>
        <p>
          {{ displayText(selected.example_type) }} ·
          {{
            selected.scenario_tags?.map(displayText).join("、") || "通用情境"
          }}
        </p>
        <details>
          <summary>来源与版本信息</summary>
          <dl class="example-source">
            <div>
              <dt>来源报告案例</dt>
              <dd>{{ selected.source_case_id || "合成教学示例" }}</dd>
            </div>
            <div>
              <dt>来源运行记录</dt>
              <dd>{{ selected.source_skill_run_id || "—" }}</dd>
            </div>
            <div>
              <dt>审核人</dt>
              <dd>{{ selected.reviewed_by || "未审核" }}</dd>
            </div>
          </dl>
          <code
            >{{ selected.skill_key }} ·
            {{ selected.target_fragment_key || "不限段落" }}</code
          >
        </details>

        <div class="example-readonly-block">
          <strong>输入情境</strong
          ><ReadableData
            :value="
              admin && selected.status === 'CANDIDATE'
                ? previewObject(draft.inputContext)
                : selected.input_context
            "
          />
        </div>
        <div class="example-readonly-block">
          <strong>参考输出</strong
          ><ReadableData
            :value="
              admin && selected.status === 'CANDIDATE'
                ? previewObject(draft.expectedOutput)
                : selected.expected_output
            "
          />
        </div>

        <template v-if="admin && selected.status === 'CANDIDATE'">
          <details>
            <summary>适用范围与结构化内容维护</summary>
            <label for="example-fragment">目标片段标识（可留空）</label>
            <input
              id="example-fragment"
              v-model.trim="draft.target_fragment_key"
              maxlength="200"
            />
            <label for="example-tags">情境标签</label>
            <input
              id="example-tags"
              v-model="draft.scenarioTags"
              placeholder="例如：职业、决策（逗号分隔）"
            />
            <label for="example-applicability">适用条件 JSON</label>
            <textarea
              id="example-applicability"
              v-model="draft.applicability"
              rows="3"
              spellcheck="false"
            ></textarea>
            <label for="example-input">脱敏输入情境 JSON</label>
            <textarea
              id="example-input"
              v-model="draft.inputContext"
              rows="5"
              spellcheck="false"
            ></textarea>
            <label for="example-output">期望输出 JSON</label>
            <textarea
              id="example-output"
              v-model="draft.expectedOutput"
              rows="6"
              spellcheck="false"
            ></textarea>
          </details>
          <label for="example-teaching">教学要点（每行一项）</label>
          <textarea
            id="example-teaching"
            v-model="draft.teachingPoints"
            rows="3"
          ></textarea>
          <label for="example-anti-patterns">反例模式（每行一项）</label>
          <textarea
            id="example-anti-patterns"
            v-model="draft.antiPatterns"
            rows="3"
          ></textarea>
          <div class="example-review-fields">
            <label for="example-quality">质量评分</label>
            <input
              id="example-quality"
              v-model.number="draft.qualityScore"
              type="number"
              min="0"
              max="1"
              step="0.01"
              required
            />
            <label class="deidentification-check"
              ><input v-model="draft.deidentified" type="checkbox" />
              已完成人工脱敏复核</label
            >
          </div>
          <div class="example-actions">
            <VanButton
              class="secondary-button compact-button"
              type="default"
              plain
              :disabled="busy"
              native-type="submit"
              :loading="busy"
              >保存审核内容</VanButton
            >
            <VanButton
              class="primary-button compact-button"
              type="primary"
              :disabled="
                busy ||
                !selected.deidentified ||
                selected.quality_score < 0.6 ||
                !selected.teaching_points?.length
              "
              :loading="busy"
              @click.prevent="publishSelected"
              >审核并发布</VanButton
            >
          </div>
        </template>

        <template v-else>
          <div class="example-readonly-block">
            <strong>教学要点</strong>
            <ul>
              <li
                v-for="(point, index) in selected.teaching_points"
                :key="index"
              >
                {{ displayText(point) }}
              </li>
            </ul>
          </div>
          <div
            v-if="selected.anti_patterns?.length"
            class="example-readonly-block"
          >
            <strong>需要避免</strong>
            <ul>
              <li v-for="(point, index) in selected.anti_patterns" :key="index">
                {{ displayText(point) }}
              </li>
            </ul>
          </div>
          <details>
            <summary>适用条件与原始结构</summary>
            <ReadableData :value="selected.applicability_json || {}" />
            <pre>{{
              JSON.stringify(
                {
                  applicability: selected.applicability_json,
                  input: selected.input_context,
                  output: selected.expected_output,
                },
                null,
                2,
              )
            }}</pre>
          </details>
          <div v-if="admin" class="example-actions">
            <VanButton
              v-if="
                selected.status === 'PUBLISHED' || selected.status === 'RETIRED'
              "
              class="secondary-button compact-button"
              type="default"
              plain
              :disabled="busy"
              @click="createRevision"
              >创建新版本</VanButton
            >
            <VanButton
              v-if="selected.status !== 'RETIRED'"
              class="secondary-button compact-button"
              type="default"
              plain
              :disabled="busy"
              @click="retireSelected"
              >停用示例</VanButton
            >
          </div>
        </template>
      </form>
      <div v-else-if="examples.length" class="example-editor-empty">
        选择一条示例查看审核信息。
      </div>
    </div>
  </section>
</template>

<script>
import { Button as VanButton } from "vant";
import api from "../api.js";
import ReadableData from "./ReadableData.vue";
import { skillInfo, displayText } from "../presentation.js";

function lines(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function emptyDraft() {
  return {
    target_fragment_key: "",
    scenarioTags: "",
    applicability: "{}",
    inputContext: "{}",
    expectedOutput: "{}",
    teachingPoints: "",
    antiPatterns: "",
    qualityScore: 0.8,
    deidentified: false,
  };
}

export default {
  name: "ExamplesPanel",
  components: { VanButton, ReadableData },
  props: {
    admin: { type: Boolean, default: true },
    skillKey: { type: String, default: "" },
  },
  data() {
    return {
      examples: [],
      selected: null,
      filter: "",
      loading: false,
      busy: false,
      error: "",
      notice: "",
      draft: emptyDraft(),
    };
  },
  mounted() {
    this.loadExamples();
  },
  watch: {
    skillKey() {
      this.loadExamples();
    },
  },
  methods: {
    skillInfo,
    displayText,
    exampleTitle(example) {
      return displayText(
        example.teaching_points?.[0] ||
          `${skillInfo(example.skill_key).name}示例 ${example.id}`,
      );
    },
    selectExampleById(id) {
      const example = this.examples.find((item) => item.id === Number(id));
      if (example) this.selectExample(example);
    },
    previewObject(text) {
      try {
        return JSON.parse(text);
      } catch {
        return "结构化内容格式有误，请展开维护内容修正。";
      }
    },
    async loadExamples() {
      this.loading = true;
      this.error = "";
      try {
        if (this.admin) {
          const params = {
            status: this.filter || undefined,
            skill_key: this.skillKey || undefined,
          };
          this.examples = await api.getSkillExamples(params);
        } else {
          this.examples = await api.getPublishedSkillExamples({
            skill_key: this.skillKey || undefined,
          });
        }
        if (this.selected) {
          const refreshed = this.examples.find(
            (item) => item.id === this.selected.id,
          );
          this.selected = refreshed || null;
          if (this.selected) this.selectExample(this.selected);
        }
        if (!this.selected && this.examples.length)
          this.selectExample(this.examples[0]);
      } catch (error) {
        this.error = error.response?.data?.detail || "无法读取示例。";
      } finally {
        this.loading = false;
      }
    },
    selectExample(example) {
      this.selected = example;
      this.notice = "";
      this.draft = {
        target_fragment_key: example.target_fragment_key || "",
        scenarioTags: (example.scenario_tags || []).join(", "),
        applicability: JSON.stringify(
          example.applicability_json || {},
          null,
          2,
        ),
        inputContext: JSON.stringify(example.input_context || {}, null, 2),
        expectedOutput: JSON.stringify(example.expected_output || {}, null, 2),
        teachingPoints: (example.teaching_points || []).join("\n"),
        antiPatterns: (example.anti_patterns || []).join("\n"),
        qualityScore: example.quality_score ?? 0.8,
        deidentified: Boolean(example.deidentified),
      };
    },
    parseObject(text, label) {
      let value;
      try {
        value = JSON.parse(text);
      } catch (error) {
        throw new Error(`${label} JSON 格式错误：${error.message}`);
      }
      if (!value || Array.isArray(value) || typeof value !== "object") {
        throw new Error(`${label} 必须是 JSON 对象。`);
      }
      return value;
    },
    async saveCandidate() {
      if (!this.admin || !this.selected) return;
      this.busy = true;
      this.error = "";
      try {
        const updated = await api.updateSkillExample(this.selected.id, {
          target_fragment_key: this.draft.target_fragment_key || null,
          scenario_tags: this.draft.scenarioTags
            .split(/[，,]/)
            .map((item) => item.trim())
            .filter(Boolean),
          applicability_json: this.parseObject(
            this.draft.applicability,
            "适用条件",
          ),
          input_context: this.parseObject(this.draft.inputContext, "输入情境"),
          expected_output: this.parseObject(
            this.draft.expectedOutput,
            "期望输出",
          ),
          teaching_points: lines(this.draft.teachingPoints),
          anti_patterns: lines(this.draft.antiPatterns),
          quality_score: Number(this.draft.qualityScore),
          confirmed_deidentified: this.draft.deidentified,
        });
        this.replaceExample(updated);
        this.notice = "审核内容已保存。";
      } catch (error) {
        this.error =
          error.response?.data?.detail || error.message || "保存失败。";
      } finally {
        this.busy = false;
      }
    },
    async publishSelected() {
      if (!this.selected) return;
      await this.saveCandidate();
      if (this.error) return;
      this.busy = true;
      try {
        const published = await api.publishSkillExample(this.selected.id);
        this.replaceExample(published);
        this.notice = `示例第 ${published.version_no} 版已发布。`;
        await this.loadExamples();
      } catch (error) {
        this.error = error.response?.data?.detail || "发布失败。";
      } finally {
        this.busy = false;
      }
    },
    async retireSelected() {
      if (!this.selected) return;
      this.busy = true;
      try {
        const retired = await api.retireSkillExample(this.selected.id);
        this.replaceExample(retired);
        this.notice = "示例已停用。";
        await this.loadExamples();
      } catch (error) {
        this.error = error.response?.data?.detail || "退役失败。";
      } finally {
        this.busy = false;
      }
    },
    async createRevision() {
      if (!this.selected) return;
      this.busy = true;
      try {
        const candidate = await api.createSkillExampleRevision(
          this.selected.id,
        );
        await this.loadExamples();
        this.filter = "CANDIDATE";
        this.examples = await api.getSkillExamples({
          status: "CANDIDATE",
          skill_key: this.skillKey || undefined,
        });
        this.selectExample(candidate);
        this.notice = `已创建示例第 ${candidate.version_no} 版，等待审核。`;
      } catch (error) {
        this.error = error.response?.data?.detail || "创建新版本失败。";
      } finally {
        this.busy = false;
      }
    },
    replaceExample(example) {
      this.selected = example;
      this.examples = this.examples.map((item) =>
        item.id === example.id ? example : item,
      );
      this.selectExample(example);
    },
    statusLabel(status) {
      return (
        { CANDIDATE: "待审核", PUBLISHED: "已发布", RETIRED: "已停用" }[
          status
        ] || "未知状态"
      );
    },
  },
};
</script>

<style scoped src="./ExamplesPanel.css"></style>
