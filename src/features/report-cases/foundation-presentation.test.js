import test from "node:test";
import assert from "node:assert/strict";
import { buildFoundationView } from "./foundation-presentation.js";

test("stored calculation facts remain intact and missing time does not acquire a pillar or fortune periods", () => {
  const data = {
    bazi: { day: { stem: "乙", branch: "丑" }, day_master: "乙" },
    bazi_facts: {
      day_master: { stem: "乙", element: "木", polarity: "阴" },
      limitations: ["出生时间未知"],
    },
    limitations: ["出生时间未知"],
    input_assumptions: ["日期仅为演示"],
  };
  const original = JSON.stringify(data);
  const view = buildFoundationView(data);
  assert.equal(view.master, "乙 · 阴 · 木");
  assert.equal(view.pillars.find((p) => p.key === "hour").available, false);
  assert.deepEqual(view.dayun, []);
  assert.deepEqual(view.limitations, ["出生时间未知"]);
  assert.deepEqual(view.assumptions, ["日期仅为演示"]);
  assert.equal(JSON.stringify(data), original);
});

test("ten god counts and stored period dates are displayed without strength or interpretation scores", () => {
  const data = {
    bazi_facts: {
      ten_god_counts: {
        visible: { 正官: 1 },
        hidden: { 正官: 2 },
        absent: ["比肩"],
      },
      dayun: [
        {
          pillar: "戊辰",
          start_year: 2017,
          end_year: 2026,
          start_age: 14,
          end_age: 23,
        },
      ],
      interactions: [
        {
          symbols: "庚乙",
          type: "天干五合",
          pillars: ["month", "day"],
          note: "有合不等于合化",
        },
      ],
    },
  };
  const view = buildFoundationView(data);
  assert.deepEqual(view.counts, [
    { name: "正官", visible: 1, hidden: 2 },
    { name: "比肩", visible: 0, hidden: 0 },
  ]);
  assert.match(view.countNote, /不代表旺衰/);
  assert.deepEqual(view.dayun, data.bazi_facts.dayun);
  assert.equal(view.interactions[0].positions, "月柱 ↔ 日柱");
  assert.equal(view.interactions[0].note, "有合不等于合化");
  assert.equal("strength" in view, false);
});

test("key palaces retain full stars and brightness while birth and flying transformations remain separate", () => {
  const data = {
    ziwei: {
      life_palace: { branch: "酉", main_stars: ["天府"] },
      body_palace: { branch: "丑", main_stars: ["天相"] },
      palaces: [
        {
          name: "命宮",
          branch: "酉",
          main_stars: ["天府"],
          aux_stars: ["天福"],
          brightness: { 天府: "旺" },
        },
      ],
      year_transformations: { 廉貞: "祿" },
      flying_transformations: [
        {
          source_palace: "命宮",
          target_palaces: ["福德宮"],
          transformation: "忌",
          star: "贪狼",
        },
      ],
    },
  };
  const view = buildFoundationView(data);
  assert.deepEqual(view.keyPalaces[0].aux_stars, ["天福"]);
  assert.equal(view.keyPalaces[0].brightness.天府, "旺");
  assert.equal(view.transformations[0].source, "命宫");
  assert.equal(view.transformations[0].targets, "福德宫");
  assert.deepEqual(view.yearTransformations, [{ star: "廉貞", type: "祿" }]);
  assert.equal(data.ziwei.flying_transformations[0].source_palace, "命宮");
});

test("legacy and unrecognized calculation shapes remain readable without inventing chart fields", () => {
  assert.equal(
    buildFoundationView({
      year: { stem: "甲", branch: "子" },
      day_master: "乙",
    }).pillars[0].available,
    true,
  );
  assert.equal(
    buildFoundationView({ external_result: { unknown: 1 } }).hasChart,
    false,
  );
  assert.equal(buildFoundationView(null).hasChart, false);
});
