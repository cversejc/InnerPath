import { createApp } from 'vue'
import 'vant/es/action-sheet/style/index'
import 'vant/es/button/style/index'
import 'vant/es/cell/style/index'
import 'vant/es/cell-group/style/index'
import 'vant/es/field/style/index'
import 'vant/es/tabbar/style/index'
import 'vant/es/tabbar-item/style/index'
import App from './App.vue'
import router from './router'
import './style.css'
import BrandNav from './components/BrandNav.vue'
import BrandFooter from './components/BrandFooter.vue'
import IconMark from './components/IconMark.vue'

const app = createApp(App)

app.component('BrandNav', BrandNav)
app.component('BrandFooter', BrandFooter)
app.component('IconMark', IconMark)

app.use(router).mount('#app')
