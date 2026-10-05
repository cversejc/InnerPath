import test from "node:test";
import assert from "node:assert/strict";
import {
  buildSkillCatalog,
  REPORT_SKILLS,
  runSkillKey,
  displayText,
  patchInstructions,
  readableEntries,
  evaluationCheckLabel,
} from "./presentation.js";

test("catalog groups versions without losing custom skills or changing runtime keys", () => {
  const versions = [
    { skill_key: "report.s1_foundation_analysis", name: "S1" },
    { skill_key: "report.s1_foundation_analysis", name: "S1 old" },
    { skill_key: "custom.review", name: "个性化复核" },
  ];
  const catalog = buildSkillCatalog(versions);
  assert.equal(
    catalog.filter((item) => item.key === "report.s1_foundation_analysis")
      .length,
    1,
  );
  assert.equal(catalog.at(-1).name, "个性化复核");
  assert.deepEqual(
    new Set(REPORT_SKILLS.map((item) => item.step)),
    new Set(["S1", "S2", "S3", "S4", "S5", "S6"]),
  );
  assert.equal(versions[0].name, "S1");
});

test("actual report run target types resolve to the owning skill", () => {
  assert.equal(
    runSkillKey({ target_type: "REPORT_ANALYSIS_DRAFT", target_key: "S2" }),
    "report.s2_psychology_mapping",
  );
  assert.equal(
    runSkillKey({ target_type: "NARRATIVE_CANDIDATES" }),
    "report.narrative_plan",
  );
  assert.equal(
    runSkillKey({
      target_type: "REPORT_FRAGMENT",
      target_key: "chapter1.identity",
    }),
    "report.fragment_authoring",
  );
  assert.equal(
    runSkillKey({ target_type: "REPORT_QA" }),
    "report.final_validator",
  );
  assert.equal(
    runSkillKey({ target_type: "REPORT_CHAPTER_VALIDATION" }),
    "report.final_validator",
  );
  assert.equal(runSkillKey({ target_type: "UNKNOWN" }), "");
});

test("instruction form preserves contracts, runtime identity, knowledge and unknown settings", () => {
  const source = {
    identity: { skill_key: "report.s1_foundation_analysis", name: "原名" },
    instructions: {
      objective: "旧目标",
      methodology: ["旧方法"],
      sop_contract: { topics: ["题目"] },
    },
    output_contract: { required: ["findings"] },
    knowledge_policy: { snapshot: ["原知识"] },
    extension: { future: true },
  };
  const updated = JSON.parse(
    patchInstructions(JSON.stringify(source), {
      objective: "新目标",
      methodology: ["新方法"],
    }),
  );
  assert.deepEqual(updated.identity, source.identity);
  assert.deepEqual(
    updated.instructions.sop_contract,
    source.instructions.sop_contract,
  );
  assert.deepEqual(updated.output_contract, source.output_contract);
  assert.deepEqual(updated.knowledge_policy, source.knowledge_policy);
  assert.deepEqual(updated.extension, source.extension);
  assert.equal(source.instructions.objective, "旧目标");
  assert.equal(updated.instructions.objective, "新目标");
  assert.throws(() => patchInstructions("[]", { objective: "x" }));
});

test("reader translates display labels while technical references remain in original data", () => {
  const source = {
    findings: [{ claim: "Evidence 支持 Finding", finding_key: "f1" }],
    unknown_schema: { exact_key: "x" },
  };
  const entries = readableEntries(source);
  assert.equal(entries[0].label, "专业判断");
  assert.equal(
    displayText(entries[0].value[0].claim),
    "资料依据 支持 专业判断",
  );
  assert.equal(source.findings[0].finding_key, "f1");
  assert.ok(source.unknown_schema);
  assert.equal(displayText("BLOCK", "semantic_role"), "当前卡点");
  assert.equal(displayText("BLOCK", "severity"), "必须处理");
  assert.equal(displayText("repetition"), "重复表达");
  assert.equal(displayText("S2 心理 Signal"), "第 2 步 心理 线索");
  assert.equal(displayText("report.blocks.breakthrough"), "整合与破局方向");
  assert.equal(
    evaluationCheckLabel("required:findings"),
    "包含必需内容 · 专业判断",
  );
});
