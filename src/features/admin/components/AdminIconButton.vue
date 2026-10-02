<script setup>
import { Button as VanButton } from 'vant'
import IconMark from '../../../components/IconMark.vue'

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true }
})

const emit = defineEmits(['click'])
</script>

<template>
  <VanButton
    class="admin-icon-button"
    plain
    native-type="button"
    :aria-label="label"
    :title="label"
    @click="emit('click', $event)"
  >
    <template #icon><IconMark :name="icon" /></template>
  </VanButton>
</template>

<style scoped>
.admin-icon-button {
  width: 44px;
  min-width: 44px;
  height: 44px;
  border-radius: 10px;
  padding: 0;
}
</style>
