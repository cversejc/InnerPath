<template>
  <section class="report-node-workbench" :class="{ 'node-focused': stage && viewStep }" aria-label="报告节点工作台">
    <ol v-if="!viewStep" class="workflow-progress-rail" aria-label="报告六步处理进度">
      <li
        v-for="(step, index) in steps"
        :key="step.id"
        :class="[
          'workflow-progress-step',
          {
            selected: step.id === viewStep?.id,
            complete: step.status === 'COMPLETED',
          },
        ]"
      >
        <button
          type="button"
          class="workflow-step-select"
          :aria-pressed="step.id === viewStep?.id"
          :aria-current="step.id === currentStep?.id ? 'step' : undefined"
          @click="$emit('select-step', step.step_key)"
        >
          <span class="progress-marker">{{
            String(index + 1).padStart(2, "0")
          }}</span
          ><span class="progress-copy"
            ><strong>{{ stageFor(step.step_key)?.shortName }}</strong
            ><small>{{ statusLabel(step.status) }}</small></span
          >
        </button>
      </li>
    </ol>
    <template v-if="stage && viewStep">
      <div class="node-toolbar">
      <header class="node-heading">
        <div class="node-identity">
          <h2>{{ stage.shortName }}</h2>
          <span class="node-state" :title="viewMode === 'UPCOMING' ? '先完成前序节点，再开始处理' : viewMode !== 'CURRENT' ? '历史节点，可查看输入、技能记录和审核成果，当前内容只读' : ''">{{ statusLabel(viewStep.status) }}{{ viewMode === 'UPCOMING' ? ' · 预览' : viewMode !== 'CURRENT' ? ' · 只读' : '' }}</span>
        </div>
        <select class="node-step-switch" aria-label="切换分析节点" :value="viewStep.step_key" @change="$emit('select-step', $event.target.value)">
          <option v-for="step in steps" :key="step.id" :value="step.step_key">{{ step.sequence_no }}/{{ steps.length }} · {{ stageFor(step.step_key)?.shortName }} · {{ statusLabel(step.status) }}</option>
        </select>
        <div class="node-header-actions">
          <VanButton
            plain
            native-type="button"
            @click="openDialog('tools', $event)"
            >技能工具</VanButton
          ><VanButton
            plain
            native-type="button"
            @click="openDialog('tasks', $event)"
            >任务说明</VanButton
          >
        </div>
      </header>
      <nav
        ref="viewNavigation"
        class="node-view-actions"
        aria-label="本节点工作界面"
      >
        <VanButton
          v-for="view in views"
          :key="view.id"
          plain
          native-type="button"
          :aria-pressed="section === view.id"
          :class="{ active: section === view.id }"
          @click="$emit('to-section', view.id)"
          >{{ view.label }}</VanButton
        >
      </nav>
      </div>
      <div class="node-workspace-body" role="region" :aria-label="`${stage.shortName}工作内容`" tabindex="0">
      <div v-if="section === 'overview'" class="node-home">
        <div class="node-brief">
          <div>
            <p class="eyebrow">你的任务</p>
            <p>{{ stage.task }}</p>
          </div>
        </div>
        <div class="node-launchers">
          <button
            v-for="view in views.filter((item) => item.id !== 'overview')"
            :key="view.id"
            type="button"
            @click="$emit('to-section', view.id)"
          >
            <strong>{{ view.label }}</strong
            ><span>{{ viewHint(view.id) }}</span
            ><span class="launcher-arrow" aria-hidden="true">→</span>
          </button>
        </div>
      </div>
      <NodeInputsPanel
        v-if="section === 'inputs'"
        :key="viewStep.step_key"
        :groups="inputGroups"
        :guidance="stage.inputGuidance"
      />
      <div
        v-if="isCurrent && completionGate && section === 'overview'"
        class="node-completion-gate"
        role="status"
      >
        <strong>{{
          completionGate.can_complete ? "审核条件已满足" : "完成前还需处理"
        }}</strong>
        <ul v-if="!completionGate.can_complete">
          <li v-for="blocker in completionGate.blockers" :key="blocker">
            {{ blockerLabel(blocker) }}
          </li>
        </ul>
      </div>
      <footer v-if="section === 'overview'" class="node-actions">
        <VanButton
          v-if="isCurrent && viewStep.status === 'READY'"
          type="primary"
          class="primary-button"
          native-type="button"
          :loading="loading"
          @click="$emit('start-step')"
          >开始本节点</VanButton
        ><template
          v-if="
            isCurrent &&
            viewStep.status === 'IN_REVIEW' &&
            viewStep.step_key !== 'S6'
          "
          ><VanButton
            plain
            native-type="button"
            :disabled="loading"
            @click="$emit('toggle-return')"
            >退回上游</VanButton
          ><VanButton
            type="primary"
            class="primary-button"
            native-type="button"
            :loading="loading"
            :disabled="
              loading || (completionGate && !completionGate.can_complete)
            "
            @click="$emit('complete-step')"
            >确认成果并完成本节点</VanButton
          ></template
        ><VanButton
          v-if="viewStep.status === 'COMPLETED' && canReopen"
          plain
          native-type="button"
          :disabled="loading"
          @click="$emit('reopen', viewStep)"
          >重开本节点</VanButton
        ><VanButton
          v-if="viewMode !== 'CURRENT' && currentStep"
          plain
          native-type="button"
          @click="$emit('select-step', currentStep.step_key)"
          >回到当前待办</VanButton
        >
      </footer>
      <slot />
      </div>
      <NodeWorkbenchDialog
        :return-focus-element="dialogTrigger"
        :show="Boolean(dialog)"
        :title="dialogKind === 'tools' ? '本节点技能工具' : '任务与完成标准'"
        @update:show="
          (value) => {
            if (!value) dialog = '';
          }
        "
      >
        <template v-if="dialogKind === 'tools'"
          ><p>
            技能使用本节点资料生成候选结果。运行后进入对应工作界面，由你审核确认。
          </p>
          <article
            v-for="tool in tools"
            :key="tool.action"
            class="node-skill-tool"
          >
            <h3>{{ tool.name }}</h3>
            <p>输入：{{ tool.input }}</p>
            <p>产出：{{ tool.output }}</p>
            <p v-if="tool.disabledReason" class="tool-reason">
              {{ tool.disabledReason }}
            </p>
            <VanButton
              type="primary"
              class="primary-button"
              native-type="button"
              :disabled="tool.disabled"
              @click="runTool(tool)"
              >运行技能</VanButton
            ><VanButton
              plain
              native-type="button"
              @click="openView(tool.destination)"
              >查看结果</VanButton
            >
          </article>
          <router-link class="node-studio-link" :to="studioLocation"
            >前往技能与示例工作台</router-link
          >
          <details v-if="stageRuns.length">
            <summary>本节点运行记录 · {{ stageRuns.length }} 次</summary>
            <ul>
              <li v-for="run in stageRuns" :key="run.id">
                {{ runStatus(run.status) }} · 技能版本
                {{ run.skill_version_id }} · 使用
                {{ run.selected_examples?.length || 0 }} 个样例
              </li>
            </ul>
          </details></template
        >
        <template v-else
          ><h3>本步目标</h3>
          <p>{{ stage.purpose }}</p>
          <p>{{ stage.deliverable }}</p>
          <h3>本步要完成什么</h3>
          <p>{{ stage.task }}</p>
          <ol>
            <li v-for="action in stage.actions" :key="action">{{ action }}</li>
          </ol>
          <h3>职责分工</h3>
          <dl class="node-responsibilities">
            <dt>程序</dt>
            <dd>
              {{
                contract?.responsibilities.program ||
                (stage.stepKey === "S1"
                  ? "按出生资料计算四柱、大运和紫微结构，保留测算依据。"
                  : "整理已确认输入、记录版本及校验来源和交付条件。")
              }}
            </dd>
            <dt>AI</dt>
            <dd>
              {{
                contract?.responsibilities.ai ||
                "运行本节点技能，提供候选分析、写作或检查结果。"
              }}
            </dd>
            <dt>咨询师</dt>
            <dd>
              {{
                contract?.responsibilities.human ||
                "核对输入和现实情境，修改或拒绝候选，确认本步成果后再向下游传递。"
              }}
            </dd>
          </dl>
          <h3>完成标准</h3>
          <ul>
            <li v-for="item in stage.checklist" :key="item">{{ item }}</li>
          </ul>
          <details v-if="contract?.topics">
            <summary>详细分析范围 · {{ contract.topics.length }} 项</summary>
            <article v-for="topic in contract.topics" :key="topic.fragment_key">
              <h4>{{ topic.title }}</h4>
              <p>{{ topic.task }}</p>
            </article>
          </details></template
        >
      </NodeWorkbenchDialog>
    </template>
    <div v-else class="workflow-finished-state">
      <h2>
        {{ reportCase.status === "DELIVERED" ? "报告已交付" : "报告处理总览" }}
      </h2>
      <p>选择上方节点，查看该步骤的输入、技能和成果。</p>
      <dl class="report-overview-stats">
        <div>
          <dt>已确认判断</dt>
          <dd>
            {{
              content.findings.filter((item) => item.status === "CONFIRMED")
                .length
            }}
            条
          </dd>
        </div>
        <div>
          <dt>已确认分析</dt>
          <dd>
            {{
              content.fragments.filter(
                (item) =>
                  item.fragment_type === "ANALYSIS" &&
                  item.status === "CONFIRMED",
              ).length
            }}
            项
          </dd>
        </div>
        <div>
          <dt>已确认正文</dt>
          <dd>
            {{
              content.fragments.filter(
                (item) =>
                  item.fragment_type === "REPORT" &&
                  item.status === "CONFIRMED",
              ).length
            }}
            段
          </dd>
        </div>
      </dl>
    </div>
  </section>
</template>
<script>
import { Button as VanButton } from "vant";
import { REPORT_STEP_STATUS_LABELS, reportStage } from "../stages.js";
import {
  buildWorkbenchInputGroups,
  classifyWorkbenchStepView,
} from "../workbench-inputs.js";
import { nodeViews, nodeTools, nodeAssets } from "../node-workspace.js";
import NodeInputsPanel from "./NodeInputsPanel.vue";
import NodeWorkbenchDialog from "./NodeWorkbenchDialog.vue";
export default {
  components: { VanButton, NodeInputsPanel, NodeWorkbenchDialog },
  props: {
    reportCase: Object,
    content: Object,
    currentStep: Object,
    selectedStepKey: String,
    section: String,
    completionGate: Object,
    narrativePlan: Object,
    quality: Object,
    analysisRuns: { type: Array, default: () => [] },
    loading: Boolean,
    toolPending: Boolean,
    generationStatus: String,
    canReopen: Boolean,
    studioLocation: Object,
  },
  emits: [
    "select-step",
    "to-section",
    "start-step",
    "complete-step",
    "toggle-return",
    "reopen",
    "run-tool",
  ],
  data: () => ({ dialog: "", dialogKind: "tools", dialogTrigger: null }),
  computed: {
    steps() {
      return this.reportCase.workflow_instance?.steps || [];
    },
    viewStep() {
      return (
        this.steps.find((step) => step.step_key === this.selectedStepKey) ||
        null
      );
    },
    stage() {
      return reportStage(this.viewStep?.step_key);
    },
    viewMode() {
      return classifyWorkbenchStepView(this.viewStep, this.currentStep);
    },
    isCurrent() {
      return this.viewMode === "CURRENT";
    },
    views() {
      return nodeViews(this.viewStep?.step_key);
    },
    inputGroups() {
      return buildWorkbenchInputGroups({
        stage: this.stage,
        reportCase: this.reportCase,
        content: this.content,
        narrativePlan: this.narrativePlan,
        quality: this.quality,
      });
    },
    tools() {
      return nodeTools(this.viewStep, this.currentStep, {
        pending: this.toolPending,
        generationStatus: this.generationStatus,
        planReady:
          this.narrativePlan?.status === "CONFIRMED" &&
          this.narrativePlan?.plan_json?.content_plan?.status === "READY",
      });
    },
    contract() {
      return this.isCurrent ? this.completionGate?.sop_contract : null;
    },
    stageRuns() {
      return this.analysisRuns.filter(
        (run) => run.step_task_id === this.viewStep?.id,
      );
    },
  },
  watch: {
    dialog(value) {
      if (value) this.dialogKind = value;
    },
    selectedStepKey() {
      this.dialog = "";
      this.revealSelectedView();
    },
    section() {
      this.revealSelectedView();
    },
  },
  mounted() {
    this.revealSelectedView();
  },
  methods: {
    revealSelectedView() {
      this.$nextTick(() => {
        this.$refs.viewNavigation?.querySelector('[aria-pressed="true"]')?.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
    },
    openDialog(kind, event) {
      this.dialogTrigger = event.currentTarget;
      this.dialog = kind;
    },
    stageFor: reportStage,
    statusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || "待处理";
    },
    runStatus(status) {
      return (
        {
          PENDING: "待运行",
          RUNNING: "运行中",
          COMPLETED: "已完成",
          FAILED: "失败",
        }[status] || "待处理"
      );
    },
    viewHint(id) {
      return {
        inputs: `${this.inputGroups.length} 类输入，逐项查看来源`,
        suggestions: "查看技能候选，选择加入审核",
        findings: `${nodeAssets(this.content, this.viewStep, "findings").length} 条本步判断，逐条确认`,
        fragments: `${nodeAssets(this.content, this.viewStep, "fragments").length} 项内容，逐项审阅与编辑`,
        writing: "选择报告主线，确认编排",
        quality: "复核七维评分并处理每项问题",
      }[id];
    },
    blockerLabel(code) {
      return (
        {
          report_analysis_findings_unreviewed: "尚有判断待审核",
          report_analysis_fragments_unreviewed: "尚有分析内容待审核",
          report_analysis_fragments_stale: "前序依据已更新，请重新审核分析",
          report_analysis_output_required: "先确认判断和分析成果",
          report_analysis_sop_coverage_required:
            "按分析范围逐项确认，缺资料须说明暂缓原因",
          confirmed_finding_required: "至少确认一条有依据的专业判断",
          confirmed_analysis_fragment_required: "至少确认一项分析",
          confirmed_analysis_topic_coverage_required:
            "按分析清单逐项确认，缺资料须记录暂缓原因",
          confirmed_growth_experiments_required: "确认3–5项可执行成长实验",
        }[code] || "请检查未完成的审核项"
      );
    },
    openView(section) {
      this.dialog = "";
      this.$emit("to-section", section);
    },
    runTool(tool) {
      if (tool.disabled) return;
      this.dialog = "";
      this.$emit("run-tool", tool);
    },
  },
};
</script>
<style scoped src="./ReportNodeWorkbench.css"></style>
