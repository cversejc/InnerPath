<template>
  <section class="skill-instructions" aria-label="技能维护内容">
    <p v-if="!intentOnly" class="maintenance-note">
      {{
        editable
          ? "修改目标与方法后保存草稿，评估通过后再发布。发布版本供咨询工作台后续运行使用。"
          : "已发布版本只读。需要调整时，请先从该版本创建草稿。"
      }}
    </p>
    <template v-if="specification">
      <label v-if="editable"
        >{{ intentOnly ? "目标" : "技能目标" }}<textarea
          :value="specification.instructions?.objective || ''"
          rows="3"
          @input="update({ objective: $event.target.value })"
        ></textarea>
      </label>
      <div v-else>
        <h3>{{ intentOnly ? "目标" : "技能目标" }}</h3>
        <p>{{ displayText(specification.instructions?.objective) }}</p>
      </div>
      <label v-if="editable"
        >{{ intentOnly ? "分析方法（每行一项）" : "执行方法（每行一项）" }}<textarea
          :value="(specification.instructions?.methodology || []).join('\n')"
          rows="8"
          @input="
            update({
              methodology: $event.target.value
                .split(/\r?\n/)
                .filter((item) => item.trim()),
            })
          "
        ></textarea>
      </label>
      <div v-else>
        <h3>{{ intentOnly ? "分析方法" : "执行方法" }}</h3>
        <ol>
          <li
            v-for="(item, index) in specification.instructions?.methodology ||
            []"
            :key="index"
          >
            {{ displayText(item) }}
          </li>
        </ol>
      </div>
      <div v-if="!intentOnly" class="skill-policy-summary">
        <strong>示例使用</strong>
        <p>
          {{
            specification.example_policy?.enabled
              ? `每次最多参考 ${specification.example_policy.max_examples || 0} 条匹配的已发布示例`
              : "当前版本未启用示例参考"
          }}
        </p>
        <p>
          示例帮助学习方法与表达；用户事实须来自本次资料。报告由咨询师确认，日历通过整体校准后交付。
        </p>
      </div>
      <details v-if="!intentOnly && specification.instructions?.sop_contract">
        <summary>详细分析范围</summary>
        <ReadableData :value="specification.instructions.sop_contract" />
      </details>
      <details v-if="!intentOnly && specification.knowledge_policy?.snapshot?.length">
        <summary>技能知识参考</summary>
        <ReadableData :value="specification.knowledge_policy.snapshot" />
      </details>
    </template>
    <details v-if="!intentOnly" class="technical-config">
      <summary>高级配置 · 原始结构</summary>
      <p>用于维护输入输出约束、模型参数和技术标识。字段名称须保留系统格式。</p>
      <label for="skill-specification">完整技能配置</label
      ><textarea
        id="skill-specification"
        :value="text"
        class="json-editor"
        :readonly="!editable"
        spellcheck="false"
        @input="$emit('update:text', $event.target.value)"
      ></textarea>
    </details>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="instruction-actions"><slot /></div>
  </section>
</template>
<script>
import { parseSpecification } from "../studio.js";
import { patchInstructions, displayText } from "../presentation.js";
import ReadableData from "./ReadableData.vue";
export default {
  components: { ReadableData },
  props: {
    text: String,
    guidance: { type: Object, default: null },
    editable: Boolean,
    intentOnly: Boolean,
    error: { type: String, default: "" },
  },
  emits: ["update:text", "update:guidance"],
  computed: {
    specification() {
      if (this.intentOnly)
        return {
          instructions: this.guidance || { objective: "", methodology: [] },
        };
      const parsed = parseSpecification(this.text).value;
      return parsed;
    },
  },
  methods: {
    displayText,
    update(patch) {
      if (this.intentOnly) {
        this.$emit("update:guidance", {
          objective: this.guidance?.objective || "",
          methodology: Array.isArray(this.guidance?.methodology)
            ? [...this.guidance.methodology]
            : [],
          ...patch,
        });
        return;
      }
      let sourceText = this.text;
      this.$emit("update:text", patchInstructions(sourceText, patch));
    },
  },
};
</script>
<style scoped>
.skill-instructions {
  display: grid;
  gap: var(--space-4);
}
h3 {
  font-size: var(--text-h4);
  margin: 0;
}
p,
li {
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
label {
  display: grid;
  gap: var(--space-2);
  color: var(--ink-soft);
}
textarea {
  width: 100%;
  min-height: var(--touch-target);
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
  background: var(--paper-soft);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
  line-height: var(--leading-body);
  resize: vertical;
}
.json-editor {
  min-height: 420px;
  font-family: var(--font-mono);
}
summary {
  display: flex;
  align-items: center;
  min-height: var(--touch-target);
  color: var(--cinnabar-deep);
  cursor: pointer;
}
.maintenance-note,
.skill-policy-summary {
  padding: var(--space-3);
  border-left: 3px solid var(--jade);
  background: var(--surface);
}
.maintenance-note {
  line-height: var(--leading-body);
}
.instruction-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
