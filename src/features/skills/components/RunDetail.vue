<template>
  <section class="run-detail" aria-live="polite">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">运行记录 {{ run.id }} · {{ runStatusLabel }}</p>
        <h3>
          {{
            run.status === "FAILED"
              ? "执行失败"
              : run.status === "COMPLETED"
                ? "执行结果"
                : "执行状态"
          }}
        </h3>
      </div>
    </div>
    <div v-if="run.runtime_instruction" class="run-consultant-feedback">
      <strong>本次咨询师反馈</strong>
      <p>{{ run.runtime_instruction }}</p>
    </div>
    <p v-if="run.context_snapshot?.analysis_feedback_source_run_id" class="run-feedback-source">
      本次重跑针对运行记录 {{ run.context_snapshot.analysis_feedback_source_run_id }} 的 AI 结果。
    </p>
    <p v-if="run.error" class="run-error" role="alert">{{ run.error }}</p>
    <SkillResultReader v-if="run.output_parsed" :value="run.output_parsed" />
    <p v-else>暂无结果，等待执行完成。</p>
    <details
      v-if="run.context_snapshot && Object.keys(run.context_snapshot).length"
      class="context-reference"
    >
      <summary>技能使用的资料（技术结构）</summary>
      <pre class="output-block">{{
        JSON.stringify(run.context_snapshot, null, 2)
      }}</pre>
    </details>
    <details class="context-reference">
      <summary>知识引用（{{ run.selected_knowledge?.length || 0 }}）</summary>
      <pre v-if="run.selected_knowledge?.length" class="output-block">{{
        JSON.stringify(run.selected_knowledge, null, 2)
      }}</pre>
      <p v-else class="empty-reference">本次运行没有知识引用。</p>
    </details>
    <details class="context-reference">
      <summary>
        本次参考的示例（{{ run.selected_examples?.length || 0 }}）
      </summary>
      <div v-if="run.selected_examples?.length" class="selected-examples">
        <article
          v-for="example in run.selected_examples"
          :key="`${example.example_key}:${example.version_no}`"
          class="selected-example"
        >
          <strong
            >示例 {{ example.example_id }} · 第
            {{ example.version_no }} 版</strong
          >
          <span>匹配分 {{ example.retrieval_score }}</span>
          <ReadableData :value="example.example_snapshot" />
          <details>
            <summary>匹配依据与原始结构</summary>
            <pre class="output-block">{{
              JSON.stringify(example, null, 2)
            }}</pre>
          </details>
        </article>
      </div>
      <p v-else class="empty-reference">本次运行没有参考已发布示例。</p>
    </details>
    <details v-if="canRecommend" class="recommend-experience">
      <summary>将本次运行的经验推荐为示例</summary>
      <form class="example-recommend-form" @submit.prevent="recommendExample">
        <p>说明哪些方法值得复用，提交后由管理员脱敏并审核发布。</p>
        <label for="recommend-example-type">示例类型</label>
        <select id="recommend-example-type" v-model="exampleType">
          <option value="POSITIVE">正向示例</option>
          <option value="CONTRASTIVE">对照示例</option>
          <option value="MISSED_INSIGHT">补充洞察</option>
        </select>
        <label for="recommend-example-tags">情境标签</label>
        <input
          id="recommend-example-tags"
          v-model="scenarioTags"
          placeholder="例如：职业、决策（逗号分隔）"
        />
        <label for="recommend-example-points">教学要点（每行一项）</label>
        <textarea
          id="recommend-example-points"
          v-model="teachingPoints"
          rows="3"
        ></textarea>
        <VanButton
          class="secondary-button compact-button"
          type="default"
          plain
          native-type="submit"
          :disabled="recommending"
          :loading="recommending"
          >提交给管理员审核</VanButton
        >
        <p
          v-if="recommendationNotice"
          class="recommendation-notice"
          role="status"
        >
          {{ recommendationNotice }}
        </p>
        <p v-if="recommendationError" class="run-error" role="alert">
          {{ recommendationError }}
        </p>
      </form>
    </details>
    <details v-if="admin && run.output_raw" class="raw-output">
      <summary>模型原始输出</summary>
      <pre class="output-block">{{ run.output_raw }}</pre>
    </details>
    <details v-if="traceRows.length">
      <summary>模型与用量记录</summary>
      <dl class="trace-list">
        <div v-for="[label, value] in traceRows" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value }}</dd>
        </div>
      </dl>
    </details>
  </section>
</template>

<script>
import { formatTrace, RUN_STATUS_LABELS } from "../studio.js";
import { Button as VanButton } from "vant";
import api from "../api.js";
import SkillResultReader from "./SkillResultReader.vue";
import ReadableData from "./ReadableData.vue";

export default {
  name: "RunDetail",
  components: { VanButton, SkillResultReader, ReadableData },
  props: {
    run: { type: Object, required: true },
    admin: { type: Boolean, default: false },
    caseId: { type: [String, Number], default: null },
  },
  data() {
    return {
      exampleType: "POSITIVE",
      scenarioTags: "",
      teachingPoints: "",
      recommending: false,
      recommendationNotice: "",
      recommendationError: "",
    };
  },
  computed: {
    runStatusLabel() {
      return RUN_STATUS_LABELS[this.run.status] || "未知状态";
    },
    traceRows() {
      return formatTrace(this.run.model_trace);
    },
    canRecommend() {
      if (this.admin && this.run.target_type === 'CALENDAR_PRODUCTION') return this.run.status === 'COMPLETED'
      return (
        !this.admin &&
        this.caseId &&
        Number(this.run.report_case_id) === Number(this.caseId) &&
        this.run.status === "COMPLETED"
      );
    },
  },
  methods: {
    async recommendExample() {
      if (!this.canRecommend || this.recommending) return;
      this.recommending = true;
      this.recommendationError = "";
      this.recommendationNotice = "";
      try {
        const tags = this.scenarioTags
          .split(/[，,]/)
          .map((item) => item.trim())
          .filter(Boolean);
        const points = this.teachingPoints
          .split(/\r?\n/)
          .map((item) => item.trim())
          .filter(Boolean);
        const recommend = this.admin && this.run.target_type === 'CALENDAR_PRODUCTION'
          ? api.recommendCalendarSkillExample : api.recommendSkillExample
        const candidate = await recommend(this.admin ? this.run.id : Number(this.caseId), {
          skill_run_id: this.run.id,
          example_type: this.exampleType,
          scenario_tags: tags,
          teaching_points: points,
        });
        this.recommendationNotice = `已提交候选示例 ${candidate.id}，等待管理员审核。`;
      } catch (error) {
        this.recommendationError =
          error.response?.data?.detail || "推荐提交失败。";
      } finally {
        this.recommending = false;
      }
    },
  },
};
</script>

<style scoped src="./RunDetail.css"></style>
