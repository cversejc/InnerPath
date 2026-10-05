import test from "node:test";
import assert from "node:assert/strict";
import {
  nodeAssets,
  nodeTools,
  resolveNodeLocation,
  nodeViews,
} from "./node-workspace.js";
import { nodeWorkspaceComputed, nodeWorkspaceMethods } from "./node-workspace-state.js";

const steps = ["S1", "S2", "S3", "S4", "S5", "S6"].map((step_key, index) => ({
  id: index + 1,
  step_key,
  sequence_no: index + 1,
  status: index === 0 ? "COMPLETED" : index === 1 ? "IN_REVIEW" : "PENDING",
}));

test("a report node stays read-only while its case waits for user information", () => {
  const step = {
    id: 1,
    status: "IN_REVIEW",
    required_capability: "mingli",
    assignee_id: 4,
  };
  const context = {
    selectedReportStep: step,
    currentReportStep: step,
    staffActor: { id: 4, role: "consultant", consultant_type: "mingli" },
    reportCase: { status: "ACTIVE" },
    workspace: { request: { status: "accepted" } },
  };

  assert.equal(nodeWorkspaceComputed.canEditSelectedReportStep.call(context), true);
  context.workspace.request.status = "needs_info";
  assert.equal(nodeWorkspaceComputed.canEditSelectedReportStep.call(context), false);
});

test("node links restore the selected history without exposing unrelated functional pages", () => {
  assert.deepEqual(
    resolveNodeLocation(steps, steps[1], { step: "S1", section: "findings" }),
    { stepKey: "S1", section: "findings" },
  );
  assert.deepEqual(
    resolveNodeLocation(steps, steps[1], { step: "S1", section: "quality" }),
    { stepKey: "S1", section: "overview" },
  );
  assert.deepEqual(
    resolveNodeLocation(steps, steps[1], { step: "all", section: "overview" }),
    { stepKey: "", section: "overview" },
  );
  assert.deepEqual(
    resolveNodeLocation(steps, steps[1], { section: "quality" }),
    { stepKey: "S6", section: "quality" },
  );
  assert.deepEqual(
    resolveNodeLocation(steps, steps[1], { section: "evidence" }),
    { stepKey: "S2", section: "inputs" },
  );
  assert.equal(
    nodeViews("S5").some((view) => view.id === "quality"),
    false,
  );
});

test("review assets belong to the selected node; report review excludes internal analysis", () => {
  const content = {
    findings: [{ owner_step_task_id: 1 }, { owner_step_task_id: 2 }],
    fragments: [
      { owner_step_task_id: 1, fragment_type: "ANALYSIS" },
      { owner_step_task_id: 2, fragment_type: "ANALYSIS" },
      { owner_step_task_id: 5, fragment_type: "REPORT" },
    ],
  };
  assert.equal(nodeAssets(content, steps[0], "findings").length, 1);
  assert.deepEqual(nodeAssets(content, steps[1], "fragments"), [
    content.fragments[1],
  ]);
  assert.deepEqual(nodeAssets(content, steps[5], "fragments"), [
    content.fragments[2],
  ]);
});

test("skills enforce historical, future, not-started, busy and narrative prerequisites", () => {
  assert.equal(nodeTools(steps[0], steps[1])[0].disabled, true);
  assert.equal(nodeTools(steps[2], steps[1])[0].disabled, true);
  assert.equal(
    nodeTools(
      { ...steps[1], status: "READY" },
      { ...steps[1], status: "READY" },
    )[0].disabled,
    true,
  );
  assert.equal(
    nodeTools(steps[1], steps[1], { pending: true })[0].disabled,
    true,
  );
  assert.equal(nodeTools(steps[1], steps[1])[0].disabled, false);
  const writer = { ...steps[4], status: "IN_REVIEW" };
  assert.equal(nodeTools(writer, writer)[1].disabled, true);
  assert.equal(
    nodeTools(writer, writer, { planReady: true })[1].disabled,
    false,
  );
  for (const generationStatus of [
    "READY_FOR_REVIEW",
    "COHERENCE_CHECK",
    "NEEDS_INPUT",
  ]) {
    assert.equal(
      nodeTools(writer, writer, { planReady: true, generationStatus })[1]
        .disabled,
      true,
    );
  }
});

test("tool dispatch invokes the actual workflow command and opens its review destination", async () => {
  for (const [key, action, method, destination] of [
    ["S2", "analysis", "startReportAnalysisDraft", "suggestions"],
    ["S5", "narrative", "generateNarrativeCandidates", "writing"],
    ["S5", "authoring", "generateCompleteReport", "fragments"],
    ["S6", "quality", "runReportQuality", "quality"],
  ]) {
    const step = {
        ...steps.find((item) => item.step_key === key),
        status: "IN_REVIEW",
      },
      calls = [];
    const ctx = {
      staffActor: { id: 1, role: "consultant" },
      selectedReportStep: step,
      currentReportStep: step,
      reportNarrative: { current_plan: { status: "CONFIRMED" } },
      reportContentPlan: { status: "READY" },
      setReportWorkspaceSection: (section) => calls.push(section),
      [method]: async () => calls.push(method),
    };
    await nodeWorkspaceMethods.runReportNodeTool.call(ctx, { action });
    assert.deepEqual(calls, [destination, method]);
  }
  const history = {
    selectedReportStep: steps[0],
    currentReportStep: steps[1],
    reportNarrative: {},
    setReportWorkspaceSection: () => assert.fail("history must not dispatch"),
    startReportAnalysisDraft: () => assert.fail("history must not mutate"),
  };
  await nodeWorkspaceMethods.runReportNodeTool.call(history, {
    action: "analysis",
  });
});
