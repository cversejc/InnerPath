<template>
  <VanDialog
    :show="show"
    id="report-node-dialog"
    class="node-dialog"
    :title="title"
    :show-confirm-button="false"
    :close-on-click-overlay="true"
    :aria-label="title"
    role="dialog"
    aria-modal="true"
    @update:show="$emit('update:show', $event)"
    @opened="focusFirst"
    @closed="$nextTick(restoreFocus)"
  >
    <div class="node-dialog-body"><slot /></div>
    <template #footer
      ><div class="node-dialog-footer">
        <VanButton
          plain
          native-type="button"
          @click="$emit('update:show', false)"
          >关闭</VanButton
        >
      </div></template
    >
  </VanDialog>
</template>
<script>
import { Dialog as VanDialog, Button as VanButton } from "vant";
export default {
  components: { VanDialog, VanButton },
  props: { show: Boolean, title: String, returnFocusElement: Object },
  emits: ["update:show"],
  data: () => ({ returnFocus: null }),
  watch: {
    show(value) {
      if (value) {
        this.returnFocus = this.returnFocusElement || document.activeElement;
        document.addEventListener("keydown", this.onKeydown, true);
        this.$nextTick(this.focusFirst);
      } else {
        document.removeEventListener("keydown", this.onKeydown, true);
      }
    },
  },
  beforeUnmount() {
    document.removeEventListener("keydown", this.onKeydown, true);
  },
  methods: {
    focusable() {
      return [
        ...(document
          .getElementById("report-node-dialog")
          ?.querySelectorAll(
            'button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]',
          ) || []),
      ].filter((item) => item.getClientRects().length);
    },
    focusFirst() {
      this.focusable()[0]?.focus();
    },
    restoreFocus() {
      if (this.returnFocus?.isConnected) this.returnFocus.focus();
    },
    onKeydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        this.$emit("update:show", false);
        return;
      }
      if (event.key !== "Tab") return;
      const items = this.focusable(),
        first = items[0],
        last = items.at(-1);
      if (!items.includes(event.target)) {
        event.preventDefault();
        (event.shiftKey ? last : first)?.focus();
      } else if (event.shiftKey && event.target === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && event.target === last) {
        event.preventDefault();
        first?.focus();
      }
    },
  },
};
</script>
<style>
.node-dialog.van-dialog {
  width: min(780px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  color: var(--ink);
  background: var(--paper-soft);
}
.node-dialog-body {
  max-height: min(65dvh, 650px);
  overflow-y: auto;
  padding: var(--space-5);
}
.node-dialog-body p,
.node-dialog-body li {
  line-height: var(--leading-body);
  overflow-wrap: anywhere;
}
.node-dialog-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--line);
}
</style>
