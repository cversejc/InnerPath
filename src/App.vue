<template>
  <div id="app" ref="appContent">
    <router-view />
  </div>
</template>

<script>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const ignoredTextSelector = 'script, style, textarea, pre, code, [contenteditable]:not([contenteditable="false"])'
const textAttributes = ['alt', 'aria-description', 'aria-label', 'placeholder', 'title']

function removeChineseFullStops(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    if (node.parentElement?.closest(ignoredTextSelector)) return
    const cleaned = node.nodeValue.replaceAll('。', '')
    if (cleaned !== node.nodeValue) node.nodeValue = cleaned
    return
  }

  if (node.nodeType === Node.ELEMENT_NODE) {
    for (const attribute of textAttributes) {
      const value = node.getAttribute(attribute)
      if (value?.includes('。')) node.setAttribute(attribute, value.replaceAll('。', ''))
    }
    if (node.matches(ignoredTextSelector)) return
  }

  if (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return
  for (const child of node.childNodes) removeChineseFullStops(child)
}

export default {
  name: 'App',
  setup() {
    const appContent = ref(null)
    let copyObserver

    onMounted(() => {
      const root = appContent.value
      if (!root) return

      // Keep dynamic report and calendar copy aligned with the site's punctuation rule.
      removeChineseFullStops(root)
      copyObserver = new MutationObserver(records => {
        for (const record of records) {
          if (record.type === 'attributes') {
            removeChineseFullStops(record.target)
          } else {
            for (const node of record.addedNodes || []) removeChineseFullStops(node)
            if (record.type === 'characterData') removeChineseFullStops(record.target)
          }
        }
      })
      copyObserver.observe(root, {
        attributes: true,
        attributeFilter: textAttributes,
        characterData: true,
        childList: true,
        subtree: true
      })
    })

    onBeforeUnmount(() => copyObserver?.disconnect())

    return { appContent }
  }
}
</script>

<style>
#app {
  width: 100%;
  min-height: 100dvh;
}
</style>
