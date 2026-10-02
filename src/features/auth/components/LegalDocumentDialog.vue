<template>
  <Teleport to="body">
    <div class="legal-dialog-layer" @click.self="close">
      <section
        ref="dialog"
        class="legal-dialog"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        :aria-labelledby="titleId"
        @keydown="handleKeydown"
      >
        <header class="legal-dialog-header">
          <div>
            <p class="legal-dialog-kicker">辰鉴 · 文档草案</p>
            <h2 :id="titleId">{{ document.title }}</h2>
          </div>
          <VanButton
            class="legal-close-button"
            type="default"
            plain
            icon="cross"
            native-type="button"
            aria-label="关闭文档"
            @click="close"
          />
        </header>

        <div class="legal-document-scroll" tabindex="0">
          <p class="legal-template-notice">
            当前为模板草案。运营主体、服务范围、数据处理安排及联系渠道等内容待确认，正式上线前请完成核实、替换和审阅。
          </p>
          <p class="legal-document-date">发布日期 / 更新日期：[待确认]</p>

          <section v-for="section in document.sections" :key="section.title" class="legal-document-section">
            <h3>{{ section.title }}</h3>
            <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
          </section>
        </div>

        <footer class="legal-dialog-footer">
          <VanButton class="legal-done-button" type="primary" native-type="button" @click="close">
            关闭并返回
          </VanButton>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script>
import { Button as VanButton } from 'vant'
import { legalDocuments } from '../legalDocuments.js'

export default {
  name: 'LegalDocumentDialog',
  components: { VanButton },
  props: {
    type: {
      type: String,
      required: true,
      validator: value => ['terms', 'privacy'].includes(value)
    }
  },
  emits: ['close'],
  computed: {
    document() {
      return legalDocuments[this.type]
    },
    titleId() {
      return `legal-document-${this.type}-title`
    }
  },
  mounted() {
    document.body.classList.add('dialog-open')
    this.$nextTick(() => {
      this.$refs.dialog?.querySelector('.legal-close-button')?.focus({ preventScroll: true })
    })
  },
  beforeUnmount() {
    document.body.classList.remove('dialog-open')
  },
  methods: {
    close() {
      this.$emit('close')
    },
    handleKeydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        this.close()
        return
      }
      if (event.key !== 'Tab') return

      const focusable = [...this.$refs.dialog.querySelectorAll('button:not([disabled]), [tabindex="0"]')]
        .filter(element => element.getClientRects().length > 0)
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!first || !last) {
        event.preventDefault()
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }
}
</script>

<style scoped src="./LegalDocumentDialog.css"></style>
