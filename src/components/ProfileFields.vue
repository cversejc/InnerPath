<template>
  <div class="profile-fields">
    <ProfileCoreFields
      :profile="profile"
      :errors="errors"
      :id-prefix="idPrefix"
      :gender-options="genderOptions"
      :calendar-options="calendarOptions"
      :time-options="timeOptions"
      @set-field="setField"
      @set-number-field="setNumberField"
      @select-time-precision="selectTimePrecision"
    />

    <button
      v-if="showOptional && optionalCollapsible"
      type="button"
      class="optional-toggle"
      :aria-expanded="optionalExpanded"
      :aria-controls="`${idPrefix}-optional-section`"
      @click="$emit('update:optionalExpanded', !optionalExpanded)"
    >
      <span>{{ optionalExpanded ? '收起个人画像' : '展开个人画像' }}</span>
      <span class="optional-toggle-meta">{{ optionalExpanded ? '稳定背景，可随时更新' : '还有可选信息' }}</span>
      <span aria-hidden="true">{{ optionalExpanded ? '−' : '+' }}</span>
    </button>

    <ProfileExtendedFields
      v-if="showOptional && (!optionalCollapsible || optionalExpanded)"
      :profile="profile"
      :id-prefix="idPrefix"
      :marital-options="maritalOptions"
      :occupation-options="occupationOptions"
      :education-options="educationOptions"
      :experience-options="experienceOptions"
      :attitude-options="attitudeOptions"
      :depth-options="depthOptions"
      :usage-options="usageOptions"
      @set-field="setField"
      @set-keywords="setKeywords"
      @toggle-list="toggleList"
    />
  </div>
</template>

<script src="./ProfileFields.js"></script>

<style scoped src="./ProfileFields.css"></style>
