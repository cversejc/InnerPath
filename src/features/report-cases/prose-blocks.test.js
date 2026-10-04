import test from "node:test";
import assert from "node:assert/strict";
import { proseBlocks } from "./prose-blocks.js";

test("report prose renders complete table columns and preserves surrounding paragraphs", () => {
  const result = proseBlocks(
    "阶段说明\n\n| 计算阶段 | 观察入口 |\n| --- | --- |\n| 戊辰 2017–2026 | 核对真实反馈 |\n\n这些内容不是确定预测。",
  );
  assert.deepEqual(result, [
    { type: "text", text: "阶段说明" },
    {
      type: "table",
      headers: ["计算阶段", "观察入口"],
      rows: [["戊辰 2017–2026", "核对真实反馈"]],
    },
    { type: "text", text: "这些内容不是确定预测。" },
  ]);
});
test("unrecognized pipe syntax and incomplete rows remain in readable text", () => {
  assert.deepEqual(proseBlocks("A | B\n普通说明\n尾句"), [
    { type: "text", text: "A | B\n普通说明\n尾句" },
  ]);
  const result = proseBlocks(
    "| A | B |\n| --- | --- |\n| too | many | cells |",
  );
  assert.equal(result[1].text, "| too | many | cells |");
});
test("HTML-like source text is retained as text instead of emitted as rendered HTML", () => {
  const source = "<img src=x onerror=alert(1)>\n<script>bad()</script>";
  assert.deepEqual(proseBlocks(source), [{ type: "text", text: source }]);
});
