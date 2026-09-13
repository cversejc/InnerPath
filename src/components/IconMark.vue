<template>
  <svg
    class="icon-mark"
    :class="`icon-mark--${name}`"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="path in paths" :key="path" :d="path" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: {
    type: String,
    default: 'spark'
  }
})

const icons = {
  spark: ['M12 3l1.35 5.65L19 10l-5.65 1.35L12 17l-1.35-5.65L5 10l5.65-1.35L12 3Z'],
  document: ['M6 3.75h8.5L18 7.25v13H6z', 'M14.5 3.75v3.5H18', 'M8.5 11h7', 'M8.5 14.5h7', 'M8.5 18H13'],
  reports: ['M4.5 4.5h15v15h-15z', 'M8 16.5v-3.5', 'M12 16.5v-6', 'M16 16.5V8'],
  calendar: ['M5 4.5h14v15H5z', 'M8 3v3', 'M16 3v3', 'M5 9h14', 'M8.5 12h.01', 'M12 12h.01', 'M15.5 12h.01', 'M8.5 15.5h.01', 'M12 15.5h.01'],
  person: ['M12 12a3.25 3.25 0 1 0 0-.01', 'M5.5 20a6.5 6.5 0 0 1 13 0'],
  settings: ['M4 7h16', 'M4 17h16', 'M9 7a2 2 0 1 0 0 .01', 'M15 17a2 2 0 1 0 0 .01'],
  career: ['M5 6.5h14v13H5z', 'M9 6.5v-2h6v2', 'M8.5 12h7'],
  relationship: ['M12 20s-7-4.35-7-9.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 7 3.5C19 15.65 12 20 12 20Z'],
  family: ['M8 11a2.5 2.5 0 1 0 0-.01', 'M16 11a2.5 2.5 0 1 0 0-.01', 'M12 8a2.5 2.5 0 1 0 0-.01', 'M4.5 19a3.5 3.5 0 0 1 7 0', 'M12.5 19a3.5 3.5 0 0 1 7 0'],
  self: ['M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 0 0 0-17Z', 'M12 8v8', 'M8 12h8'],
  growth: ['M12 20V8', 'M12 8 8.5 4.5', 'M12 8l3.5-3.5', 'M7 20h10'],
  stress: ['M6.5 18.5h10a3.5 3.5 0 0 0 .55-6.96A5.5 5.5 0 0 0 6.4 10.8a3.9 3.9 0 0 0 .1 7.7Z', 'M9 15.5h.01', 'M15 15.5h.01'],
  book: ['M4.5 5.5A2.5 2.5 0 0 1 7 3h5v16H7a2.5 2.5 0 0 0-2.5 2.5z', 'M19.5 5.5A2.5 2.5 0 0 0 17 3h-5v16h5a2.5 2.5 0 0 1 2.5 2.5z'],
  education: ['M4 8l8-4 8 4-8 4-8-4Z', 'M7 10.5v5c3 2.2 7 2.2 10 0v-5', 'M20 9v5'],
  group: ['M8 11a3 3 0 1 0 0-.01', 'M16 11a3 3 0 1 0 0-.01', 'M3.5 19a4.5 4.5 0 0 1 9 0', 'M11.5 19a4.5 4.5 0 0 1 9 0'],
  bridge: ['M4 17h16', 'M6 17V9', 'M12 17V6', 'M18 17V9', 'M4 9h16'],
  refresh: ['M20 11a8 8 0 0 0-14.7-4L4 9', 'M4 4v5h5', 'M4 13a8 8 0 0 0 14.7 4L20 15', 'M20 20v-5h-5'],
  link: ['M10 13a4 4 0 0 0 5.66.34l2-2a4 4 0 0 0-5.66-5.66l-1.15 1.15', 'M14 11a4 4 0 0 0-5.66-.34l-2 2A4 4 0 0 0 12 18.32l1.15-1.15'],
  search: ['M10.8 5.2a5.6 5.6 0 1 0 0 11.2a5.6 5.6 0 0 0 0-11.2Z', 'm15 15 4 4'],
  download: ['M12 4v11', 'm7 11 5 5 5-5', 'M5 20h14'],
  close: ['M6 6l12 12', 'M18 6 6 18'],
  logout: ['M14 4h5v16h-5', 'M3 12h11', 'm10 8 4 4-4 4'],
  arrow: ['M5 12h13', 'm13 6 6 6-6 6'],
  'arrow-left': ['M19 12H6', 'm11 6-6 6 6 6'],
  plus: ['M12 5v14', 'M5 12h14'],
  compass: ['M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 0 0 0-17Z', 'm15.5 8.5-2.35 4.65L8.5 15.5l2.35-4.65L15.5 8.5Z']
}

const paths = computed(() => icons[props.name] || icons.spark)
</script>

<style>
.icon-mark {
  display: block;
  width: 1em;
  height: 1em;
  flex: 0 0 auto;
}
</style>
