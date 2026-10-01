import authModeMethods from './methods/mode.js'
import authSessionMethods from './methods/session.js'
import {
  authSubmitLabel,
  authSubtitle,
  authTitle,
  resolveAuthMode
} from './presentation.js'

export default {
  name: 'Auth',
  data() {
    return {
      mode: 'login',
      form: {
        name: '',
        phone: '',
        password: '',
        token: ''
      },
      submitting: false,
      errorMessage: '',
      successMessage: ''
    }
  },
  computed: {
    title() {
      return authTitle(this.mode)
    },
    subtitle() {
      return authSubtitle(this.mode)
    },
    submitLabel() {
      return authSubmitLabel(this.mode)
    }
  },
  mounted() {
    this.mode = resolveAuthMode(this.$route.query.mode, this.$route.path)
    this.form.token = this.$route.query.token || ''
  },
  methods: {
    ...authModeMethods,
    ...authSessionMethods
  }
}
