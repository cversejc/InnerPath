// Read-only projections of stored calculations; no chart facts are inferred here.
const PILLAR_LABELS = {
  year: "年柱",
  month: "月柱",
  day: "日柱",
  hour: "时柱",
};
const CONVENTION_LABELS = {
  pillars: "四柱规则",
  dayun: "起运规则",
  time: "时间口径",
  strength_and_useful_gods: "解释职责",
};
const PALACE_LABELS = {
  life_palace: "命宫",
  body_palace: "身宫",
  wellbeing_palace: "福德宫",
  career_palace: "官禄宫",
  wealth_palace: "财帛宫",
  relationship_palace: "夫妻宫",
};
const list = (value) => (Array.isArray(value) ? value : []);
const object = (value) =>
  value && typeof value === "object" && !Array.isArray(value) ? value : {};
export const palaceLabel = (value) =>
  String(value || "")
    .replaceAll("宮", "宫")
    .replaceAll("祿", "禄")
    .replaceAll("財", "财")
    .replaceAll("遷", "迁");

export function buildFoundationView(value) {
  const data = object(value);
  const bazi = object(
    data.bazi || (data.year || data.day_master ? data : null),
  );
  const facts = object(data.bazi_facts);
  const master = object(facts.day_master);
  const ziwei = object(data.ziwei);
  const palaces = list(ziwei.palaces).map((palace) => ({
    ...palace,
    name: palaceLabel(palace.name),
  }));
  const keyPalaces = Object.entries(PALACE_LABELS).flatMap(([key, label]) => {
    const palace = object(ziwei[key]);
    if (!Object.keys(palace).length) return [];
    return [
      {
        ...(palaces.find((item) => item.branch === palace.branch) || palace),
        label,
      },
    ];
  });
  const counts = object(facts.ten_god_counts);
  const godNames = [
    ...new Set([
      ...Object.keys(object(counts.visible)),
      ...Object.keys(object(counts.hidden)),
      ...list(counts.absent),
    ]),
  ];
  return {
    hasChart: Boolean(
      Object.keys(bazi).length ||
      Object.keys(facts).length ||
      Object.keys(ziwei).length,
    ),
    pillars: Object.entries(PILLAR_LABELS).map(([key, label]) => {
      const pillar = object(facts.pillars?.[key] || bazi[key]);
      return {
        ...pillar,
        key,
        label,
        available: Boolean(pillar.stem && pillar.branch),
        hidden_stems: list(pillar.hidden_stems),
      };
    }),
    master: [
      master.stem ||
        (typeof bazi.day_master === "string" ? bazi.day_master : ""),
      master.polarity,
      master.element,
    ]
      .filter(Boolean)
      .join(" · "),
    dates: [
      ["公历", data.solar_date],
      ["农历", data.lunar_date],
      ["生肖", data.zodiac],
      ["纳音", data.nayin],
    ].filter(([, value]) => value),
    assumptions: list(data.input_assumptions),
    limitations: [
      ...new Set([...list(data.limitations), ...list(facts.limitations)]),
    ],
    counts: godNames.map((name) => ({
      name,
      visible: counts.visible?.[name] ?? 0,
      hidden: counts.hidden?.[name] ?? 0,
    })),
    countNote: counts.note || "出现次数不代表旺衰，也不能证明心理面向缺失。",
    interactions: list(facts.interactions).map((item) => ({
      ...item,
      positions: list(item.pillars)
        .map((key) => PILLAR_LABELS[key] || "其他位置")
        .join(" ↔ "),
    })),
    dayun: list(facts.dayun),
    palaces,
    keyPalaces,
    sanfang: list(ziwei.life_sanfang_sizheng).map((palace) =>
      palaceLabel(palace.name),
    ),
    palaceSources: [
      ...new Set(
        list(ziwei.flying_transformations).map((item) =>
          palaceLabel(item.source_palace),
        ),
      ),
    ],
    transformations: list(ziwei.flying_transformations).map((item) => ({
      ...item,
      source: palaceLabel(item.source_palace),
      targets:
        list(item.target_palaces).map(palaceLabel).join("、") || "未记录落宫",
    })),
    yearTransformations: Object.entries(object(ziwei.year_transformations)).map(
      ([star, type]) => ({ star, type }),
    ),
    ziweiSummary: [
      ["命主", ziwei.ming_zhu],
      ["身主", ziwei.shen_zhu],
      ["五行局", ziwei.wu_xing_ju],
    ].filter(([, value]) => value),
    conventions: Object.entries(CONVENTION_LABELS).flatMap(([key, label]) =>
      facts.conventions?.[key] ? [{ label, text: facts.conventions[key] }] : [],
    ),
    note: bazi.note || data.note || "",
  };
}
