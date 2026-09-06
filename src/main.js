import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import BrandNav from './components/BrandNav.vue'
import BrandFooter from './components/BrandFooter.vue'

const app = createApp(App)

app.component('BrandNav', BrandNav)
app.component('BrandFooter', BrandFooter)

app.use(router).mount('#app')
