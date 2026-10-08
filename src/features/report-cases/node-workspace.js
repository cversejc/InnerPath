import { reportStage } from "./stages.js";
import { classifyWorkbenchStepView } from "./workbench-inputs.js";

export function nodeViews(stepKey) {
  const nodeHome = { id: "overview", label: "节点首页" };
  const nodeReview = { id: "signoff", label: "节点复核" };
  const upstream = { id: "upstream", label: "上游输入" };
  if (["S1", "S2", "S3", "S4"].includes(stepKey))
    return [
      nodeHome,
      upstream,
      ...(stepKey === "S1"
        ? [
            { id: "birth-time", label: "出生资料与时间核对" },
            { id: "calculation", label: "程序计算" },
          ]
        : []),
      { id: "analysis", label: "AI 分析" },
      { id: "findings", label: "判断审核" },
      { id: "fragments", label: "分析内容" },
      nodeReview,
    ];
  if (stepKey === "S5")
    return [
      nodeHome,
      upstream,
      { id: "writing", label: "AI 写作与编排" },
      { id: "fragments", label: "完整报告审阅" },
      nodeReview,
    ];
  if (stepKey === "S6")
    return [
      nodeHome,
      upstream,
      { id: "quality", label: "AI 检查与问题" },
      { id: "fragments", label: "复核正文" },
      nodeReview,
    ];
  return [nodeHome, upstream, nodeReview];
}

export function nodeCheckpoint(stepKey, section) {
  if (section === "signoff") return "node";
  if (stepKey === "S1" && section === "birth-time") return "birth_data";
  if (["S1", "S2", "S3", "S4"].includes(stepKey)) {
    if (section === "findings") return "findings";
    if (section === "fragments") return "analysis";
  }
  if (stepKey === "S5") {
    if (section === "writing") return "narrative";
    if (section === "fragments") return "report";
  }
  if (stepKey === "S6" && section === "fragments") return "report";
  return "";
}

export function checkpointRendered(stepKey, section, isCurrent, stepStatus = "") {
  const checkpoint = nodeCheckpoint(stepKey, section);
  if (!checkpoint) return false;
  if (isCurrent) return true;
  // 已完成的 S1 仍要能只读查看出生资料与程序换算；其他阶段确认只在当前节点内展示。
  if (checkpoint === "birth_data") return true;
  // 已完成节点回看：节点复核页只读展示本节点完成时的检查结果与处理记录。
  return stepStatus === "COMPLETED" && checkpoint === "node";
}

export function nextNodeSection(stepKey, section) {
  const views = nodeViews(stepKey);
  const index = views.findIndex((item) => item.id === section);
  return index >= 0 ? views[index + 1]?.id || "" : "";
}

export function nextCheckpointSection(stepKey, checkpoint) {
  const checkpointSections = {
    birth_data: "birth-time",
    findings: "findings",
    analysis: "fragments",
    narrative: "writing",
    report: "fragments",
  };
  const section = checkpointSections[checkpoint];
  return section ? nextNodeSection(stepKey, section) : "";
}

export function resolveNodeLocation(steps, currentStep, query = {}) {
  const step =
    query.step === "all"
      ? null
      : steps.find((item) => item.step_key === query.step) ||
        currentStep ||
        null;
  // Preserve old links by assigning their functional page to its owning step.
  const legacyOwner = { quality: "S6", writing: "S5" };
  const selected =
    !query.step && legacyOwner[query.section]
      ? steps.find((item) => item.step_key === legacyOwner[query.section]) ||
        step
      : step;
  const sectionAliases = {
    context: "upstream",
    inputs: "upstream",
    evidence: selected?.step_key === "S1" ? "calculation" : "upstream",
    suggestions: "analysis",
  };
  const section = sectionAliases[query.section] || query.section;
  return {
    stepKey: selected?.step_key || "",
    section: nodeViews(selected?.step_key).some((item) => item.id === section)
      ? section
      : "overview",
  };
}

export function nodeAssets(content, step, type) {
  if (!step) return [];
  if (type === "findings")
    return (content.findings || []).filter(
      (item) => item.owner_step_task_id === step.id,
    );
  return (content.fragments || []).filter((item) =>
    ["S5", "S6"].includes(step.step_key)
      ? item.fragment_type === "REPORT"
      : item.fragment_type === "ANALYSIS" &&
        item.owner_step_task_id === step.id,
  );
}

export function nodeTools(
  step,
  currentStep,
  { pending = false, planReady = false, generationStatus = "" } = {},
) {
  if (!step) return [];
  const state = classifyWorkbenchStepView(step, currentStep);
  const disabledReason =
    state === "HISTORY"
      ? "历史节点只读，不能再次运行。"
      : state === "UPCOMING"
        ? "请先完成前序节点。"
        : step.status !== "IN_REVIEW"
          ? "开始本节点后才能运行技能。"
          : pending
            ? "技能正在运行，请等待结果。"
            : "";
  let tools;
  if (["S1", "S2", "S3", "S4"].includes(step.step_key))
    tools = [
      {
        action: "analysis",
        name: `${reportStage(step.step_key).shortName}分析技能`,
        input: "本节点输入和前序已确认内容",
        output: "候选判断、分析片段和风险提示",
        destination: "analysis",
      },
    ];
  else if (step.step_key === "S5")
    tools = [
      {
        action: "narrative",
        name: "报告叙事方案技能",
        input: "已确认判断、分析和用户情境",
        output: "主线候选与内容编排",
        destination: "writing",
      },
      {
        action: "authoring",
        name: "报告片段写作技能",
        input: "咨询师确认的主线及逐段来源",
        output: "逐段正文，包含章节和全文连贯检查",
        destination: "fragments",
        prerequisite: !planReady
          ? "请先确认可生成的主线和内容编排。"
          : generationStatus === "READY_FOR_REVIEW"
              ? "正文已生成，请通读全文并整体审阅。"
            : [
                  "IN_PROGRESS",
                  "CHAPTER_COHERENCE_CHECK",
                  "COHERENCE_CHECK",
                ].includes(generationStatus)
              ? "报告正在生成，请查看生成进度。"
              : [
                    "CHAPTER_COHERENCE_BLOCKED",
                    "CHAPTER_COHERENCE_FAILED",
                    "CHAPTER_COHERENCE_STALE",
                    "COHERENCE_BLOCKED",
                    "COHERENCE_FAILED",
                    "COHERENCE_STALE",
                    "NEEDS_INPUT",
                    "BLOCKED",
                  ].includes(generationStatus)
                ? "请进入主线与编排，处理生成问题后继续。"
                : "",
      },
    ];
  else
    tools = [
      {
        action: "quality",
        name: "报告语义质量审核技能",
        input: "当前正文、确认依据和编排计划",
        output: "七维评分及逐项问题",
        destination: "quality",
      },
    ];
  return tools.map((tool) => ({
    ...tool,
    disabledReason: disabledReason || tool.prerequisite || "",
    disabled: Boolean(disabledReason || tool.prerequisite),
  }));
}

export function workspaceFocusTargetId(section, targetKey) {
  // ???? id ??? CSS ????fragment_key ????????????? id+class?
  const key = String(targetKey ?? "").trim();
  if (!key) return "";
  if (section === "fragments") return `report-fragment-${key}`;
  if (section === "findings") return `report-finding-${key}`;
  return "";
}