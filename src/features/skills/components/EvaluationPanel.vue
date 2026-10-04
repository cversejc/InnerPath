<template>
  <section class="evaluation-panel">
    <div class="evaluation-heading">
      <div>
        <h2>技能质量评估</h2>
        <p v-if="version">
          {{ skillInfo(version.skill_key, version.name).name }} · 第
          {{ version.version }} 版 · {{ versionStatusLabel }}
        </p>
      </div>
      <VanButton
        class="secondary-button compact-button"
        type="default"
        plain
        :disabled="loading || !version"
        @click="loadData"
        >刷新</VanButton
      >
    </div>

    <p v-if="error" class="evaluation-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="evaluation-notice" role="status">{{ notice }}</p>

    <div class="evaluation-create">
      <div class="evaluation-create-heading">
        <div>
          <h3>验证样本</h3>
          <p>用固定案例检查输出是否符合要求。</p>
        </div>
        <VanButton
          class="secondary-button compact-button"
          type="default"
          plain
          :disabled="!cases.length"
          @click="toggleAll"
          >{{ allSelected ? "取消全选" : "全选" }}</VanButton
        >
      </div>
      <fieldset class="evaluation-case-list">
        <legend class="visually-hidden">选择回归样本</legend>
        <label
          v-for="item in cases"
          :key="item.case_key"
          class="evaluation-case"
        >
          <input
            v-model="selectedCaseKeys"
            type="checkbox"
            :value="item.case_key"
          />
          <span
            ><strong>{{ displayText(item.title) }}</strong
            ><small>{{ displayText(item.description) }}</small></span
          >
        </label>
        <p v-if="!loading && !cases.length" class="evaluation-empty">
          该技能暂无已配置验证样本。
        </p>
      </fieldset>
      <div class="evaluation-run-action">
        <span>{{ selectedCaseKeys.length }} / {{ cases.length }} 个样本</span>
        <VanButton
          class="primary-button compact-button"
          type="primary"
          :disabled="!version || !selectedCaseKeys.length || busy"
          :loading="busy"
          @click="runEvaluation"
          >开始评估</VanButton
        >
      </div>
    </div>

    <section v-if="activeBatch" class="evaluation-results" aria-live="polite">
      <div class="evaluation-results-heading">
        <div><h3>最近一次结果</h3></div>
        <span
          class="evaluation-rate"
          :class="{
            pass: activeBatch.pass_rate === 1,
            fail: activeBatch.pass_rate !== null && activeBatch.pass_rate < 1,
          }"
        >
          {{
            activeBatch.pass_rate === null
              ? "运行中"
              : `${Math.round(activeBatch.pass_rate * 100)}% 通过`
          }}
        </span>
      </div>
      <div class="evaluation-summary">
        <span>{{ activeBatch.passed }} / {{ activeBatch.total }} 通过</span>
        <span>{{ activeBatch.completed }} 完成</span>
        <span>{{ activeBatch.failed }} 运行失败</span>
        <details>
          <summary>样本集与批次标识</summary>
          <code
            >{{ activeBatch.dataset_version }} ·
            {{ activeBatch.batch_id }}</code
          >
        </details>
      </div>
      <div class="evaluation-run-list">
        <details
          v-for="run in activeBatch.runs"
          :key="run.run_id"
          class="evaluation-run"
        >
          <summary>
            <span
              ><strong>{{ displayText(run.title) }}</strong
              ><small>运行记录 {{ run.run_id }}</small></span
            >
            <span
              class="evaluation-run-state"
              :class="evaluationStateClass(run)"
              >{{ evaluationStateLabel(run) }}</span
            >
            <span class="evaluation-score">{{
              run.score === null ? "—" : `${Math.round(run.score * 100)}%`
            }}</span>
          </summary>
          <p v-if="run.error" class="evaluation-error">{{ run.error }}</p>
          <ul class="evaluation-checks">
            <li
              v-for="check in run.checks"
              :key="check.name"
              :class="{ failed: !check.passed }"
            >
              <strong>{{ check.passed ? "通过" : "未通过" }}</strong>
              <span>{{ evaluationCheckLabel(check.name) }}</span>
              <code v-if="check.actual !== undefined">{{
                JSON.stringify(check.actual)
              }}</code>
            </li>
          </ul>
          <p class="evaluation-example-note">
            参考示例：{{ run.selected_examples?.length || 0 }} 条
          </p>
        </details>
      </div>
    </section>

    <section v-if="batches.length" class="evaluation-history">
      <div class="panel-heading">
        <div><h3>历史评估</h3></div>
        <span>{{ batches.length }} 条</span>
      </div>
      <button
        v-for="batch in batches"
        :key="batch.batch_id"
        type="button"
        class="evaluation-history-row"
        :class="{ selected: activeBatch?.batch_id === batch.batch_id }"
        @click="openBatch(batch.batch_id)"
      >
        <span
          ><strong>{{ batch.passed }} / {{ batch.total }} 通过</strong
          ><small>验证样本 {{ batch.total }} 个</small></span
        >
        <span>{{
          batch.pass_rate === null
            ? "运行中"
            : `${Math.round(batch.pass_rate * 100)}%`
        }}</span>
      </button>
    </section>
  </section>
</template>

<script>
import { Button as VanButton } from "vant";
import api from "../api.js";
import {
  skillInfo,
  displayText,
  evaluationCheckLabel,
} from "../presentation.js";
import { VERSION_STATUS_LABELS } from "../studio.js";

const POLL_INTERVAL = 2500;

export default {
  name: "EvaluationPanel",
  components: { VanButton },
  props: {
    version: { type: Object, default: null },
    startEvaluation: { type: Function, required: true },
  },
  data() {
    return {
      cases: [],
      selectedCaseKeys: [],
      batches: [],
      activeBatch: null,
      loading: false,
      busy: false,
      error: "",
      notice: "",
      pollTimer: null,
    };
  },
  computed: {
    versionStatusLabel() {
      return VERSION_STATUS_LABELS[this.version?.status] || "未知状态";
    },
    allSelected() {
      return (
        this.cases.length > 0 &&
        this.selectedCaseKeys.length === this.cases.length
      );
    },
    datasetVersion() {
      return (
        this.batches[0]?.dataset_version ||
        this.activeBatch?.dataset_version ||
        ""
      );
    },
  },
  mounted() {
    this.loadData();
  },
  beforeUnmount() {
    this.clearPoll();
  },
  watch: {
    "version.id"() {
      this.activeBatch = null;
      this.loadData();
    },
  },
  methods: {
    skillInfo,
    displayText,
    evaluationCheckLabel,
    async loadData() {
      if (!this.version) return;
      this.loading = true;
      this.error = "";
      try {
        const [cases, batches] = await Promise.all([
          api.getSkillEvaluationCases(this.version.skill_key),
          api.getSkillEvaluationBatches(this.version.id),
        ]);
        this.cases = cases;
        this.batches = batches;
        const validKeys = new Set(cases.map((item) => item.case_key));
        this.selectedCaseKeys = this.selectedCaseKeys.filter((key) =>
          validKeys.has(key),
        );
        if (!this.selectedCaseKeys.length)
          this.selectedCaseKeys = cases.map((item) => item.case_key);
        if (!this.activeBatch && batches.length) this.activeBatch = batches[0];
        if (this.activeBatch?.pass_rate === null) this.startPoll();
      } catch (error) {
        this.error =
          error.response?.data?.detail || "无法读取回归样本或评估记录。";
      } finally {
        this.loading = false;
      }
    },
    toggleAll() {
      this.selectedCaseKeys = this.allSelected
        ? []
        : this.cases.map((item) => item.case_key);
    },
    async runEvaluation() {
      if (!this.version || !this.selectedCaseKeys.length || this.busy) return;
      this.busy = true;
      this.error = "";
      this.notice = "";
      try {
        this.activeBatch = await this.startEvaluation([
          ...this.selectedCaseKeys,
        ]);
        this.notice = "评估已开始，结果会自动更新。";
        await this.loadBatches();
        if (this.activeBatch.pass_rate === null) this.startPoll();
      } catch (error) {
        this.error =
          error.response?.data?.detail || error.message || "评估批次创建失败。";
      } finally {
        this.busy = false;
      }
    },
    async loadBatches() {
      if (!this.version) return;
      this.batches = await api.getSkillEvaluationBatches(this.version.id);
    },
    async openBatch(batchId) {
      this.error = "";
      try {
        this.activeBatch = await api.getSkillEvaluation(batchId);
        if (this.activeBatch.pass_rate === null) this.startPoll();
        else this.clearPoll();
      } catch (error) {
        this.error = error.response?.data?.detail || "无法读取评估批次。";
      }
    },
    startPoll() {
      if (this.pollTimer) return;
      this.pollTimer = window.setInterval(async () => {
        if (!this.activeBatch?.batch_id) return;
        try {
          this.activeBatch = await api.getSkillEvaluation(
            this.activeBatch.batch_id,
          );
          await this.loadBatches();
          if (this.activeBatch.pass_rate !== null) this.clearPoll();
        } catch (error) {
          this.error = error.response?.data?.detail || "读取评估进度失败。";
          this.clearPoll();
        }
      }, POLL_INTERVAL);
    },
    clearPoll() {
      if (this.pollTimer) window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    },
    evaluationStateLabel(run) {
      if (run.status === "PENDING" || run.status === "RUNNING") return "运行中";
      if (run.status === "FAILED") return "运行失败";
      return run.passed ? "通过" : "未通过";
    },
    evaluationStateClass(run) {
      if (run.status === "PENDING" || run.status === "RUNNING")
        return "pending";
      return run.passed ? "passed" : "failed";
    },
  },
};
</script>

<style scoped src="./EvaluationPanel.css"></style>
