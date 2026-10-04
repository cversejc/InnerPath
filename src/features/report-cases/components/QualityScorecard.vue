<template>
  <section
    v-if="scorecard"
    class="quality-scorecard"
    aria-label="报告七维质量评分"
  >
    <h3>质量评分 · {{ scorecard.total }} / 100</h3>
    <p>
      交付门槛：总分 80，事实忠实度 16，不确定性与安全
      8。评分通过后仍需人工复核。
    </p>
    <div>
      <details v-for="(dimension, key) in scorecard.dimensions" :key="key">
        <summary>
          {{ dimension.label }} · {{ dimension.score }} /
          {{ dimension.max_score }}
        </summary>
        <p>{{ dimension.reason }}</p>
      </details>
    </div>
  </section>
</template>
<script>
export default { props: { scorecard: Object } };
</script>
<style scoped>
.quality-scorecard {
  padding: var(--space-4);
  margin: var(--space-4) 0;
  border: 1px solid var(--line);
  border-radius: var(--button-radius);
  background: var(--paper-soft);
}
h3 {
  margin: 0;
  font-size: var(--text-h4);
}
p {
  font-size: var(--text-body-sm);
  line-height: var(--leading-body);
}
.quality-scorecard > div {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
  gap: var(--space-3);
}
summary {
  cursor: pointer;
  min-height: var(--touch-target);
  padding: var(--space-2);
}
details p {
  padding: var(--space-2);
}
</style>
