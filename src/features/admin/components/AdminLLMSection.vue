<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { showConfirmDialog, Button as VanButton } from 'vant'
import {
  createAdminLLMConfiguration,
  deleteAdminLLMConfiguration,
  getAdminLLMConfigurations,
  setDefaultAdminLLMConfiguration,
  testAdminLLMConfiguration,
  updateAdminLLMConfiguration
} from '../api.js'

const PROVIDERS = [
  { id: 'deepseek', label: 'DeepSeek' },
  { id: 'openai_compatible', label: 'OpenAI 兼容接口' }
]

const configurations = ref([])
const environmentFallback = ref(null)
const selectedId = ref(null)
const isNew = ref(false)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const changingDefault = ref(false)
const deleting = ref(false)
const message = ref('')
const messageTone = ref('info')
const apiKeySource = ref('missing')

const ERROR_MESSAGES = {
  llm_api_key_required: '请填写 API 密钥后再保存或设为默认。',
  llm_configuration_name_taken: '配置名称已被使用，请换一个名称。',
  llm_configuration_not_found: '配置不存在，请刷新后重试。',
  llm_config_encryption_key_invalid: '无法解密已保存的密钥，请重新填写 API 密钥。',
  base_url_must_be_http_url: 'API 地址必须以 http:// 或 https:// 开头。',
  base_url_must_not_contain_credentials_or_query: '请将凭据填写在 API 密钥栏，API 地址不要包含账号、密码或查询参数。'
}

function createEmptyDraft() {
  return {
    name: '',
    provider: 'deepseek',
    base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-v4-flash',
    api_key: '',
    temperature: 0.7,
    max_tokens: 8000,
    timeout_seconds: 120,
    thinking_enabled: false,
    is_default: false
  }
}

const draft = reactive(createEmptyDraft())
const selected = computed(() => configurations.value.find(item => item.id === selectedId.value) || null)
const providerLabel = computed(() => PROVIDERS.find(item => item.id === draft.provider)?.label || draft.provider)
const keyStatus = computed(() => {
  if (draft.api_key) return '新密钥将在保存时加密存储。'
  if (apiKeySource.value === 'saved') return '已保存密钥；留空会继续使用当前密钥。'
  if (apiKeySource.value === 'environment') return '使用服务端环境变量中的 DeepSeek 密钥。'
  return '尚未配置密钥。'
})

function showMessage(text, tone = 'info') {
  message.value = text
  messageTone.value = tone
}

function errorMessage(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return ERROR_MESSAGES[detail] || detail
  if (Array.isArray(detail)) return '配置内容不符合要求，请检查必填项和数值范围。'
  return error?.message || '请求失败，请稍后重试。'
}

function resetDraft(values = createEmptyDraft()) {
  Object.assign(draft, createEmptyDraft(), values, { api_key: '' })
}

function selectConfiguration(configuration) {
  selectedId.value = configuration.id
  isNew.value = false
  apiKeySource.value = configuration.api_key_source
  resetDraft(configuration)
  message.value = ''
}

function startNewConfiguration() {
  const fallback = environmentFallback.value
  selectedId.value = null
  isNew.value = true
  apiKeySource.value = 'missing'
  resetDraft({
    ...createEmptyDraft(),
    name: `模型配置 ${configurations.value.length + 1}`,
    provider: fallback?.provider || 'deepseek',
    base_url: fallback?.base_url || 'https://api.deepseek.com/v1',
    model: fallback?.model || 'deepseek-v4-flash',
    is_default: configurations.value.length === 0 && Boolean(fallback?.configured)
  })
  showMessage('填写服务地址与模型；保存密钥后可设为默认。')
}

async function loadConfigurations(preferredId = selectedId.value) {
  loading.value = true
  message.value = ''
  try {
    const data = await getAdminLLMConfigurations()
    configurations.value = data.items || []
    environmentFallback.value = data.environment_fallback || null
    const next = configurations.value.find(item => item.id === preferredId)
      || configurations.value.find(item => item.is_default)
      || configurations.value[0]
    if (next) selectConfiguration(next)
    else if (!isNew.value) startNewConfiguration()
  } catch (error) {
    showMessage(errorMessage(error), 'error')
  } finally {
    loading.value = false
  }
}

function payload() {
  return {
    name: draft.name,
    provider: draft.provider,
    base_url: draft.base_url,
    model: draft.model,
    api_key: draft.api_key || null,
    temperature: Number(draft.temperature),
    max_tokens: Number(draft.max_tokens),
    timeout_seconds: Number(draft.timeout_seconds),
    thinking_enabled: Boolean(draft.thinking_enabled),
    is_default: Boolean(draft.is_default)
  }
}

async function saveConfiguration() {
  saving.value = true
  message.value = ''
  try {
    const saved = isNew.value
      ? await createAdminLLMConfiguration(payload())
      : await updateAdminLLMConfiguration(selectedId.value, payload())
    apiKeySource.value = saved.api_key_source
    selectedId.value = saved.id
    isNew.value = false
    await loadConfigurations(saved.id)
    showMessage('模型配置已保存。', 'success')
  } catch (error) {
    showMessage(errorMessage(error), 'error')
  } finally {
    saving.value = false
  }
}

async function testConfiguration() {
  testing.value = true
  message.value = ''
  try {
    const result = await testAdminLLMConfiguration({
      ...payload(),
      configuration_id: selectedId.value
    })
    showMessage(`连接成功 · ${result.model} · ${result.latency_ms} ms`, 'success')
  } catch (error) {
    showMessage(errorMessage(error), 'error')
  } finally {
    testing.value = false
  }
}

async function makeDefault() {
  if (!selectedId.value) return
  changingDefault.value = true
  try {
    await setDefaultAdminLLMConfiguration(selectedId.value)
    await loadConfigurations(selectedId.value)
    showMessage('默认模型已切换。', 'success')
  } catch (error) {
    showMessage(errorMessage(error), 'error')
  } finally {
    changingDefault.value = false
  }
}

async function removeConfiguration() {
  if (!selected.value || selected.value.is_default) return
  try {
    await showConfirmDialog({
      title: '删除模型配置',
      message: `确定删除“${selected.value.name}”吗？`
    })
  } catch {
    return
  }

  deleting.value = true
  try {
    const removedId = selectedId.value
    await deleteAdminLLMConfiguration(removedId)
    selectedId.value = null
    await loadConfigurations()
    showMessage('模型配置已删除。', 'success')
  } catch (error) {
    showMessage(errorMessage(error), 'error')
  } finally {
    deleting.value = false
  }
}

onMounted(() => loadConfigurations())
</script>

<template>
  <section class="content-view llm-settings">
    <div class="view-heading llm-heading">
      <div>
        <p class="eyebrow">PLATFORM / MODEL SERVICES</p>
        <h2>模型配置</h2>
        <p>维护供报告、日历与技能调用的对话模型服务。</p>
      </div>
      <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="loading" @click="startNewConfiguration">
        新增配置
      </VanButton>
    </div>

    <p v-if="message" :class="['llm-message', `llm-message-${messageTone}`]" role="status" aria-live="polite">
      {{ message }}
    </p>

    <div class="llm-layout">
      <aside class="panel-surface llm-list" aria-label="模型服务配置列表">
        <div class="panel-heading">
          <div><p class="eyebrow">PROVIDERS</p><h3>服务配置</h3></div>
          <span>{{ configurations.length }}</span>
        </div>
        <div v-if="loading" class="llm-list-state" role="status">正在读取配置…</div>
        <div v-else-if="configurations.length" class="llm-config-list">
          <button
            v-for="configuration in configurations"
            :key="configuration.id"
            type="button"
            :class="['llm-config-item', { selected: selectedId === configuration.id }]"
            :aria-pressed="selectedId === configuration.id"
            @click="selectConfiguration(configuration)"
          >
            <span class="llm-config-item__top">
              <strong>{{ configuration.name }}</strong>
              <span v-if="configuration.is_default" class="llm-default-label">默认</span>
            </span>
            <span class="llm-config-item__meta">{{ PROVIDERS.find(item => item.id === configuration.provider)?.label }} · {{ configuration.model }}</span>
            <span class="llm-config-item__status">{{ configuration.api_key_configured ? '密钥已配置' : '缺少密钥' }}</span>
          </button>
        </div>
        <div v-else class="llm-list-state">
          <p>尚无后台配置。</p>
          <small v-if="environmentFallback?.configured">
            当前生成请求继续使用服务器环境中的 {{ environmentFallback.provider }} / {{ environmentFallback.model }}。
          </small>
          <small v-else>请新增一个模型配置并设置 API 密钥。</small>
        </div>
      </aside>

      <form v-if="!loading" class="panel-surface llm-editor" @submit.prevent="saveConfiguration">
        <div class="panel-heading llm-editor-heading">
          <div>
            <p class="eyebrow">{{ isNew ? 'NEW PROVIDER' : 'PROVIDER SETTINGS' }}</p>
            <h3>{{ isNew ? '新增模型服务' : (selected?.name || '模型服务') }}</h3>
          </div>
          <span v-if="selected?.is_default" class="llm-default-label">当前默认</span>
        </div>

        <div class="llm-form-grid">
          <label class="llm-field">
            <span>配置名称</span>
            <input v-model.trim="draft.name" required maxlength="80" autocomplete="off" placeholder="例如：主模型服务">
          </label>
          <label class="llm-field">
            <span>服务商协议</span>
            <select v-model="draft.provider">
              <option v-for="provider in PROVIDERS" :key="provider.id" :value="provider.id">{{ provider.label }}</option>
            </select>
          </label>
          <label class="llm-field llm-field-wide">
            <span>API 地址</span>
            <input v-model.trim="draft.base_url" required type="url" maxlength="500" inputmode="url" placeholder="https://api.example.com/v1">
            <small>可填 API 根地址，也可填完整的 /chat/completions 地址。</small>
          </label>
          <label class="llm-field llm-field-wide">
            <span>模型名称</span>
            <input v-model.trim="draft.model" required maxlength="50" autocomplete="off" placeholder="例如：deepseek-v4-flash">
          </label>
          <label class="llm-field llm-field-wide">
            <span>API 密钥</span>
            <input v-model="draft.api_key" type="password" autocomplete="new-password" spellcheck="false" :placeholder="isNew ? '输入服务商 API 密钥' : '留空以保留已保存的密钥'">
            <small>{{ keyStatus }}</small>
          </label>
          <label class="llm-field">
            <span>Temperature</span>
            <input v-model.number="draft.temperature" type="number" min="0" max="2" step="0.1" inputmode="decimal">
          </label>
          <label class="llm-field">
            <span>最大输出 Token</span>
            <input v-model.number="draft.max_tokens" type="number" min="1" max="32768" step="1" inputmode="numeric">
          </label>
          <label class="llm-field">
            <span>超时秒数</span>
            <input v-model.number="draft.timeout_seconds" type="number" min="1" max="240" step="1" inputmode="numeric">
          </label>
          <label v-if="draft.provider === 'deepseek'" class="llm-toggle">
            <input v-model="draft.thinking_enabled" type="checkbox">
            <span><strong>启用思考模式</strong><small>仅用于 DeepSeek 服务。</small></span>
          </label>
        </div>

        <div class="llm-editor-footer">
          <div class="llm-editor-actions">
            <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="saving || testing" :loading="testing" loading-text="测试中…" @click="testConfiguration">
              测试连接
            </VanButton>
            <VanButton v-if="selected && !selected.is_default" class="secondary-button compact-button" type="default" plain native-type="button" :disabled="saving || testing || changingDefault" :loading="changingDefault" loading-text="切换中…" @click="makeDefault">
              设为默认
            </VanButton>
            <VanButton v-if="selected && !selected.is_default" class="llm-delete-button" type="default" plain native-type="button" :disabled="saving || testing || deleting" :loading="deleting" loading-text="删除中…" @click="removeConfiguration">
              删除
            </VanButton>
          </div>
          <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="saving || testing" :loading="saving" loading-text="保存中…">
            保存配置
          </VanButton>
        </div>
        <p class="llm-security-note">密钥只在服务器端加密保存，读取配置时不会返回密钥明文。</p>
        <span class="sr-only" aria-live="polite">{{ providerLabel }}</span>
      </form>
    </div>
  </section>
</template>
