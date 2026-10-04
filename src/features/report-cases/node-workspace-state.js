import {
  nodeAssets,
  nodeViews,
  nodeTools,
  resolveNodeLocation,
} from "./node-workspace.js";

import { canHandleStep } from "./professional-ownership.js";

function selected(items, key, field) {
  const item = items.find((row) => String(row[field]) === key) || items[0];
  return item ? [item] : [];
}

export const nodeWorkspaceComputed = {
  nodeToolPending() {
    const running = (run) => ["PENDING", "RUNNING"].includes(run?.status);
    return (
      this.reportAnalysisPending ||
      this.reportNarrativeSaving ||
      this.reportQualitySaving ||
      (this.reportNarrative.candidate_runs || []).some(running) ||
      (this.reportNarrative.fragment_runs || []).some(running) ||
      running(this.reportQuality.latest_validator_run)
    );
  },
  selectedReportStep() {
    return (
      this.reportCase?.workflow_instance?.steps.find(
        (step) => step.step_key === this.selectedReportStepKey,
      ) || null
    );
  },
  canEditSelectedReportStep() {
    return (
      this.selectedReportStep?.id === this.currentReportStep?.id &&
      this.currentReportStep?.status === "IN_REVIEW" &&
      canHandleStep(this.selectedReportStep, this.staffActor) &&
      this.workspace?.request?.status !== "needs_info" &&
      !["DELIVERED", "CANCELLED"].includes(this.reportCase?.status)
    );
  },
  nodeFindings() {
    return nodeAssets(
      this.reportCaseContent,
      this.selectedReportStep,
      "findings",
    );
  },
  nodeFragments() {
    return nodeAssets(
      this.reportCaseContent,
      this.selectedReportStep,
      "fragments",
    );
  },
  visibleNodeFindings() {
    return selected(
      this.nodeFindings,
      this.nodeRecordKeys.findings,
      "finding_key",
    );
  },
  visibleNodeFragments() {
    return selected(
      this.nodeFragments,
      this.nodeRecordKeys.fragments,
      "fragment_key",
    );
  },
  nodeQualityItems() {
    return (this.reportQuality.issues || []).map((issue) => ({
      ...issue,
      key: String(issue.id),
      title: `${this.assetStatusLabel(issue.status)} · ${this.qualityIssueLabel(issue.issue_type)} · ${this.qualityIssueMessage(issue)}`,
    }));
  },
  visibleNodeQualityIssues() {
    return selected(
      this.reportQuality.issues || [],
      this.nodeRecordKeys.quality,
      "id",
    );
  },
  nodeNarrativeCandidates() {
    return [...(this.reportNarrative.candidate_runs || [])]
      .sort((a, b) => b.id - a.id)
      .flatMap((run) =>
        (run.output_parsed?.candidates || []).map((candidate) => ({
          key: `${run.id}:${candidate.candidate_key}`,
          title: candidate.theme,
          run,
          candidate,
        })),
      );
  },
  visibleNarrativeCandidateRuns() {
    const item = selected(
      this.nodeNarrativeCandidates,
      this.nodeRecordKeys.candidate,
      "key",
    )[0];
    return item
      ? [
          {
            ...item.run,
            output_parsed: {
              ...item.run.output_parsed,
              candidates: [item.candidate],
            },
          },
        ]
      : [...(this.reportNarrative.candidate_runs || [])]
          .sort((a, b) => b.id - a.id)
          .slice(0, 1);
  },
  visiblePlannedFragments() {
    return selected(
      this.nodePlannedFragments,
      this.nodeRecordKeys.planned,
      "fragment_key",
    );
  },
  nodePlannedFragments() {
    return (this.reportContentPlan?.fragments || []).map((fragment) => ({
      ...fragment,
      title: this.fragmentTitle(fragment.fragment_key, fragment),
    }));
  },
  visibleNarrativeFragmentRuns() {
    const key = this.visiblePlannedFragments[0]?.fragment_key;
    return (this.reportNarrative.fragment_runs || [])
      .filter((run) => run.target_key === key)
      .slice(0, 1);
  },
  reportWorkspaceSections() {
    return nodeViews(this.selectedReportStepKey);
  },
};

export const nodeWorkspaceMethods = {
  selectReportNode(stepKey) {
    if (
      !this.reportCase?.workflow_instance?.steps.some(
        (step) => step.step_key === stepKey,
      )
    )
      return;
    this.selectedReportStepKey = stepKey;
    this.nodeRecordKeys = {
      findings: "",
      fragments: "",
      quality: "",
      planned: "",
      candidate: "",
    };
    this.nodeWritingMode = "plan";
    this.showNodeAddForm = false;
    this.reportStepReturn.visible = false;
    this.setReportWorkspaceSection("overview");
  },
  openReportOverview() {
    this.selectedReportStepKey = "";
    this.workspaceSection = "overview";
    this.syncWorkspaceRoute(this.selectedRequest.id, "overview", {
      history: "push",
    });
    this.scrollWorkspaceToTop();
  },
  restoreReportNode(query = this.$route.query) {
    const location = resolveNodeLocation(
      this.reportCase?.workflow_instance?.steps || [],
      this.currentReportStep,
      query,
    );
    this.selectedReportStepKey = location.stepKey;
    this.workspaceSection = location.section;
  },
  async runReportNodeTool(requestedTool) {
    const tool = nodeTools(this.selectedReportStep, this.currentReportStep, {
      pending: this.nodeToolPending,
      planReady:
        this.reportNarrative.current_plan?.status === "CONFIRMED" &&
        this.reportContentPlan?.status === "READY",
      generationStatus: this.reportGeneration?.status,
    }).find((item) => item.action === requestedTool.action);
    if (!tool || tool.disabled || !canHandleStep(this.selectedReportStep, this.staffActor)) return;
    this.setReportWorkspaceSection(tool.destination);
    const method = {
      analysis: "startReportAnalysisDraft",
      narrative: "generateNarrativeCandidates",
      authoring: "generateCompleteReport",
      quality: "runReportQuality",
    }[tool.action];
    await this[method]();
  },
};
