import test from "node:test";
import assert from "node:assert/strict";
import {
  checkpointRendered,
  nodeAssets,
  nodeCheckpoint,
  nextCheckpointSection,
  nextNodeSection,
  nodeTools,
  resolveNodeLocation,
  nodeViews,
  workspaceFocusTargetId,
} from "./node-workspace.js";
import {
  nodeWorkspaceComputed,
  nodeWorkspaceMethods,
} from "./node-workspace-state.js";

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
    { stepKey: "S2", section: "upstream" },
  );
  assert.equal(
    nodeViews("S5").some((view) => view.id === "quality"),
    false,
  );
  assert.equal(
    nodeViews("S5").find((view) => view.id === "fragments").label,
    "完整报告审阅",
  );
});

test("whole-node checkpoints stay on the matching workflow substep", () => {
  assert.equal(nodeCheckpoint("S1", "birth-time"), "birth_data");
  assert.equal(nodeCheckpoint("S1", "calculation"), "");
  for (const stepKey of ["S1", "S2", "S3", "S4"]) {
    assert.equal(nodeCheckpoint(stepKey, "findings"), "findings");
    assert.equal(nodeCheckpoint(stepKey, "fragments"), "analysis");
    assert.equal(nodeCheckpoint(stepKey, "signoff"), "node");
  }
  assert.equal(nodeCheckpoint("S5", "writing"), "narrative");
  assert.equal(nodeCheckpoint("S5", "fragments"), "report");
  assert.equal(nodeCheckpoint("S6", "quality"), "");
  assert.equal(nodeCheckpoint("S6", "fragments"), "report");
  assert.equal(nodeCheckpoint("S6", "signoff"), "node");
});

test("workflow sections advance in order while keeping review pages between decisions", () => {
  assert.equal(nextNodeSection("S1", "upstream"), "birth-time");
  assert.equal(nextNodeSection("S1", "calculation"), "analysis");
  assert.equal(nextNodeSection("S2", "analysis"), "findings");
  assert.equal(nextNodeSection("S6", "quality"), "fragments");
  assert.equal(nextNodeSection("S1", "signoff"), "");

  assert.equal(nextCheckpointSection("S1", "birth_data"), "calculation");
  assert.equal(nextCheckpointSection("S1", "findings"), "fragments");
  assert.equal(nextCheckpointSection("S3", "analysis"), "signoff");
  assert.equal(nextCheckpointSection("S5", "report"), "signoff");
  assert.equal(nextCheckpointSection("S6", "report"), "signoff");
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

test("legacy node links restore the current workspace section", () => {
  const context = {
    reportCase: { workflow_instance: { steps } },
    currentReportStep: steps[1],
    selectedReportStepKey: "",
    workspaceSection: "",
  };

  nodeWorkspaceMethods.restoreReportNode.call(context, {
    step: "S1",
    section: "evidence",
  });
  assert.equal(context.selectedReportStepKey, "S1");
  assert.equal(context.workspaceSection, "calculation");

  nodeWorkspaceMethods.restoreReportNode.call(context, {
    step: "S2",
    section: "inputs",
  });
  assert.equal(context.selectedReportStepKey, "S2");
  assert.equal(context.workspaceSection, "upstream");
});

test("completed S1 keeps the birth data checkpoint readable", () => {
  assert.equal(checkpointRendered("S1", "birth-time", true), true);
  assert.equal(checkpointRendered("S1", "birth-time", false), true);
  assert.equal(checkpointRendered("S1", "findings", true), true);
  assert.equal(checkpointRendered("S1", "findings", false), false);
  assert.equal(checkpointRendered("S6", "fragments", false), false);
  assert.equal(checkpointRendered("S1", "upstream", true), false);
});

test("completed nodes keep their node review checkpoint readable", () => {
  assert.equal(checkpointRendered("S5", "signoff", false, "COMPLETED"), true);
  assert.equal(checkpointRendered("S6", "signoff", false, "COMPLETED"), true);
  assert.equal(checkpointRendered("S5", "signoff", false, "PENDING"), false);
  assert.equal(checkpointRendered("S5", "signoff", false, "IN_REVIEW"), false);
  assert.equal(checkpointRendered("S5", "fragments", false, "COMPLETED"), false);
  assert.equal(checkpointRendered("S5", "signoff", true, "IN_REVIEW"), true);
});

test("check problem cards point at the exact finding or fragment they flag", () => {
  assert.equal(workspaceFocusTargetId("fragments", "ziwei"), "report-fragment-ziwei");
  assert.equal(
    workspaceFocusTargetId("fragments", "analysis.s2.stars"),
    "report-fragment-analysis.s2.stars",
  );
  assert.equal(workspaceFocusTargetId("findings", "001-abc"), "report-finding-001-abc");
  assert.equal(workspaceFocusTargetId("fragments", ""), "");
  assert.equal(workspaceFocusTargetId("findings", null), "");
  assert.equal(workspaceFocusTargetId("analysis", "ziwei"), "");
});