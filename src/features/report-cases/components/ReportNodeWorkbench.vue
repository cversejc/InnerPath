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
          <span class="node-state" :title="viewMode === 'UPCOMING' ? '先完成前序节点，再开始处理' : viewMode !== 'CURRENT' ? '历史节点可查看输入、运行记录和审核成果；当前内容只读' : ''">{{ statusLabel(viewStep.status) }}{{ viewMode === 'UPCOMING' ? ' · 预览' : viewMode !== 'CURRENT' ? ' · 只读' : '' }}</span>
        </div>
        <div class="node-header-actions">
          <VanButton
            plain
            native-type="button"
            @click="openDialog($event)"
            >任务说明</VanButton
          >
        </div>
      </header>
      <nav
        ref="viewNavigation"
        class="node-view-actions"
        aria-label="本节点工作界面"
      >
        <template v-for="(view, index) in views" :key="view.id">
          <VanButton
            plain
            native-type="button"
            :aria-pressed="section === view.id"
            :disabled="reviewBusy"
            :class="{ active: section === view.id }"
            @click="$emit('to-section', view.id)"
            >{{ index + 1 }}. {{ view.label }}</VanButton
          >
          <span v-if="index < views.length - 1" class="node-view-arrow" aria-hidden="true">→</span>
        </template>
      </nav>
      </div>
      <div class="node-workspace-body" role="region" :aria-label="`${stage.shortName}工作内容`" tabindex="0">
      <div v-if="section === 'overview'" class="node-home">
        <div v-if="viewStep.status === 'COMPLETED' && currentStep" class="node-continuation" role="status">
          <strong>本节点已完成 · 下一待办：{{ stageFor(currentStep.step_key)?.shortName }}</strong>
          <p>{{ canHandleCurrent ? '已确认成果已传给下一节点。进入下一待办后，点击“开始本节点”继续工作。' : `下一待办由${specialtyLabels[currentStep.required_capability] || '对应咨询师'}负责${currentStep.assignee_id ? '，请由该负责人接续处理。' : '，当前待接单或分配。'}` }}</p>
          <VanButton plain native-type="button" @click="$emit('select-step', currentStep.step_key)">进入当前待办</VanButton>
        </div>
        <div v-else-if="isCurrent && viewStep.status === 'READY'" class="node-continuation" role="status">
          <strong>{{ canAct ? '本节点已就绪，可以开始处理' : `${ownerLabel}待办 · ${viewStep.assignee_id ? '由对应负责人处理' : '尚未接单或分配'}` }}</strong>
          <p>{{ canAct ? '请先点击下方“开始本节点”，再按顺序核对上游输入和本节点任务。' : '前序成果已传入本节点。对应负责人接单或由管理员分配后，才能开始处理。' }}</p>
        </div>
        <div class="node-brief">
          <div>
            <p class="eyebrow">你的任务</p>
            <p>{{ stage.task }}</p>
          </div>
        </div>
        <div class="node-launchers">
          <button
            v-for="(view, index) in views.filter((item) => item.id !== 'overview')"
            :key="view.id"
            type="button"
            @click="$emit('to-section', view.id)"
          >
            <strong>{{ views.findIndex((item) => item.id === view.id) + 1 }}. {{ view.label }}</strong
            ><span>{{ viewHint(view.id) }}</span
            ><span class="launcher-arrow" aria-hidden="true">→</span>
          </button>
        </div>
      </div>
      <NodeInputsPanel
        v-if="section === 'upstream'"
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
      <p v-if="viewStep" class="node-owner" role="status">负责专业：{{ ownerLabel }} · {{ viewStep.assignee_id ? "已接单" : "待接单" }}<span v-if="!canAct && !waitingForUser"> · 本节点供你查看，由对应负责人处理</span></p>
      <footer v-if="section === 'overview' || section === 'signoff'" class="node-actions">
        <VanButton
          v-if="section === 'overview' && canAct && isCurrent && viewStep.status === 'READY'"
          type="primary"
          class="primary-button"
          native-type="button"
          :loading="loading"
          :disabled="loading || reviewBusy"
          @click="$emit('start-step')"
          >开始本节点</VanButton
        ><template
          v-if="
            canAct && isCurrent &&
            viewStep.status === 'IN_REVIEW' &&
            viewStep.step_key !== 'S6' &&
            !aggregatePolicy
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
            loading || reviewBusy || (completionGate && !completionGate.can_complete)
            "
            @click="$emit('complete-step')"
            >确认成果并进入下一节点</VanButton
          ></template
        ><VanButton
          v-if="canAct && isCurrent && viewStep.status === 'IN_REVIEW'"
          plain
          native-type="button"
          :disabled="loading || toolPending || ['IN_PROGRESS', 'CHAPTER_COHERENCE_CHECK', 'COHERENCE_CHECK'].includes(generationStatus)"
          @click="$emit('request-info', viewStep)"
          >向用户补问</VanButton
        ><VanButton
          v-if="viewStep.status === 'COMPLETED' && canReopen && canAct"
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
      <NodeReviewCheckpoint
        v-if="aggregatePolicy && activeCheckpoint && checkpointVisible"
        :key="`${reportCase.id}:${viewStep.step_key}:${activeCheckpoint}`"
        :case-id="reportCase.id"
        :step="viewStep"
        :checkpoint="activeCheckpoint"
        :can-write="canAct && viewStep.status === 'IN_REVIEW'"
        :busy="reviewBusy || loading"
        @changed="$emit('review-changed')"
        @approved="$emit('review-approved')"
        @busy="$emit('review-busy', $event)"
        @request-info="$emit('request-info', $event)"
        @to-section="(section, targetKey) => $emit('to-section', section, targetKey)"
        @advance="$emit('to-section', $event)"
      />
      <footer
        v-if="isCurrent && canAct && viewStep.status === 'IN_REVIEW' && !activeCheckpoint && nextSection"
        class="node-actions node-forward-actions"
      >
        <VanButton
          type="primary"
          class="primary-button"
          native-type="button"
          :disabled="loading || reviewBusy"
          @click="$emit('to-section', nextSection)"
        >
          继续到{{ nextSectionLabel }}
        </VanButton>
      </footer>
      </div>
      <NodeWorkbenchDialog
        :return-focus-element="dialogTrigger"
        :show="Boolean(dialog)"
        title="任务与完成标准"
        @update:show="
          (value) => {
            if (!value) dialog = '';
          }
        "
      >
        <h3>本步目标</h3>
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
          </details>
      </NodeWorkbenchDialog>
    </template>
    <div v-else class="workflow-finished-state">
      <h2>
        {{ reportCase.status === "DELIVERED" ? "报告已交付" : "报告处理总览" }}
      </h2>
      <p>选择上方节点，查看该步骤的上游资料、处理过程和成果。</p>
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
import { canHandleStep, specialtyLabels } from "../professional-ownership.js";
import { Button as VanButton } from "vant";
import { REPORT_STEP_STATUS_LABELS, reportStage } from "../stages.js";
import {
  buildWorkbenchInputGroups,
  classifyWorkbenchStepView,
} from "../workbench-inputs.js";
import { checkpointRendered, nextNodeSection, nodeCheckpoint, nodeViews, nodeAssets } from "../node-workspace.js";
import NodeInputsPanel from "./NodeInputsPanel.vue";
import NodeWorkbenchDialog from "./NodeWorkbenchDialog.vue";
import NodeReviewCheckpoint from "./NodeReviewCheckpoint.vue";
export default {
  components: { VanButton, NodeInputsPanel, NodeWorkbenchDialog, NodeReviewCheckpoint },
  props: {
    reportCase: Object,
    actor: Object,
    content: Object,
    currentStep: Object,
    selectedStepKey: String,
    section: String,
    completionGate: Object,
    narrativePlan: Object,
    quality: Object,
    loading: Boolean,
    toolPending: Boolean,
    generationStatus: String,
    canReopen: Boolean,
    waitingForUser: Boolean,
    reviewBusy: Boolean,
  },
  emits: [
    "select-step",
    "to-section",
    "start-step",
    "complete-step",
    "request-info",
    "toggle-return",
    "reopen",
    "review-changed",
    "review-approved",
    "review-busy",
  ],
  data: () => ({ dialog: "", dialogTrigger: null }),
  computed: {
    aggregatePolicy() { return this.reportCase?.review_policy_version === 'six-node-review-v1' },
    canAct() { return canHandleStep(this.viewStep, this.actor) && !this.waitingForUser },
    canHandleCurrent() { return canHandleStep(this.currentStep, this.actor) },
    specialtyLabels() { return specialtyLabels },
    ownerLabel() { return specialtyLabels[this.viewStep?.required_capability] || "咨询师" },
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
    activeCheckpoint() { return nodeCheckpoint(this.viewStep?.step_key, this.section) },
    checkpointVisible() { return checkpointRendered(this.viewStep?.step_key, this.section, this.isCurrent, this.viewStep?.status) },
    nextSection() { return nextNodeSection(this.viewStep?.step_key, this.section) },
    nextSectionLabel() { return this.views.find((item) => item.id === this.nextSection)?.label || "下一工作页" },
    inputGroups() {
      return buildWorkbenchInputGroups({
        stage: this.stage,
        reportCase: this.reportCase,
        content: this.content,
        narrativePlan: this.narrativePlan,
        quality: this.quality,
      });
    },
    contract() {
      return this.isCurrent ? this.completionGate?.sop_contract : null;
    },
  },
  watch: {
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
    openDialog(event) {
      this.dialogTrigger = event.currentTarget;
      this.dialog = "tasks";
    },
    stageFor: reportStage,
    statusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || "待处理";
    },
    viewHint(id) {
      return {
        upstream: `${this.inputGroups.length} 类输入，集中核对资料与来源`,
        signoff: "检查各阶段确认与问题处理结果，完成节点签核",
        "birth-time": "对照申请资料与程序换算；无异常时一次确认",
        calculation: "查看完整程序计算结果与依据；异常时修订并说明原因",
        analysis: "运行 AI 分析，查看并处理候选结果",
        findings: `${nodeAssets(this.content, this.viewStep, "findings").length} 条本步判断，集中核对并确认`,
        fragments: `${nodeAssets(this.content, this.viewStep, "fragments").length} 项完整内容，整体审阅并确认`,
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
  },
};
</script>
<style scoped src="./ReportNodeWorkbench.css"></style>
