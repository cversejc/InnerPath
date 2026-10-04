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
  RUN_STATUS_LABELS,
  sampleInput,
  VERSION_STATUS_LABELS,
} from "./studio.js";

const POLL_INTERVAL = 2500;

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
    return {
      isAdmin: hasRole("admin"),
      versions: [],
      selectedVersion: null,
      selectedSkillKey:
        REPORT_SKILLS.find((item) => item.key === this.$route.query.skill)
          ?.key ||
        REPORT_SKILLS.find((item) => item.step === this.$route.query.step)
          ?.key ||
        REPORT_SKILLS[0].key,
      activeAdminTab: [
        "overview",
        "examples",
        "runs",
        ...(hasRole("admin") ? ["skills", "debug", "evaluation"] : []),
      ].includes(this.$route.query.panel)
        ? this.$route.query.panel
        : "overview",
      specificationText: "",
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
    studioTabs() {
      return [
        { id: "overview", label: "使用说明" },
        ...(this.isAdmin ? [{ id: "skills", label: "技能维护" }] : []),
        { id: "examples", label: "示例库" },
        { id: "runs", label: "运行记录" },
        ...(this.isAdmin
          ? [
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
      return this.editable
        ? parseSpecification(this.specificationText).error
        : "";
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
        const current =
          this.skillVersions.find(
            (item) => item.id === this.selectedVersion?.id,
          ) ||
          this.skillVersions.find((item) => item.status === "PUBLISHED") ||
          this.skillVersions[0];
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
      this.specificationText = JSON.stringify(
        version.specification_json,
        null,
        2,
      );
      this.selectedRun = null;
      this.loadRuns();
    },
    selectSkill(key) {
      this.selectedSkillKey = key;
      this.selectedRun = null;
      this.changeTab("overview");
      if (this.isAdmin) {
        const version =
          this.skillVersions.find((item) => item.status === "PUBLISHED") ||
          this.skillVersions[0];
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
    async createDraft() {
      if (!this.selectedVersion) return;
      this.saving = true;
      try {
        const created = await api.createSkillVersion({
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
      const parsed = parseSpecification(this.specificationText);
      if (parsed.error) {
        this.showMessage(parsed.error, "error");
        if (options.rethrow) throw new Error(parsed.error);
        return;
      }
      this.saving = true;
      try {
        const updated = await api.updateSkillVersion(this.selectedVersion.id, {
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
      const parsed = parseSpecification(this.specificationText);
      if (parsed.error) return;
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
      this.specificationText = JSON.stringify(
        version.specification_json,
        null,
        2,
      );
    },
    async startRun() {
      if (this.inputError || !this.selectedVersion) return;
      this.running = true;
      try {
        const run = await api.runSkill(this.selectedVersion.id, {
          idempotency_key:
            globalThis.crypto?.randomUUID?.() ||
            `studio-${Date.now()}-${Math.random()}`,
          input_data: JSON.parse(this.inputText),
          runtime_instruction: this.runtimeInstruction || null,
        });
        this.selectedRun = run;
        await this.loadRuns();
        this.changeTab("runs");
        this.startPoll();
        this.showMessage(`运行记录 ${run.id} 已加入队列。`);
      } catch (error) {
        this.showMessage(
          error.response?.data?.detail || "运行请求失败。",
          "error",
        );
      } finally {
        this.running = false;
      }
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
        this.selectedRun = this.visibleRuns[0] || null;
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
    showMessage(message, kind = "") {
      this.message = message;
      this.messageKind = kind;
    },
  },
};
