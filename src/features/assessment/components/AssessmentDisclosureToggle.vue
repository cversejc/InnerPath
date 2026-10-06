<script setup>
import { Button as VanButton } from 'vant'

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, required: true },
  expanded: { type: Boolean, default: false },
  actionLabel: { type: String, default: '' },
  controls: { type: String, default: '' }
})

const emit = defineEmits(['toggle'])
</script>

<template>
  <VanButton
    native-type="button"
    type="default"
    plain
    class="fold-toggle"
    :aria-expanded="props.expanded"
    :aria-controls="props.controls || undefined"
    @click="emit('toggle')"
  >
    <span class="fold-toggle-copy">
      <strong>{{ props.title }}</strong>
      <small>{{ props.description }}</small>
    </span>
    <span v-if="props.actionLabel" class="fold-toggle-action">{{ props.actionLabel }}</span>
    <span aria-hidden="true">{{ props.expanded ? '−' : '+' }}</span>
  </VanButton>
</template>
