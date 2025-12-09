<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEnvironmentStore } from '../../stores/environment'
import { useAuthStore } from '../../stores/auth'
import { assetService, configObjectService } from '../../api/services'
import CodeEditor from '../../components/CodeEditor.vue'

const route = useRoute()
const router = useRouter()
const environmentStore = useEnvironmentStore()
const authStore = useAuthStore()

const asset = ref(null)
const configObjects = ref([])
const isLoading = ref(true)
const error = ref('')
const activeTab = ref(0)

// Modals
const showAddObjectModal = ref(false)
const showEditValuesModal = ref(false)
const showEditDescriptionModal = ref(false)
const showPromoteModal = ref(false)
const showHistoryModal = ref(false)
const editingObject = ref(null)
const viewingHistoryObject = ref(null)
const historyVersions = ref([])

// Forms
const newObjectForm = ref({
  name: '',
  object_type: 'kv',
  description: ''
})

const editValuesForm = ref({
  environment: '',
  values: []
})

const editDescriptionForm = ref({
  description: ''
})

const promoteForm = ref({
  from_environment: 'local',
  to_environment: 'stage'
})

const currentEnvironment = computed(() => environmentStore.currentEnvironment)

// Generate curl command for a config object
function generateCurlCommand(configObject) {
  const tenantSlug = authStore.user?.tenant?.slug || 'your-org-slug'
  const assetSlug = asset.value?.slug || 'asset-slug'
  const objectKey = configObject.key || configObject.name.toLowerCase().replace(/\s+/g, '-')
  const env = currentEnvironment.value
  
  return `curl https://api.configmat.com/public/${tenantSlug}/${assetSlug}/${env}/${objectKey} \\
  -H "X-API-Key: your_api_key_here"`
}

// Generate sample response for a config object
function generateSampleResponse(configObject) {
  const values = getObjectValues(configObject)
  
  if (configObject.object_type === 'kv') {
    // Convert KV pairs to object
    const kvObject = {}
    values.forEach(v => {
      if (v.value_type === 'json') {
        kvObject[v.key] = v.value_json
      } else if (v.value_type === 'boolean') {
        kvObject[v.key] = v.value_string === 'true'
      } else if (v.value_type === 'number') {
        kvObject[v.key] = Number(v.value_string)
      } else {
        kvObject[v.key] = v.value_string
      }
    })
    return JSON.stringify(kvObject, null, 2)
  } else if (configObject.object_type === 'json') {
    return JSON.stringify(values[0]?.value_json || {}, null, 2)
  } else {
    // Text type
    return values[0]?.value_string || ''
  }
}

// Get values for current environment
function getObjectValues(configObject) {
  if (!configObject.values) return []
  return configObject.values.filter(v => v.environment === currentEnvironment.value)
}

// Check if object has values for current environment
function hasValues(configObject) {
  return getObjectValues(configObject).length > 0
}

// Check if all environments have the same values
function checkEnvironmentSync(configObject) {
  if (!configObject.values || configObject.values.length === 0) {
    return { synced: true, missingEnvs: [], message: 'No values set' }
  }

  const environments = ['local', 'stage', 'prod']
  const envValues = {}
  const missingEnvs = []

  // Group values by environment
  environments.forEach(env => {
    const values = configObject.values.filter(v => v.environment === env)
    if (values.length === 0) {
      missingEnvs.push(env)
    } else {
      envValues[env] = values
    }
  })

  // If any environment is missing values, not synced
  if (missingEnvs.length > 0) {
    return {
      synced: false,
      missingEnvs,
      message: `Missing in: ${missingEnvs.join(', ')}`
    }
  }

  // Compare values across environments
  const localValues = envValues['local']
  const stageValues = envValues['stage']
  const prodValues = envValues['prod']

  // For KV type, compare KEYS ONLY (Structure)
  if (configObject.object_type === 'kv') {
    const localKeys = new Set(localValues.map(v => v.key))
    const stageKeys = new Set(stageValues.map(v => v.key))
    const prodKeys = new Set(prodValues.map(v => v.key))

    const allSame = 
      localKeys.size === stageKeys.size && 
      localKeys.size === prodKeys.size &&
      [...localKeys].every(k => stageKeys.has(k) && prodKeys.has(k))

    return {
      synced: allSame,
      missingEnvs: [],
      message: allSame ? 'Structure synced' : 'Structure differs (missing keys)'
    }
  } else {
    // For JSON, YAML, Text types, compare single value
    const localVal = JSON.stringify(localValues[0]?.value_json || localValues[0]?.value_string)
    const stageVal = JSON.stringify(stageValues[0]?.value_json || stageValues[0]?.value_string)
    const prodVal = JSON.stringify(prodValues[0]?.value_json || prodValues[0]?.value_string)

    const allSame = localVal === stageVal && stageVal === prodVal

    return {
      synced: allSame,
      missingEnvs: [],
      message: allSame ? 'Synced' : 'Values differ'
    }
  }
}

async function loadAsset() {
  isLoading.value = true
  error.value = ''
  
  try {
    const slug = route.params.slug
    asset.value = await assetService.getAsset(slug)
    await loadConfigObjects()
  } catch (err) {
    console.error('Failed to load asset:', err)
    error.value = 'Failed to load asset. Please try again.'
  } finally {
    isLoading.value = false
  }
}

async function loadConfigObjects() {
  if (!asset.value) return
  
  try {
    const response = await configObjectService.getObjects(asset.value.id)
    configObjects.value = response.results || response
  } catch (err) {
    console.error('Failed to load config objects:', err)
  }
}

async function handleAddObject() {
  try {
    const data = {
      ...newObjectForm.value,
      asset: asset.value.id
    }
    
    await configObjectService.createObject(data)
    await loadConfigObjects()
    
    // Reset form and close modal
    newObjectForm.value = { name: '', object_type: 'kv', description: '' }
    showAddObjectModal.value = false
  } catch (err) {
    console.error('Failed to create object:', err)
    alert('Failed to create config object. Please try again.')
  }
}

function openEditValues(configObject) {
  editingObject.value = configObject
  
  // Load existing values for current environment
  const existingValues = getObjectValues(configObject)
  
  if (configObject.object_type === 'kv') {
    editValuesForm.value = {
      environment: currentEnvironment.value,
      values: existingValues.length > 0 
        ? existingValues.map(v => ({
            key: v.key,
            value_type: v.value_type,
            value_string: v.value_string,
            value_json: v.value_json,
            value_reference: v.value_reference
          }))
        : [{ key: '', value_type: 'string', value_string: '', value_json: null, value_reference: null }]
    }
  } else if (configObject.object_type === 'json') {
    const jsonValue = existingValues[0]?.value_json || {}
    editValuesForm.value = {
      environment: currentEnvironment.value,
      values: [{ 
        key: configObject.name, 
        value_type: 'json', 
        value_json: JSON.stringify(jsonValue, null, 2),
        value_string: null,
        value_reference: null
      }]
    }
  } else {
    // text type
    editValuesForm.value = {
      environment: currentEnvironment.value,
      values: [{ 
        key: configObject.name, 
        value_type: 'string', 
        value_string: existingValues[0]?.value_string || '',
        value_json: null,
        value_reference: null
      }]
    }
  }
  
  showEditValuesModal.value = true
}

async function handleSaveValues() {
  try {
    await configObjectService.updateObjectValues(
      editingObject.value.id,
      editValuesForm.value.environment,
      editValuesForm.value.values
    )
    
    await loadConfigObjects()
    showEditValuesModal.value = false
    editingObject.value = null
  } catch (err) {
    console.error('Failed to save values:', err)
    alert('Failed to save values. Please try again.')
  }
}

function addKVRow() {
  editValuesForm.value.values.push({
    key: '',
    value_type: 'string',
    value_string: '',
    value_json: null,
    value_reference: null
  })
}

function removeKVRow(index) {
  editValuesForm.value.values.splice(index, 1)
}

async function handleDeleteObject(configObject) {
  if (!confirm(`Delete "${configObject.name}"? This will remove it from ALL environments.`)) {
    return
  }
  
  try {
    await configObjectService.deleteObject(configObject.id)
    await loadConfigObjects()
  } catch (err) {
    console.error('Failed to delete object:', err)
    alert('Failed to delete object. Please try again.')
  }
}

function openEditDescription(configObject) {
  editingObject.value = configObject
  editDescriptionForm.value.description = configObject.description || ''
  showEditDescriptionModal.value = true
}

async function handleSaveDescription() {
  try {
    await configObjectService.updateObject(editingObject.value.id, {
      description: editDescriptionForm.value.description
    })
    
    // Update local object
    editingObject.value.description = editDescriptionForm.value.description
    
    // Close modal
    showEditDescriptionModal.value = false
    editingObject.value = null
  } catch (err) {
    console.error('Failed to update description:', err)
    alert('Failed to update description. Please try again.')
  }
}

async function handlePromote() {
  try {
    await assetService.promoteAsset(
      asset.value.slug,
      promoteForm.value.from_environment,
      promoteForm.value.to_environment
    )
    
    showPromoteModal.value = false
    alert('Promotion started successfully! Changes will appear shortly.')
    
    // Reload after a delay
    setTimeout(() => loadConfigObjects(), 2000)
  } catch (err) {
    console.error('Failed to promote:', err)
    alert('Failed to promote configuration. Please try again.')
  }
}

function editAsset() {
  router.push(`/assets/${asset.value.slug}/edit`)
}

async function deleteAsset() {
  if (!confirm(`Delete "${asset.value.name}"? This action cannot be undone.`)) {
    return
  }
  
  try {
    await assetService.deleteAsset(asset.value.slug)
    router.push('/assets')
  } catch (err) {
    console.error('Failed to delete asset:', err)
    alert('Failed to delete asset. Please try again.')
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString()
}

async function openHistory(configObject) {
  viewingHistoryObject.value = configObject
  showHistoryModal.value = true
  historyVersions.value = []
  
  try {
    const response = await configObjectService.getVersions(configObject.id, currentEnvironment.value)
    historyVersions.value = response.results || response
  } catch (err) {
    console.error('Failed to load history:', err)
    alert('Failed to load history.')
  }
}

// Watch for environment changes
watch(currentEnvironment, () => {
  // Re-render will happen automatically due to computed properties
})

async function handleRollback(version) {
  if (!confirm(`Are you sure you want to rollback to version v${version.version_number}? This will overwrite current values.`)) {
    return
  }
  
  try {
    await configObjectService.rollbackVersion(version.id)
    alert('Rollback successful!')
    
    // Refresh history and values
    await openHistory(viewingHistoryObject.value)
    await loadConfigObjects()
  } catch (err) {
    console.error('Rollback failed:', err)
    alert('Rollback failed. Please try again.')
  }
}

onMounted(() => {
  loadAsset()
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-12">
      <div class="text-muted-foreground">Loading asset...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-12">
      <div class="text-destructive mb-4">{{ error }}</div>
      <button @click="loadAsset" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
        Retry
      </button>
    </div>

    <!-- Asset Content -->
    <template v-else-if="asset">
      <!-- Header -->
      <div class="flex items-start justify-between">
        <div class="flex-1">
          <h1 class="text-3xl font-bold text-foreground normal-case">{{ asset.name }}</h1>
          <div class="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
            <span class="font-mono">{{ asset.slug }}</span>
            <span>•</span>
            <span>{{ asset.context }}</span>
            <span>•</span>
            <span class="px-2 py-0.5 bg-primary/10 text-primary rounded">{{ asset.context_type }}</span>
            <span>•</span>
            <span>Updated {{ formatDate(asset.updated_at) }}</span>
          </div>
          <p v-if="asset.description" class="mt-2 text-muted-foreground">{{ asset.description }}</p>
        </div>
        <div class="flex gap-2">
          <button @click="showHistoryModal = true" class="px-4 py-2 bg-background border border-input rounded-lg hover:bg-muted">
            History
          </button>
          <button @click="editAsset" class="px-4 py-2 bg-background border border-input rounded-lg hover:bg-muted">
            Edit
          </button>
          <button @click="deleteAsset" class="px-4 py-2 bg-destructive/10 text-destructive border border-destructive/20 rounded-lg hover:bg-destructive/20">
            Delete
          </button>
        </div>
      </div>

      <!-- Environment & Actions Bar -->
      <div class="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <label class="text-sm font-medium text-foreground">Environment:</label>
          <select
            v-model="environmentStore.currentEnvironment"
            class="px-4 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="local">Local</option>
            <option value="stage">Stage</option>
            <option value="prod">Production</option>
          </select>
        </div>
        <div class="flex gap-2">
          <button @click="showPromoteModal = true" class="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90">
            Promote Config
          </button>
          <button @click="showAddObjectModal = true" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90">
            + Add Object
          </button>
        </div>
      </div>

      <!-- Config Objects -->
      <div v-if="configObjects.length === 0" class="bg-card border border-border rounded-lg p-12 text-center">
        <p class="text-muted-foreground mb-4">No config objects yet.</p>
        <button @click="showAddObjectModal = true" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
          Add Your First Object
        </button>
      </div>

      <div v-else class="bg-card border border-border rounded-lg">
        <!-- Tabs -->
        <div class="border-b border-border flex overflow-x-auto">
          <button
            v-for="(obj, index) in configObjects"
            :key="obj.id"
            @click="activeTab = index"
            :class="[
              'px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
              activeTab === index
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            ]"
          >
            <div class="flex items-center gap-2">
              <span class="normal-case">{{ obj.name }}</span>
              <span v-if="!hasValues(obj)" class="text-xs text-destructive">●</span>
              <span 
                v-else-if="!checkEnvironmentSync(obj).synced" 
                class="text-xs text-yellow-600"
                :title="checkEnvironmentSync(obj).message"
              >
                ⚠
              </span>
              <span 
                v-else 
                class="text-xs text-green-600"
                title="All environments synced"
              >
                ✓
              </span>
            </div>
          </button>
        </div>

        <!-- Tab Content -->
        <div class="p-6">
          <div v-for="(obj, index) in configObjects" :key="obj.id" v-show="activeTab === index">
            <!-- Header Section -->
            <div class="mb-6">
              <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                  <h3 class="text-lg font-semibold text-foreground normal-case">{{ obj.name }}</h3>
                  <p class="text-sm text-muted-foreground">Type: {{ obj.object_type.toUpperCase() }}</p>
                </div>
                <div class="flex gap-2">
                  <button @click="openHistory(obj)" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">
                    History
                  </button>
                  <button @click="openEditValues(obj)" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">
                    {{ hasValues(obj) ? 'Edit Values' : 'Add Values' }}
                  </button>
                  <button @click="handleDeleteObject(obj)" class="px-3 py-1.5 bg-destructive/10 text-destructive rounded text-sm">
                    Delete
                  </button>
                </div>
              </div>
              
              <!-- Description -->
              <div v-if="obj.description" class="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                <div class="flex items-start justify-between gap-2">
                  <div class="flex items-start gap-2 flex-1">
                    <svg class="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p class="text-sm text-foreground">{{ obj.description }}</p>
                  </div>
                  <button 
                    @click="openEditDescription(obj)" 
                    class="text-xs text-blue-600 hover:text-blue-700 font-medium flex-shrink-0"
                  >
                    Edit
                  </button>
                </div>
              </div>
              <div v-else class="bg-muted/30 border border-border rounded-lg p-3">
                <div class="flex items-center justify-between">
                  <p class="text-sm text-muted-foreground italic">No description</p>
                  <button 
                    @click="openEditDescription(obj)" 
                    class="text-xs text-primary hover:text-primary/80 font-medium"
                  >
                    Add Description
                  </button>
                </div>
              </div>
              
              <!-- Environment Sync Status -->
              <div 
                v-if="hasValues(obj)"
                :class="[
                  'rounded-lg p-3 flex items-center gap-2',
                  checkEnvironmentSync(obj).synced 
                    ? 'bg-green-500/10 border border-green-500/20' 
                    : 'bg-yellow-500/10 border border-yellow-500/20'
                ]"
              >
                <svg 
                  v-if="checkEnvironmentSync(obj).synced"
                  class="w-4 h-4 text-green-600 flex-shrink-0" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <svg 
                  v-else
                  class="w-4 h-4 text-yellow-600 flex-shrink-0" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div class="flex-1">
                  <p 
                    :class="[
                      'text-sm font-medium',
                      checkEnvironmentSync(obj).synced ? 'text-green-700' : 'text-yellow-700'
                    ]"
                  >
                    {{ checkEnvironmentSync(obj).message }}
                  </p>
                  <p 
                    v-if="checkEnvironmentSync(obj).missingEnvs.length > 0"
                    class="text-xs text-muted-foreground mt-0.5"
                  >
                    Add values to missing environments or use "Promote Config" to sync
                  </p>
                </div>
              </div>
            </div>

            <!-- Values Display -->
            <div v-if="!hasValues(obj)" class="bg-muted/30 border border-border rounded-lg p-8 text-center">
              <p class="text-muted-foreground">No values set for {{ currentEnvironment }} environment</p>
            </div>

            <!-- KV Type -->
            <div v-else-if="obj.object_type === 'kv'" class="border border-border rounded-lg overflow-hidden">
              <table class="w-full">
                <thead class="bg-muted/50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Key</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Value</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Type</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border">
                  <tr v-for="value in getObjectValues(obj)" :key="value.id">
                    <td class="px-4 py-2 font-mono text-sm">{{ value.key }}</td>
                    <td class="px-4 py-2 text-sm">
                      <span v-if="value.value_type === 'json'" class="font-mono text-xs">
                        {{ JSON.stringify(value.value_json) }}
                      </span>
                      <span v-else-if="value.value_type === 'boolean'" :class="value.value_string === 'true' ? 'text-green-600' : 'text-red-600'">
                        {{ value.value_string }}
                      </span>
                      <span v-else class="font-mono">{{ value.value_string }}</span>
                    </td>
                    <td class="px-4 py-2 text-xs text-muted-foreground">{{ value.value_type }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- JSON Type -->
            <div v-else-if="obj.object_type === 'json'" class="border border-border rounded-lg p-4 bg-muted/30">
              <pre class="text-sm font-mono overflow-x-auto">{{ JSON.stringify(getObjectValues(obj)[0]?.value_json, null, 2) }}</pre>
            </div>

            <!-- YAML Type -->
            <div v-else-if="obj.object_type === 'yaml'" class="border border-border rounded-lg p-4 bg-muted/30">
              <pre class="text-sm font-mono whitespace-pre-wrap">{{ getObjectValues(obj)[0]?.value_string }}</pre>
            </div>

            <!-- Text Type -->
            <div v-else class="border border-border rounded-lg p-4 bg-muted/30">
              <pre class="text-sm whitespace-pre-wrap">{{ getObjectValues(obj)[0]?.value_string }}</pre>
            </div>

            <!-- API Usage Section -->
            <div v-if="hasValues(obj)" class="mt-6 space-y-4">
              <h4 class="text-sm font-semibold text-foreground">API Usage</h4>
              
              <!-- Curl Command -->
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-2">cURL Command</label>
                <div class="bg-muted/50 border border-border rounded-lg p-3 font-mono text-xs overflow-x-auto">
                  <pre class="text-foreground">{{ generateCurlCommand(obj) }}</pre>
                </div>
              </div>

              <!-- Sample Response -->
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-2">Sample Response</label>
                <div class="bg-muted/50 border border-border rounded-lg p-3 font-mono text-xs overflow-x-auto">
                  <pre class="text-foreground">{{ generateSampleResponse(obj) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Add Object Modal -->
    <div v-if="showAddObjectModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showAddObjectModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold text-foreground mb-4">Add Config Object</h2>
        <form @submit.prevent="handleAddObject" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Name *</label>
            <input
              v-model="newObjectForm.name"
              type="text"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg"
              placeholder="e.g., stripe_config"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Type</label>
            <select v-model="newObjectForm.object_type" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="kv">Key-Value</option>
              <option value="json">JSON</option>
              <option value="yaml">YAML</option>
              <option value="text">Text</option>
              <option value="file">File</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Description</label>
            <textarea
              v-model="newObjectForm.description"
              rows="2"
              class="w-full px-4 py-2 bg-background border border-input rounded-lg resize-none"
            ></textarea>
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg">Create</button>
            <button type="button" @click="showAddObjectModal = false" class="px-4 py-2 bg-background border border-input rounded-lg">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Description Modal -->
    <div v-if="showEditDescriptionModal && editingObject" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showEditDescriptionModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-lg">
        <h2 class="text-xl font-bold text-foreground mb-4">
          Edit Description: {{ editingObject.name }}
        </h2>

        <form @submit.prevent="handleSaveDescription" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Description</label>
            <textarea
              v-model="editDescriptionForm.description"
              rows="4"
              class="w-full px-4 py-2 bg-background border border-input rounded-lg resize-y"
              placeholder="Add a description to provide context for this config object..."
            ></textarea>
            <p class="text-xs text-muted-foreground mt-1">
              Describe what this configuration is for and how it should be used.
            </p>
          </div>

          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg">
              Save Description
            </button>
            <button type="button" @click="showEditDescriptionModal = false" class="px-4 py-2 bg-background border border-input rounded-lg">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Values Modal -->
    <div v-if="showEditValuesModal && editingObject" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showEditValuesModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <h2 class="text-xl font-bold text-foreground mb-4">
          Edit Values: {{ editingObject.name }} ({{ currentEnvironment }})
        </h2>

        <form @submit.prevent="handleSaveValues" class="space-y-4">
          <!-- KV Type -->
          <div v-if="editingObject.object_type === 'kv'" class="space-y-2">
            <div v-for="(row, index) in editValuesForm.values" :key="index" class="flex gap-2 items-start">
              <input
                v-model="row.key"
                type="text"
                placeholder="Key"
                required
                class="flex-1 px-3 py-2 bg-background border border-input rounded text-sm font-mono"
              />
              <select
                v-model="row.value_type"
                class="px-3 py-2 bg-background border border-input rounded text-sm"
              >
                <option value="string">String</option>
                <option value="number">Number</option>
                <option value="boolean">Boolean</option>
                <option value="json">JSON</option>
                <option value="yaml">YAML</option>
              </select>
              
              <!-- Boolean Dropdown -->
              <select
                v-if="row.value_type === 'boolean'"
                v-model="row.value_string"
                required
                class="flex-1 px-3 py-2 bg-background border border-input rounded text-sm"
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
              
              <!-- JSON Editor -->
              <div v-else-if="row.value_type === 'json'" class="flex-1">
                <CodeEditor
                  v-model="row.value_json"
                  language="json"
                  placeholder='{"key": "value"}'
                  height="400px"
                />
              </div>
              
              <!-- YAML Editor -->
              <div v-else-if="row.value_type === 'yaml'" class="flex-1">
                <CodeEditor
                  v-model="row.value_string"
                  language="yaml"
                  placeholder='key: value'
                  height="400px"
                />
              </div>
              
              <!-- String/Number Input -->
              <input
                v-else
                v-model="row.value_string"
                type="text"
                placeholder="Value"
                required
                class="flex-1 px-3 py-2 bg-background border border-input rounded text-sm font-mono"
              />
              
              <button
                type="button"
                @click="removeKVRow(index)"
                class="px-3 py-2 bg-destructive/10 text-destructive rounded text-sm"
              >
                ×
              </button>
            </div>
            <button
              type="button"
              @click="addKVRow"
              class="w-full px-4 py-2 bg-muted border border-border rounded text-sm"
            >
              + Add Row
            </button>
          </div>

          <!-- JSON Type -->
          <div v-else-if="editingObject.object_type === 'json'">
            <CodeEditor
              v-model="editValuesForm.values[0].value_json"
              language="json"
              placeholder='{\n  "key": "value"\n}'
              height="500px"
            />
          </div>

          <!-- YAML Type -->
          <div v-else-if="editingObject.object_type === 'yaml'">
            <CodeEditor
              v-model="editValuesForm.values[0].value_string"
              language="yaml"
              placeholder='key: value'
              height="500px"
            />
          </div>

          <!-- Text Type -->
          <div v-else>
            <textarea
              v-model="editValuesForm.values[0].value_string"
              rows="12"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded text-sm resize-y"
              placeholder="Enter text content..."
            ></textarea>
          </div>

          <div class="flex gap-2 pt-4">
            <button type="submit" class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg">Save Values</button>
            <button type="button" @click="showEditValuesModal = false" class="px-4 py-2 bg-background border border-input rounded-lg">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Promote Modal -->
    <div v-if="showPromoteModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showPromoteModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold text-foreground mb-4">Promote Configuration</h2>
        <form @submit.prevent="handlePromote" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">From Environment</label>
            <select v-model="promoteForm.from_environment" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="local">Local</option>
              <option value="stage">Stage</option>
              <option value="prod">Production</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">To Environment</label>
            <select v-model="promoteForm.to_environment" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="local">Local</option>
              <option value="stage">Stage</option>
              <option value="prod">Production</option>
            </select>
          </div>
          <p class="text-sm text-muted-foreground">
            This will sync the configuration structure from <strong>{{ promoteForm.from_environment }}</strong> to <strong>{{ promoteForm.to_environment }}</strong>.
          </p>
          <div class="bg-muted/50 p-3 rounded text-xs text-muted-foreground space-y-2">
            <p>
              <span class="font-semibold text-foreground">Key-Value Objects:</span> 
              New keys are added. Obsolete keys are removed. <span class="text-green-600 font-medium">Existing values are preserved.</span>
            </p>
            <p>
              <span class="font-semibold text-foreground">Other Objects:</span> 
              The entire configuration is overwritten.
            </p>
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg">Promote</button>
            <button type="button" @click="showPromoteModal = false" class="px-4 py-2 bg-background border border-input rounded-lg">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <!-- History Modal (Placeholder) -->
    <!-- History Modal -->
    <div v-if="showHistoryModal && viewingHistoryObject" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showHistoryModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-foreground">
            Version History: {{ viewingHistoryObject.name }} ({{ currentEnvironment }})
          </h2>
          <button @click="showHistoryModal = false" class="text-muted-foreground hover:text-foreground">
            ✕
          </button>
        </div>

        <div v-if="historyVersions.length === 0" class="text-center py-12 text-muted-foreground">
          No history available for this environment.
        </div>

        <div v-else class="space-y-4">
          <div v-for="version in historyVersions" :key="version.id" class="border border-border rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-3">
                <span class="px-2 py-1 bg-primary/10 text-primary rounded text-xs font-bold">
                  v{{ version.version_number }}
                </span>
                <span class="text-sm text-muted-foreground">
                  {{ formatDate(version.updated_at) }}
                </span>
                <span v-if="version.change_summary" class="text-sm text-foreground font-medium">
                  {{ version.change_summary }}
                </span>
              </div>
              <div class="text-xs text-muted-foreground">
                Updated by: {{ version.updated_by_name || 'System' }}
              </div>
            </div>

            <!-- Snapshot Display -->
            <div class="bg-muted/30 rounded p-3 font-mono text-xs overflow-x-auto max-h-60 mb-3">
              <pre>{{ JSON.stringify(version.value_snapshot.values, null, 2) }}</pre>
            </div>

            <div class="flex justify-end">
              <button 
                @click="handleRollback(version)"
                class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-xs hover:opacity-90"
              >
                Rollback to this version
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
