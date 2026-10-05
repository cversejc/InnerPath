import { reportStage } from "./stages.js";
import { classifyWorkbenchStepView } from "./workbench-inputs.js";

export function nodeViews(stepKey) {
  const common = [
    { id: "overview", label: "节点首页" },
    { id: "upstream", label: "上游输入" },
  ];
  if (["S1", "S2", "S3", "S4"].includes(stepKey))
    return [
      ...common,
      ...(stepKey === "S1" ? [{ id: "calculation", label: "程序计算" }] : []),
      { id: "analysis", label: "AI 分析" },
      { id: "findings", label: "判断审核" },
      { id: "fragments", label: "分析内容" },
    ];
  if (stepKey === "S5")
    return [
      ...common,
      { id: "writing", label: "AI 写作与编排" },
      { id: "fragments", label: "逐段审稿" },
    ];
  if (stepKey === "S6")
    return [
      ...common,
      { id: "quality", label: "AI 检查与问题" },
      { id: "fragments", label: "复核正文" },
    ];
  return common;
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
            ? "正文已生成，请进入逐段审稿。"
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
