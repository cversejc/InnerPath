import { Button as VanButton } from "vant";
import { hasRole } from "../../stores/auth.js";
import api from "./api.js";
import RunDetail from "./components/RunDetail.vue";
import ExamplesPanel from "./components/ExamplesPanel.vue";
import EvaluationPanel from "./components/EvaluationPanel.vue";
import SkillInstructions from "./components/SkillInstructions.vue";
import {
  buildSkillCatalog,
  REPORT_SKILLS,
  runSkillKey,
} from "./presentation.js";
import {
  parseSpecification,
  feedbackPreviewFromRun,
  isReportSkillFeedbackRun,
  runInputPreviewFromRun,
  RUN_STATUS_LABELS,
  sampleInput,
  VERSION_STATUS_LABELS,
} from "./studio.js";

const POLL_INTERVAL = 2500;
const S1_FOUNDATION_SKILL_KEY = REPORT_SKILLS.find((item) => item.step === "S1")?.key;
const REASONING_GUIDANCE_SKILL_KEYS = new Set(
  REPORT_SKILLS.filter((item) => ["S1", "S2", "S3"].includes(item.step)).map(
    (item) => item.key,
  ),
);

function reasoningGuidanceFromVersion(version) {
  const guidance = version?.reasoning_guidance;
  if (guidance && typeof guidance === "object")
    return JSON.parse(JSON.stringify(guidance));
  return { objective: "", methodology: [] };
}

export default {
  name: "SkillStudio",
  components: {
    RunDetail,
    ExamplesPanel,
    EvaluationPanel,
    SkillInstructions,
    VanButton,
  },
  data() {
    const isAdmin = hasRole("admin");
    const selectedSkillKey =
      REPORT_SKILLS.find((item) => item.key === this.$route.query.skill)?.key ||
      REPORT_SKILLS.find((item) => item.step === this.$route.query.step)?.key ||
      REPORT_SKILLS[0].key;
    const validPanels = [
      "overview",
      "examples",
      "runs",
      ...(isAdmin ? ["skills", "feedback", "debug", "evaluation"] : []),
    ];
    const requestedPanel = validPanels.includes(this.$route.query.panel)
      ? this.$route.query.panel
      : "overview";
    const activeAdminTab =
      isAdmin && REASONING_GUIDANCE_SKILL_KEYS.has(selectedSkillKey)
        ? requestedPanel === "overview"
          ? "skills"
          : requestedPanel === "evaluation"
            ? "debug"
            : requestedPanel
        : requestedPanel;
    return {
      isAdmin,
      versions: [],
      selectedVersion: null,
      selectedSkillKey,
      activeAdminTab,
      specificationText: "",
      reasoningGuidance: { objective: "", methodology: [] },
      inputText: JSON.stringify(sampleInput(), null, 2),
      runtimeInstruction: "",
      runs: [],
      selectedRun: null,
      caseId: this.$route.query.case_id
        ? String(this.$route.query.case_id)
        : "",
      caseIdDraft: this.$route.query.case_id
        ? String(this.$route.query.case_id)
        : "",
      sourceRunId: Number.isSafeInteger(Number(this.$route.query.run_id)) && Number(this.$route.query.run_id) > 0
        ? Number(this.$route.query.run_id)
        : null,
      feedbackSourceRun: null,
      inputPreviewSourceRun: null,
      previewRunId: null,
      loading: false,
      saving: false,
      publishing: false,
      running: false,
      caseLoading: false,
      message: "",
      messageKind: "",
      pollTimer: null,
      RUN_STATUS_LABELS,
      VERSION_STATUS_LABELS,
    };
  },
  computed: {
    isS1Admin() {
      return this.isAdmin && this.selectedSkillKey === S1_FOUNDATION_SKILL_KEY;
    },
    isReasoningGuidanceAdmin() {
      return (
        this.isAdmin && REASONING_GUIDANCE_SKILL_KEYS.has(this.selectedSkillKey)
      );
    },
    catalog() {
      return buildSkillCatalog(this.versions);
    },
    selectedSkill() {
      return (
        this.catalog.find((item) => item.key === this.selectedSkillKey) ||
        this.catalog[0]
      );
    },
    skillVersions() {
      return this.versions
        .filter((item) => item.skill_key === this.selectedSkillKey)
        .sort((a, b) => b.version - a.version);
    },
    visibleRuns() {
      return this.isAdmin
        ? this.runs
        : this.runs.filter((run) => runSkillKey(run) === this.selectedSkillKey);
    },
    feedbackRuns() {
      if (!this.isAdmin) return [];
      const rows = this.visibleRuns.filter(
        isReportSkillFeedbackRun,
      );
      if (
        this.feedbackSourceRun &&
        this.versions.some(
          (version) =>
            version.id === this.feedbackSourceRun.skill_version_id &&
            version.skill_key === this.selectedSkillKey,
        ) &&
        !rows.some((run) => run.id === this.feedbackSourceRun.id)
      )
        rows.push(this.feedbackSourceRun);
      return rows.sort((left, right) => right.id - left.id);
    },
    previewRun() {
      if (!this.previewRunId) return null;
      return (
        this.runs.find((run) => run.id === this.previewRunId) ||
        (this.selectedRun?.id === this.previewRunId ? this.selectedRun : null)
      );
    },
    studioTabs() {
      if (this.isReasoningGuidanceAdmin)
        return [
          { id: "skills", label: "维护思路" },
          { id: "debug", label: "试用与评估" },
          { id: "examples", label: "参考与记录" },
        ];
      return [
        { id: "overview", label: "使用说明" },
        ...(this.isAdmin ? [{ id: "skills", label: "技能维护" }] : []),
        { id: "examples", label: "示例库" },
        { id: "runs", label: "运行记录" },
        ...(this.isAdmin
          ? [
              { id: "feedback", label: `咨询师反馈${this.feedbackRuns.length ? ` · ${this.feedbackRuns.length}` : ""}` },
              { id: "debug", label: "试运行" },
              { id: "evaluation", label: "质量评估" },
            ]
          : []),
      ];
    },
    studioReturnLocation() {
      const fallback = "/staff";
      const target =
        typeof this.$route.query.return_to === "string"
          ? this.$route.query.return_to
          : "";
      if (target === "/staff" || target.startsWith("/staff?")) return target;
      if (this.isAdmin && (target === "/admin" || target.startsWith("/admin?")))
        return target;
      return fallback;
    },
    editable() {
      return this.isAdmin && this.selectedVersion?.status === "DRAFT";
    },
    specError() {
      if (!this.editable) return "";
      let instructions;
      if (REASONING_GUIDANCE_SKILL_KEYS.has(this.selectedSkillKey)) {
        instructions = this.reasoningGuidance || {};
      } else {
        const parsed = parseSpecification(this.specificationText);
        if (parsed.error) return parsed.error;
        return "";
      }
      if (!String(instructions.objective || "").trim())
        return "请填写 AI 分析目标。";
      if (String(instructions.objective).length > 1200)
        return "AI 分析目标不超过 1200 字。";
      if (
        !Array.isArray(instructions.methodology) ||
        !instructions.methodology.some((item) => String(item).trim())
      )
        return "请填写分析目标，并至少保留一条分析思路。";
      if (
        instructions.methodology.length > 40 ||
        instructions.methodology.some((item) => String(item).length > 1000)
      )
        return "分析思路最多 40 条，每条不超过 1000 字。";
      return "";
    },
    inputError() {
      if (!this.isAdmin) return "";
      try {
        const parsed = JSON.parse(this.inputText);
        return parsed && typeof parsed === "object" && !Array.isArray(parsed)
          ? ""
          : "输入快照必须是 JSON 对象。";
      } catch (error) {
        return `JSON 格式错误：${error.message}`;
      }
    },
  },
  mounted() {
    if (this.isAdmin) this.loadVersions();
    else if (this.caseId) this.loadCaseRuns();
  },
  beforeUnmount() {
    this.clearPoll();
  },
  methods: {
    async loadVersions() {
      this.loading = true;
      try {
        this.versions = await api.getSkillVersions();
        if (
          !this.selectedVersion &&
          this.versions.some(
            (item) => item.skill_key === this.$route.query.skill,
          )
        )
          this.selectedSkillKey = this.$route.query.skill;
        let feedbackVersion = null;
        if (this.isAdmin && this.sourceRunId && !this.feedbackSourceRun) {
          try {
            const sourceRun = await api.getSkillRun(this.sourceRunId);
            const sourceVersion = this.versions.find(
              (item) => item.id === sourceRun.skill_version_id,
            );
            if (
              sourceVersion?.skill_key &&
              isReportSkillFeedbackRun(sourceRun) &&
              sourceRun.report_case_id
            ) {
              this.selectedSkillKey = sourceVersion.skill_key;
              this.loadFeedbackSource(sourceRun);
              feedbackVersion = sourceVersion;
            } else {
              this.showMessage("反馈记录与当前节点技能不匹配，未加载该记录。", "error");
            }
          } catch (error) {
            this.showMessage(
              error.response?.data?.detail || "无法读取该节点的反馈运行记录。",
              "error",
            );
          }
        }
        const current = feedbackVersion ||
          this.skillVersions.find(
            (item) => item.id === this.selectedVersion?.id,
          ) ||
          this.preferredVersion();
        if (current) this.selectVersion(current);
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "无法读取技能版本。",
          "error",
        );
      } finally {
        this.loading = false;
      }
    },
    selectVersion(version) {
      this.selectedVersion = version;
      this.previewRunId = null;
      this.reasoningGuidance = reasoningGuidanceFromVersion(version);
      this.specificationText =
        REASONING_GUIDANCE_SKILL_KEYS.has(version.skill_key)
          ? ""
          : JSON.stringify(version.specification_json, null, 2);
      this.selectedRun = null;
      this.loadRuns();
    },
    selectSkill(key) {
      this.selectedSkillKey = key;
      this.selectedRun = null;
      this.feedbackSourceRun = null;
      this.inputPreviewSourceRun = null;
      this.changeTab(this.isReasoningGuidanceAdmin ? "skills" : "overview");
      if (this.isAdmin) {
        const version = this.preferredVersion();
        if (version) this.selectVersion(version);
        else {
          this.selectedVersion = null;
          this.runs = [];
        }
      } else this.selectedRun = this.visibleRuns[0] || null;
    },
    selectVersionById(id) {
      const version = this.skillVersions.find((item) => item.id === Number(id));
      if (version) this.selectVersion(version);
    },
    preferredVersion() {
      return (
        (this.isReasoningGuidanceAdmin &&
          this.skillVersions.find((item) => item.status === "DRAFT")) ||
        this.skillVersions.find((item) => item.status === "PUBLISHED") ||
        this.skillVersions[0]
      );
    },
    selectRunById(id) {
      this.selectedRun =
        this.visibleRuns.find((item) => item.id === Number(id)) || null;
    },
    changeTab(tab) {
      this.activeAdminTab = tab;
      this.$router.replace({
        query: {
          ...this.$route.query,
          skill: this.selectedSkillKey,
          panel: tab,
        },
      });
      this.$nextTick(() => this.$refs.workBody?.scrollTo({ top: 0 }));
    },
    studioTabIsActive(tab) {
      if (this.isReasoningGuidanceAdmin && tab === "examples")
        return ["examples", "runs", "feedback"].includes(this.activeAdminTab);
      return this.activeAdminTab === tab;
    },
    async createDraft() {
      if (!this.selectedVersion) return;
      this.saving = true;
      try {
        const created =
          REASONING_GUIDANCE_SKILL_KEYS.has(this.selectedSkillKey)
            ? await api.createSkillDraft(this.selectedVersion.id)
            : await api.createSkillVersion({
                skill_key: this.selectedVersion.skill_key,
                name: this.selectedVersion.name,
                category: this.selectedVersion.category,
                specification_json: this.selectedVersion.specification_json,
              });
        this.versions.unshift(created);
        this.selectVersion(created);
        this.showMessage(
          `已创建${this.selectedSkill.name}第 ${created.version} 版草稿。`,
        );
        return created;
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "创建草稿失败。",
          "error",
        );
      } finally {
        this.saving = false;
      }
    },
    async saveDraft(options = {}) {
      const isReasoningGuidanceSkill = REASONING_GUIDANCE_SKILL_KEYS.has(
        this.selectedSkillKey,
      );
      const parsed = isReasoningGuidanceSkill
        ? null
        : parseSpecification(this.specificationText);
      if (this.specError) {
        this.showMessage(this.specError, "error");
        if (options.rethrow) throw new Error(this.specError);
        return;
      }
      this.saving = true;
      try {
        const updated =
          isReasoningGuidanceSkill
            ? await api.updateSkillReasoningGuidance(this.selectedVersion.id, {
                objective: this.reasoningGuidance.objective,
                methodology: this.reasoningGuidance.methodology,
              })
            : await api.updateSkillVersion(this.selectedVersion.id, {
                name: parsed.value.identity?.name || this.selectedVersion.name,
                category: this.selectedVersion.category,
                specification_json: parsed.value,
              });
        this.replaceVersion(updated);
        this.showMessage("草稿已保存。");
        return updated;
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "保存草稿失败。",
          "error",
        );
        if (options.rethrow) throw error;
      } finally {
        this.saving = false;
      }
    },
    async publish() {
      if (
        !REASONING_GUIDANCE_SKILL_KEYS.has(this.selectedSkillKey) &&
        parseSpecification(this.specificationText).error
      )
        return;
      this.publishing = true;
      try {
        if (this.selectedVersion.status === "DRAFT")
          await this.saveDraft({ rethrow: true });
        const published = await api.publishSkillVersion(
          this.selectedVersion.id,
        );
        this.replaceVersion(published);
        this.showMessage(
          `已发布${this.selectedSkill.name}第 ${published.version} 版。`,
        );
      } catch (error) {
        this.showMessage(error.response?.data?.detail || "发布失败。", "error");
      } finally {
        this.publishing = false;
      }
    },
    replaceVersion(version) {
      this.versions = this.versions.map((item) =>
        item.id === version.id ? version : item,
      );
      this.selectedVersion = version;
      this.reasoningGuidance = reasoningGuidanceFromVersion(version);
      this.specificationText =
        REASONING_GUIDANCE_SKILL_KEYS.has(version.skill_key)
          ? ""
          : JSON.stringify(version.specification_json, null, 2);
    },
    async startRun() {
      if (this.inputError || !this.selectedVersion) return;
      this.running = true;
      try {
        if (this.editable) await this.saveDraft({ rethrow: true });
        const run = await api.runSkill(this.selectedVersion.id, {
          idempotency_key:
            globalThis.crypto?.randomUUID?.() ||
            `studio-${Date.now()}-${Math.random()}`,
          input_data: JSON.parse(this.inputText),
          runtime_instruction: this.runtimeInstruction || null,
        });
        this.selectedRun = run;
        this.previewRunId = run.id;
        await this.loadRuns();
        this.showMessage(`草稿已保存，预览运行 ${run.id} 已加入队列。`);
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "运行请求失败。",
          "error",
        );
      } finally {
        this.running = false;
      }
    },
    loadFeedbackSource(run) {
      const preview = feedbackPreviewFromRun(run);
      if (
        !preview ||
        !this.versions.some(
          (version) =>
            version.id === run.skill_version_id &&
            version.skill_key === this.selectedSkillKey,
        )
      )
        return false;
      this.feedbackSourceRun = run;
      this.inputPreviewSourceRun = run;
      this.sourceRunId = run.id;
      this.inputText = preview.inputText;
      this.runtimeInstruction = preview.runtimeInstruction;
      return true;
    },
    async prepareRunInputPreview(run) {
      if (!this.isAdmin) return;
      const preview = runInputPreviewFromRun(run);
      const sourceVersion = this.versions.find(
        (version) =>
          version.id === run?.skill_version_id &&
          version.skill_key === this.selectedSkillKey,
      );
      if (!preview || !sourceVersion) {
        this.showMessage("运行记录没有可复用的输入，或与当前技能不匹配。", "error");
        return;
      }
      this.inputPreviewSourceRun = run;
      this.feedbackSourceRun = isReportSkillFeedbackRun(run) ? run : null;
      this.sourceRunId = run.id;
      this.inputText = preview.inputText;
      this.runtimeInstruction = preview.runtimeInstruction;
      if (this.selectedVersion?.status !== "DRAFT") {
        if (!this.selectedVersion) this.selectVersion(sourceVersion);
        const draft = await this.createDraft();
        if (!draft) return;
      }
      this.changeTab("debug");
      this.showMessage("已载入这次运行的实际输入，可修改草稿后重新预览。", "");
    },
    async prepareFeedbackPreview(run = this.feedbackSourceRun) {
      if (!this.loadFeedbackSource(run)) return;
      if (!this.selectedVersion || this.selectedVersion.status !== "DRAFT") {
        await this.createDraft();
      }
      if (!this.selectedVersion || this.selectedVersion.status !== "DRAFT") return;
      this.changeTab("skills");
      this.showMessage("已创建草稿并加载该节点的真实输入与咨询师反馈；编辑并保存后可在“试运行”预览。", "");
    },
    async startEvaluation(caseKeys) {
      if (!this.selectedVersion) throw new Error("请先选择技能版本。");
      if (this.editable) await this.saveDraft({ rethrow: true });
      return api.startSkillEvaluation(this.selectedVersion.id, {
        case_keys: caseKeys,
      });
    },
    async loadRuns() {
      if (!this.selectedVersion) return;
      const versionId = this.selectedVersion.id;
      try {
        const runs = await api.getSkillRuns(versionId);
        if (versionId !== this.selectedVersion?.id) return;
        this.runs = runs;
        if (this.selectedRun)
          this.selectedRun =
            this.runs.find((run) => run.id === this.selectedRun.id) ||
            this.selectedRun;
        else this.selectedRun = this.runs[0] || null;
        if (
          this.runs.some((run) => ["PENDING", "RUNNING"].includes(run.status))
        )
          this.startPoll();
        else this.clearPoll();
      } catch (error) {
        if (versionId !== this.selectedVersion?.id) return;
        this.showMessage(
          error.response?.data?.detail || "无法读取运行记录。",
          "error",
        );
      }
    },
    selectRun(run) {
      this.selectedRun = run;
    },
    async loadCaseRuns() {
      const id = Number(this.caseIdDraft);
      if (!Number.isSafeInteger(id) || id < 1) return;
      this.caseLoading = true;
      try {
        this.caseId = String(id);
        this.$router.replace({
          query: { ...this.$route.query, case_id: String(id) },
        });
        this.runs = await api.getCaseSkillRuns(id);
        this.selectedRun =
          this.visibleRuns.find((run) => run.id === this.sourceRunId) ||
          this.visibleRuns[0] ||
          null;
        if (
          this.runs.some((run) => ["PENDING", "RUNNING"].includes(run.status))
        )
          this.startPoll();
        else this.clearPoll();
        this.message = "";
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "无权查看该报告案例，或读取失败。",
          "error",
        );
        this.runs = [];
        this.selectedRun = null;
        this.clearPoll();
      } finally {
        this.caseLoading = false;
      }
    },
    async refreshCaseRuns() {
      if (!this.caseId) return;
      try {
        this.runs = await api.getCaseSkillRuns(Number(this.caseId));
        if (this.selectedRun)
          this.selectedRun =
            this.visibleRuns.find((run) => run.id === this.selectedRun.id) ||
            null;
        else this.selectedRun = this.visibleRuns[0] || null;
        if (
          !this.runs.some((run) => ["PENDING", "RUNNING"].includes(run.status))
        )
          this.clearPoll();
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "无法读取运行记录。",
          "error",
        );
        this.clearPoll();
      }
    },
    startPoll() {
      if (this.pollTimer) return;
      this.pollTimer = window.setInterval(() => {
        if (this.isAdmin) this.loadRuns();
        else this.refreshCaseRuns();
      }, POLL_INTERVAL);
    },
    clearPoll() {
      if (this.pollTimer) window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    },
    formatDate(value) {
      return value
        ? new Date(value).toLocaleString("zh-CN", { hour12: false })
        : "—";
    },
    feedbackTargetLabel(run) {
      const skill = this.catalog.find((item) => item.key === runSkillKey(run));
      const target = {
        REPORT_ANALYSIS_DRAFT: `分析建议 · ${run.target_key || "当前节点"}`,
        NARRATIVE_CANDIDATES: "S5 报告主线候选",
        REPORT_FRAGMENT: `S5 报告段落 · ${run.target_key || "内容片段"}`,
        REPORT_QA: "S6 交付前检查",
        CALENDAR_PRODUCTION: `日历生产 · 请求 ${run.target_key || "当前"}`,
      }[run.target_type] || run.target_key || "节点运行";
      return skill ? `${skill.node} · ${target}` : target;
    },
    showMessage(message, kind = "") {
      this.message = message;
      this.messageKind = kind;
    },
  },
};
