import { createProfileFieldOptions } from './profile-fields-options.js'
import ProfileCoreFields from './profile-fields/CoreFields.vue'
import ProfileExtendedFields from './profile-fields/ExtendedFields.vue'
import { Button as VanButton } from 'vant'

export default {
  name: 'ProfileFields',
  components: { ProfileCoreFields, ProfileExtendedFields, VanButton },
  props: {
    modelValue: {
      type: Object,
      required: true
    },
    showOptional: {
      type: Boolean,
      default: false
    },
    optionalCollapsible: {
      type: Boolean,
      default: false
    },
    optionalExpanded: {
      type: Boolean,
      default: true
    },
    errors: {
      type: Object,
      default: () => ({})
    },
    idPrefix: {
      type: String,
      default: 'profile'
    }
  },
  emits: ['update:modelValue', 'update:optionalExpanded'],
  data() {
    return createProfileFieldOptions()
  },
  computed: {
    profile() {
      return this.modelValue || {}
    }
  },
  methods: {
    emitProfile(nextProfile) {
      this.$emit('update:modelValue', nextProfile)
    },
    setField(field, value) {
      this.emitProfile({ ...this.profile, [field]: value })
    },
    setNumberField(field, value, maxLength) {
      const digits = String(value || '').replace(/\D/g, '').slice(0, maxLength)
      this.setField(field, digits === '' ? null : Number(digits))
    },
    setBirthDate({ year, month, day }) {
      this.emitProfile({
        ...this.profile,
        birth_year: year,
        birth_month: month,
        birth_day: day
      })
    },
    selectTimePrecision(value) {
      const nextProfile = { ...this.profile, birth_time_precision: value }
      if (value === 'unknown') {
        nextProfile.birth_hour = null
        nextProfile.birth_minute = null
      }
      this.emitProfile(nextProfile)
    },
    setKeywords(value) {
      const keywords = String(value || '')
        .split(/[、,，\s]+/)
        .map(item => item.trim())
        .filter(Boolean)
        .slice(0, 5)
      this.setField('personality_keywords', keywords)
    },
    toggleList(field, value, maxItems) {
      const current = Array.isArray(this.profile[field]) ? [...this.profile[field]] : []
      const index = current.indexOf(value)
      if (index >= 0) current.splice(index, 1)
      else if (current.length < maxItems) current.push(value)
      this.setField(field, current)
    }
  }
}
