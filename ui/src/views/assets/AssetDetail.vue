<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEnvironmentStore } from '../../stores/environment'
import { useAuthStore } from '../../stores/auth'
import { assetService, configObjectService } from '../../api/services'
import CodeEditor from '../../components/CodeEditor.vue'
import DiffViewer from '../../components/DiffViewer.vue'
import SmartInput from '../../components/SmartInput.vue'
import SchemaBuilder from '../../components/SchemaBuilder.vue'

const route = useRoute()
const router = useRouter()
const environmentStore = useEnvironmentStore()
const authStore = useAuthStore()

const asset = ref(null)
const configObjects = ref([])
const isLoading = ref(true)
const error = ref('')
const activeTab = ref(0)
const activePageTab = ref('values') // 'values' | 'integration' | 'history'

// Modals
const showAddObjectModal = ref(false)
const showEditValuesModal = ref(false)
const showEditDescriptionModal = ref(false)
const showPromoteModal = ref(false)
const showHistoryModal = ref(false)
const showSchemaModal = ref(false)
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

// Promote Preview State
const isPreviewingPromote = ref(false)
const promoteDiffs = ref([])
const promoteLoading = ref(false)

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

// Format JSON for display (handles both objects and stringified JSON)
function formatJsonForDisplay(value) {
  if (!value) return '{}'
  
  // If it's already an object, stringify it
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  
  // If it's a string, try to parse it first
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return JSON.stringify(parsed, null, 2)
    } catch (e) {
      // If parsing fails, return as-is (might be plain text)
      return value
    }
  }
  
  return String(value)
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
    let jsonValue = existingValues[0]?.value_json || {}
    // Parse if it's a string (backend sometimes returns stringified JSON)
    if (typeof jsonValue === 'string') {
      try {
        jsonValue = JSON.parse(jsonValue)
      } catch (e) {
        console.warn('Failed to parse JSON value:', e)
      }
    }
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
  } else if (configObject.object_type === 'yaml') {
    // YAML is stored as string
    editValuesForm.value = {
      environment: currentEnvironment.value,
      values: [{ 
        key: configObject.name, 
        value_type: 'yaml', 
        value_string: existingValues[0]?.value_string || '',
        value_json: null,
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

// Mock Schema Store (In production this would come from backend)
// Structure: { [assetId]: { [configKey]: { type: 'number', min: 10, ... } } }
const mockSchemas = ref({})

// Get schema for current object
const currentObjectSchema = computed(() => {
    if (!editingObject.value) return {}
    return mockSchemas.value[editingObject.value.id] || {}
})

function handleSaveSchema(newSchema) {
    if (!editingObject.value) return
    const assetId = editingObject.value.id
    mockSchemas.value[assetId] = newSchema
    
    // In real app, we would save this to backend
    console.log('Saved Schema for', editingObject.value.name, newSchema)
}

// Validation State for Edit Form
const formErrors = ref({})

function handleValidationError(key, errorMsg) {
    if (errorMsg) {
        formErrors.value[key] = errorMsg
    } else {
        delete formErrors.value[key]
    }
}

const isFormValid = computed(() => Object.keys(formErrors.value).length === 0)

async function handleSaveValues() {
  if (!isFormValid.value) return 

  try {
    await configObjectService.updateObjectValues(
      editingObject.value.id,
      editValuesForm.value.environment,
      editValuesForm.value.values
    )
    
    await loadConfigObjects()
    showEditValuesModal.value = false
    editingObject.value = null
    formErrors.value = {}
  } catch (err) {
    console.error('Failed to save values:', err)
    alert('Failed to save values. Please try again.')
  }
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

async function handlePromotePreview() {
  promoteLoading.value = true
  promoteDiffs.value = []
  
  try {
    // 1. Fetch all objects for the asset
    const fromEnv = promoteForm.value.from_environment
    const toEnv = promoteForm.value.to_environment
    
    // We reuse existing configObjects if possible or fetch fresh
    const objects = configObjects.value
    
    // Calculate Diff for each object
    for (const obj of objects) {
      const fromValues = obj.values.filter(v => v.environment === fromEnv)
      const toValues = obj.values.filter(v => v.environment === toEnv)
      
      const fromData = extractDiffValues(fromValues)
      const toData = extractDiffValues(toValues)
      
      // Determine if there is a change
      // Simplistic check: JSON stringify comparison
      if (JSON.stringify(fromData) !== JSON.stringify(toData)) {
        promoteDiffs.value.push({
          id: obj.id,
          name: obj.name,
          object_type: obj.object_type,
          oldValue: toData,
          newValue: fromData
        })
      }
    }
    
    isPreviewingPromote.value = true
  } catch (err) {
    console.error('Failed to preview promote:', err)
    alert('Failed to calculate differences.')
  } finally {
    promoteLoading.value = false
  }
}

async function handlePromoteConfirm() {
  try {
    promoteLoading.value = true
    await assetService.promoteAsset(
      asset.value.slug,
      promoteForm.value.from_environment,
      promoteForm.value.to_environment
    )
    
    showPromoteModal.value = false
    isPreviewingPromote.value = false
    alert('Promotion successful! Environments are now synced.')
    
    // Reload after a delay
    setTimeout(() => {
        loadConfigObjects()
        // Reset modal state
        promoteDiffs.value = [] 
    }, 1000)
  } catch (err) {
    console.error('Failed to promote:', err)
    alert('Failed to promote configuration. Please try again.')
  } finally {
    promoteLoading.value = false
  }
}

function resetPromoteModal() {
    showPromoteModal.value = false
    isPreviewingPromote.value = false
    promoteDiffs.value = []
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

// Helper to extract values for diff
function extractDiffValues(versionValues) {
  if (!versionValues) return {}
  
  // If it's a KV array, convert to object for cleaner diff
  if (Array.isArray(versionValues)) {
    const obj = {}
    versionValues.forEach(v => {
        if (v.value_type === 'json') obj[v.key] = v.value_json
        else if (v.value_type === 'boolean') obj[v.key] = v.value_string === 'true'
        else if (v.value_type === 'number') obj[v.key] = Number(v.value_string)
        else obj[v.key] = v.value_string
    })
    return obj
  }
  return versionValues
}

// Helper to get previous version for diffing
function getPreviousVersion(index) {
  if (index >= historyVersions.value.length - 1) return null
  return historyVersions.value[index + 1]
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
      <!-- Compact Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-foreground normal-case">{{ asset.name }}</h1>
          <div class="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
            <span class="font-mono text-xs">{{ asset.slug }}</span>
            <span>•</span>
            <span class="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">{{ asset.context_type }}</span>
          </div>
        </div>
        <div class="flex gap-2">
          <button @click="editAsset" class="px-3 py-1.5 text-sm bg-background border border-input rounded-lg hover:bg-muted">
            Edit
          </button>
          <button @click="deleteAsset" class="px-3 py-1.5 text-sm bg-destructive/10 text-destructive border border-destructive/20 rounded-lg hover:bg-destructive/20">
            Delete
          </button>
        </div>
      </div>

      <!-- Main Tab Navigation -->
      <div class="border-b border-border mb-6">
        <div class="flex gap-6">
          <button
            @click="activePageTab = 'values'"
            :class="[
              'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activePageTab === 'values'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            ]"
          >
            Values
          </button>
          <button
            @click="activePageTab = 'integration'"
            :class="[
              'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activePageTab === 'integration'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            ]"
          >
            Integration
          </button>
          <button
            @click="activePageTab = 'history'"
            :class="[
              'pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activePageTab === 'history'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            ]"
          >
            History
          </button>
        </div>
      </div>

      <!-- Values Tab -->
      <div v-show="activePageTab === 'values'">
        <!-- Environment & Actions Bar -->
        <div class="bg-card border border-border rounded-lg p-4 flex items-center justify-between mb-6">
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
                  <button @click="showSchemaModal = true; editingObject = obj" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">
                    Rules
                  </button>
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
              <pre class="text-sm font-mono overflow-x-auto">{{ formatJsonForDisplay(getObjectValues(obj)[0]?.value_json) }}</pre>
            </div>

            <!-- YAML Type -->
            <div v-else-if="obj.object_type === 'yaml'" class="border border-border rounded-lg p-4 bg-muted/30">
              <pre class="text-sm font-mono whitespace-pre-wrap">{{ getObjectValues(obj)[0]?.value_string }}</pre>
            </div>

            <!-- Text Type -->
            <div v-else class="border border-border rounded-lg p-4 bg-muted/30">
              <pre class="text-sm whitespace-pre-wrap">{{ getObjectValues(obj)[0]?.value_string }}</pre>
            </div>

            <!-- How to Access This Object -->
            <div v-if="hasValues(obj)" class="mt-6">
              <h4 class="text-sm font-semibold text-foreground mb-3">How to Access</h4>
              
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <!-- CLI -->
                <div class="border border-border rounded-lg p-3 bg-muted/20">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-3 h-3 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    <h5 class="font-semibold text-xs">CLI</h5>
                  </div>
                  <div class="bg-muted/50 rounded p-2 font-mono text-[10px] overflow-x-auto">
                    <div class="text-foreground">configmat get {{ asset.slug }}</div>
                    <div class="text-foreground">  --key {{ obj.key || obj.name.toLowerCase().replace(/\s+/g, '-') }}</div>
                  </div>
                </div>

                <!-- Python SDK -->
                <div class="border border-border rounded-lg p-3 bg-muted/20">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-3 h-3 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59.28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42.24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-.17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2.01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-.04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35.07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.23.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z"/>
                    </svg>
                    <h5 class="font-semibold text-xs">Python</h5>
                  </div>
                  <div class="bg-muted/50 rounded p-2 font-mono text-[10px] overflow-x-auto">
                    <div class="text-foreground">config = client.get(</div>
                    <div class="text-foreground ml-2">"{{ asset.slug }}"</div>
                    <div class="text-foreground">)</div>
                    <div class="text-foreground mt-1">val = config["{{ obj.key || obj.name.toLowerCase().replace(/\s+/g, '-') }}"]</div>
                  </div>
                </div>

                <!-- Node.js SDK -->
                <div class="border border-border rounded-lg p-3 bg-muted/20">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M11.998,24c-0.321,0-0.641-0.084-0.922-0.247l-2.936-1.737c-0.438-0.245-0.224-0.332-0.08-0.383 c0.585-0.203,0.703-0.25,1.328-0.604c0.065-0.037,0.151-0.023,0.218,0.017l2.256,1.339c0.082,0.045,0.197,0.045,0.272,0l8.795-5.076 c0.082-0.047,0.134-0.141,0.134-0.238V6.921c0-0.099-0.053-0.192-0.137-0.242l-8.791-5.072c-0.081-0.047-0.189-0.047-0.271,0 L3.075,6.68C2.99,6.729,2.936,6.825,2.936,6.921v10.15c0,0.097,0.054,0.189,0.139,0.235l2.409,1.392 c1.307,0.654,2.108-0.116,2.108-0.89V7.787c0-0.142,0.114-0.253,0.256-0.253h1.115c0.139,0,0.255,0.112,0.255,0.253v10.021 c0,1.745-0.95,2.745-2.604,2.745c-0.508,0-0.909,0-2.026-0.551L2.28,18.675c-0.57-0.329-0.922-0.945-0.922-1.604V6.921 c0-0.659,0.353-1.275,0.922-1.603l8.795-5.082c0.557-0.315,1.296-0.315,1.848,0l8.794,5.082c0.57,0.329,0.924,0.944,0.924,1.603 v10.15c0,0.659-0.354,1.273-0.924,1.604l-8.794,5.078C12.643,23.916,12.324,24,11.998,24z M19.099,13.993 c0-1.9-1.284-2.406-3.987-2.763c-2.731-0.361-3.009-0.548-3.009-1.187c0-0.528,0.235-1.233,2.258-1.233 c1.807,0,2.473,0.389,2.747,1.607c0.024,0.115,0.129,0.199,0.247,0.199h1.141c0.071,0,0.138-0.031,0.186-0.081 c0.048-0.054,0.074-0.123,0.067-0.196c-0.177-2.098-1.571-3.076-4.388-3.076c-2.508,0-4.004,1.058-4.004,2.833 c0,1.925,1.488,2.457,3.895,2.695c2.88,0.282,3.103,0.703,3.103,1.269c0,0.983-0.789,1.402-2.642,1.402 c-2.327,0-2.839-0.584-3.011-1.742c-0.02-0.124-0.126-0.215-0.253-0.215h-1.137c-0.141,0-0.254,0.112-0.254,0.253 c0,1.482,0.806,3.248,4.655,3.248C17.501,17.007,19.099,15.91,19.099,13.993z"/>
                    </svg>
                    <h5 class="font-semibold text-xs">Node.js</h5>
                  </div>
                  <div class="bg-muted/50 rounded p-2 font-mono text-[10px] overflow-x-auto">
                    <div class="text-foreground">const config = ConfigMat</div>
                    <div class="text-foreground ml-2">.load({ asset: '{{ asset.slug }}' })</div>
                    <div class="text-foreground mt-1">const val = config.get(</div>
                    <div class="text-foreground ml-2">'{{ obj.key || obj.name.toLowerCase().replace(/\s+/g, '-') }}'</div>
                    <div class="text-foreground">)</div>
                  </div>
                </div>

                <!-- cURL / REST API -->
                <div class="border border-border rounded-lg p-3 bg-muted/20">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-3 h-3 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
                    </svg>
                    <h5 class="font-semibold text-xs">REST API</h5>
                  </div>
                  <div class="bg-muted/50 rounded p-2 font-mono text-[10px] overflow-x-auto">
                    <div class="text-foreground">curl {{ generateCurlCommand(obj).split('\n')[0] }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div> <!-- End Values Tab -->

      <!-- Integration Tab -->
      <div v-show="activePageTab === 'integration'" class="space-y-6">
        <div class="bg-card border border-border rounded-lg p-6">
          <h2 class="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
            </svg>
            How to Access This Asset
          </h2>
          
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <!-- CLI -->
            <div class="border border-border rounded-lg p-4 bg-muted/20">
              <div class="flex items-center gap-2 mb-3">
                <svg class="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <h3 class="font-semibold text-sm">CLI</h3>
              </div>
              <div class="bg-muted/50 rounded p-3 font-mono text-xs overflow-x-auto">
                <div class="text-muted-foreground mb-1"># Get configuration</div>
                <div class="text-foreground">configmat get {{ asset.slug }}</div>
                <div class="text-muted-foreground mt-2 mb-1"># Pull to local</div>
                <div class="text-foreground">configmat pull</div>
              </div>
            </div>

            <!-- Python SDK -->
            <div class="border border-border rounded-lg p-4 bg-muted/20">
              <div class="flex items-center gap-2 mb-3">
                <svg class="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59.28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42.24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-.17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2.01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-.04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35.07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.23.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z"/>
                </svg>
                <h3 class="font-semibold text-sm">Python SDK</h3>
              </div>
              <div class="bg-muted/50 rounded p-3 font-mono text-xs overflow-x-auto">
                <div class="text-muted-foreground mb-1"># Initialize</div>
                <div class="text-foreground">from configmat import ConfigMat</div>
                <div class="text-foreground mt-1">client = ConfigMat(api_key="...")</div>
                <div class="text-muted-foreground mt-2 mb-1"># Get config</div>
                <div class="text-foreground">config = client.get("{{ asset.slug }}")</div>
              </div>
            </div>

            <!-- Node.js SDK -->
            <div class="border border-border rounded-lg p-4 bg-muted/20">
              <div class="flex items-center gap-2 mb-3">
                <svg class="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M11.998,24c-0.321,0-0.641-0.084-0.922-0.247l-2.936-1.737c-0.438-0.245-0.224-0.332-0.08-0.383 c0.585-0.203,0.703-0.25,1.328-0.604c0.065-0.037,0.151-0.023,0.218,0.017l2.256,1.339c0.082,0.045,0.197,0.045,0.272,0l8.795-5.076 c0.082-0.047,0.134-0.141,0.134-0.238V6.921c0-0.099-0.053-0.192-0.137-0.242l-8.791-5.072c-0.081-0.047-0.189-0.047-0.271,0 L3.075,6.68C2.99,6.729,2.936,6.825,2.936,6.921v10.15c0,0.097,0.054,0.189,0.139,0.235l2.409,1.392 c1.307,0.654,2.108-0.116,2.108-0.89V7.787c0-0.142,0.114-0.253,0.256-0.253h1.115c0.139,0,0.255,0.112,0.255,0.253v10.021 c0,1.745-0.95,2.745-2.604,2.745c-0.508,0-0.909,0-2.026-0.551L2.28,18.675c-0.57-0.329-0.922-0.945-0.922-1.604V6.921 c0-0.659,0.353-1.275,0.922-1.603l8.795-5.082c0.557-0.315,1.296-0.315,1.848,0l8.794,5.082c0.57,0.329,0.924,0.944,0.924,1.603 v10.15c0,0.659-0.354,1.273-0.924,1.604l-8.794,5.078C12.643,23.916,12.324,24,11.998,24z M19.099,13.993 c0-1.9-1.284-2.406-3.987-2.763c-2.731-0.361-3.009-0.548-3.009-1.187c0-0.528,0.235-1.233,2.258-1.233 c1.807,0,2.473,0.389,2.747,1.607c0.024,0.115,0.129,0.199,0.247,0.199h1.141c0.071,0,0.138-0.031,0.186-0.081 c0.048-0.054,0.074-0.123,0.067-0.196c-0.177-2.098-1.571-3.076-4.388-3.076c-2.508,0-4.004,1.058-4.004,2.833 c0,1.925,1.488,2.457,3.895,2.695c2.88,0.282,3.103,0.703,3.103,1.269c0,0.983-0.789,1.402-2.642,1.402 c-2.327,0-2.839-0.584-3.011-1.742c-0.02-0.124-0.126-0.215-0.253-0.215h-1.137c-0.141,0-0.254,0.112-0.254,0.253 c0,1.482,0.806,3.248,4.655,3.248C17.501,17.007,19.099,15.91,19.099,13.993z"/>
                </svg>
                <h3 class="font-semibold text-sm">Node.js SDK</h3>
              </div>
              <div class="bg-muted/50 rounded p-3 font-mono text-xs overflow-x-auto">
                <div class="text-muted-foreground mb-1"># Initialize</div>
                <div class="text-foreground">import { ConfigMat } from '@configmat/sdk'</div>
                <div class="text-muted-foreground mt-2 mb-1"># Load config</div>
                <div class="text-foreground">const config = ConfigMat.load({</div>
                <div class="text-foreground ml-2">asset: '{{ asset.slug }}'</div>
                <div class="text-foreground">})</div>
              </div>
            </div>
          </div>

          <div class="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div class="flex items-start gap-2">
              <svg class="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <div class="text-sm">
                <p class="text-foreground font-medium mb-1">Need API credentials?</p>
                <p class="text-muted-foreground">Generate an API key in <router-link to="/api-keys" class="text-primary hover:underline">Settings → API Keys</router-link> to authenticate your CLI and SDK requests.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- History Tab -->
      <div v-show="activePageTab === 'history'">
        <div class="bg-card border border-border rounded-lg p-6">
          <p class="text-muted-foreground text-center py-12">
            Asset-level history coming soon. For now, use the "History" button on individual config objects.
          </p>
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
              
              <!-- Smart Input (Replaces standard inputs) -->
              <div v-else class="flex-1">
                <SmartInput
                    v-model="row.value_string"
                    :rule="currentObjectSchema[row.key] || {}"
                    :type="row.value_type"
                    placeholder="Value"
                    @validation-error="(msg) => handleValidationError(row.key, msg)"
                />
              </div>
              
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
            <button 
                type="submit" 
                class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="!isFormValid"
            >
                Save Values
            </button>
            <button type="button" @click="showEditValuesModal = false" class="px-4 py-2 bg-background border border-input rounded-lg">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Promote Modal -->
    <div v-if="showPromoteModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="resetPromoteModal">
      <div 
        class="bg-card border border-border rounded-lg p-6 w-full flex flex-col max-h-[90vh]"
        :class="isPreviewingPromote ? 'max-w-4xl' : 'max-w-md'"
      >
        <h2 class="text-xl font-bold text-foreground mb-4">Promote Configuration</h2>
        
        <!-- Step 1: Selection -->
        <form v-if="!isPreviewingPromote" @submit.prevent="handlePromotePreview" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">From Environment (Source)</label>
            <select v-model="promoteForm.from_environment" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="local">Local</option>
              <option value="stage">Stage</option>
              <option value="prod">Production</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">To Environment (Target)</label>
            <select v-model="promoteForm.to_environment" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="local">Local</option>
              <option value="stage">Stage</option>
              <option value="prod">Production</option>
            </select>
          </div>

          <div v-if="promoteForm.from_environment === promoteForm.to_environment" class="p-3 bg-destructive/10 text-destructive text-sm rounded">
             Source and Target environments cannot be the same.
          </div>

          <div class="bg-muted/50 p-3 rounded text-xs text-muted-foreground space-y-2">
            <p>
              This will calculate the differences between environments and allow you to review them before applying.
            </p>
          </div>
          <div class="flex gap-2 pt-2">
            <button 
                type="submit" 
                class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50"
                :disabled="promoteLoading || promoteForm.from_environment === promoteForm.to_environment"
            >
                {{ promoteLoading ? 'Calculating...' : 'Review Changes' }}
            </button>
            <button type="button" @click="resetPromoteModal" class="px-4 py-2 bg-background border border-input rounded-lg">Cancel</button>
          </div>
        </form>

        <!-- Step 2: Review (Diff) -->
        <div v-else class="flex-1 overflow-hidden flex flex-col">
            <div class="mb-4 text-sm text-muted-foreground">
                Reviewing changes from <strong>{{ promoteForm.from_environment }}</strong> &rarr; <strong>{{ promoteForm.to_environment }}</strong>
            </div>

            <div class="flex-1 overflow-y-auto space-y-6 pr-2">
                <div v-if="promoteDiffs.length === 0" class="text-center py-12 text-muted-foreground">
                    <div class="text-lg">No changes detected.</div>
                    <p class="text-sm">Environments are already in sync.</p>
                </div>

                <div v-else v-for="diff in promoteDiffs" :key="diff.id">
                    <DiffViewer
                        :old-value="diff.oldValue"
                        :new-value="diff.newValue"
                        :mode="diff.object_type === 'kv' ? 'visual' : 'code'"
                        :title="diff.name"
                    />
                </div>
            </div>

            <div class="flex gap-2 pt-6 mt-2 border-t border-border">
                <button 
                    @click="handlePromoteConfirm" 
                    class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50"
                    :disabled="promoteLoading || promoteDiffs.length === 0"
                >
                    {{ promoteLoading ? 'Promoting...' : `Confirm ${promoteDiffs.length} Change${promoteDiffs.length !== 1 ? 's' : ''}` }}
                </button>
                <button 
                    @click="isPreviewingPromote = false" 
                    class="px-4 py-2 bg-background border border-input rounded-lg"
                    :disabled="promoteLoading"
                >
                    Back
                </button>
            </div>
        </div>

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
          <div v-for="(version, index) in historyVersions" :key="version.id" class="border border-border rounded-lg p-4 transition-colors hover:border-primary/50">
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

            <!-- Diff Display -->
            <div class="mb-3">
              <DiffViewer
                :old-value="extractDiffValues(getPreviousVersion(index)?.value_snapshot?.values)"
                :new-value="extractDiffValues(version.value_snapshot.values)"
                :mode="viewingHistoryObject.object_type === 'kv' ? 'visual' : 'code'"
                :title="index === historyVersions.length - 1 ? 'Initial Version' : 'Changes vs Previous'"
              />
            </div>

            <div class="flex justify-end">
              <button 
                @click="handleRollback(version)"
                class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-xs hover:opacity-90 transition-colors"
                title="Revert configuration to this version"
              >
                Rollback to this version
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Schema Builder Modal -->
    <div v-if="showSchemaModal && editingObject" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showSchemaModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-4xl max-h-[90vh]">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-bold text-foreground">
              Validation Rules: {{ editingObject.name }}
            </h2>
            <button @click="showSchemaModal = false" class="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        
        <p class="text-sm text-muted-foreground mb-4">
            Define constraints for configuration keys (e.g. min/max, regex). These rules will be enforced when editing values.
        </p>

        <SchemaBuilder
            :model-value="mockSchemas[editingObject.id] || {}"
            @update:model-value="handleSaveSchema"
        />
        
        <div class="mt-4 flex justify-end">
            <button @click="showSchemaModal = false" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg">Done</button>
        </div>
      </div>
    </div>
  </div>
</template>
