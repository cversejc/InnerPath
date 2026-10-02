import { Button as VanButton } from 'vant'
import BirthDateField from '../../components/profile-fields/BirthDateField.vue'
import {
  addCalendarDays,
  CALENDAR_TIME_OPTIONS,
  createCalendarRequestForm
} from './calendar-form.js'
import requestFormMethods from './methods/request-form.js'

export default {
  name: 'ServiceRequestForm',
  components: { VanButton, BirthDateField },
  data() {
    return {
      ready: false,
      requestId: null,
      idempotencyKey: null,
      submitting: false,
      formMessage: '',
      errors: {},
      timeOptions: CALENDAR_TIME_OPTIONS,
      form: createCalendarRequestForm()
    }
  },
  computed: {
    editing() {
      return Boolean(this.requestId)
    },
    dateRangeLabel() {
      return this.form.start_date
        ? this.form.start_date + ' 至 ' + addCalendarDays(this.form.start_date, 29)
        : '起始日期待定'
    }
  },
  async mounted() {
    if (this.$route.query.type === 'report') {
      const target = this.$route.query.requestId
        ? '/pages/assessment/assessment?requestId=' + this.$route.query.requestId
        : '/pages/assessment/assessment'
      await this.$router.replace(target)
      return
    }
    await this.loadRequestForm()
  },
  methods: {
    ...requestFormMethods
  }
}
