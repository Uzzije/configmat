<script setup>
import { ref, onMounted } from 'vue'
import { apiKeyService, assetService } from '../api/services'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const apiKeys = ref([])
const assets = ref([])
const isLoading = ref(true)
const error = ref('')
const showCreateModal = ref(false)
const showKeyModal = ref(false)
const newKeyData = ref(null)

const createForm = ref({
  label: '',
  scope: 'tenant',
  environment: 'local',
  asset_slug: null
})

async function loadKeys() {
  isLoading.value = true
  error.value = ''
  
  try {
    const response = await apiKeyService.getKeys()
    apiKeys.value = response.results || response
  } catch (err) {
    console.error('Failed to load API keys:', err)
    error.value = 'Failed to load API keys. Please try again.'
  } finally {
    isLoading.value = false
  }
}

async function loadAssets() {
  try {
    const response = await assetService.getAssets()
    assets.value = response.results || response
  } catch (err) {
    console.error('Failed to load assets:', err)
  }
}

async function handleCreate() {
  try {
    const payload = {
      label: createForm.value.label,
      scope: createForm.value.scope,
      environment: createForm.value.environment
    }
    
    if (createForm.value.scope === 'asset') {
      payload.asset_slug = createForm.value.asset_slug
    }
    
    const result = await apiKeyService.createKey(payload)
    
    // Show the raw key (only shown once!)
    newKeyData.value = result
    showCreateModal.value = false
    showKeyModal.value = true
    
    // Reset form
    createForm.value = { label: '', scope: 'tenant', environment: 'local', asset_slug: null }
    
    // Reload list
    await loadKeys()
  } catch (err) {
    console.error('Failed to create API key:', err)
    const errorMsg = err.response?.data?.asset_slug?.[0] || err.response?.data?.label?.[0] || 'Failed to create API key. Please try again.'
    alert(errorMsg)
  }
}

async function handleRevoke(key) {
  if (!confirm(`Revoke API key "${key.label}"? This action cannot be undone.`)) {
    return
  }
  
  try {
    await apiKeyService.revokeKey(key.id)
    await loadKeys()
  } catch (err) {
    console.error('Failed to revoke API key:', err)
    alert('Failed to revoke API key. Please try again.')
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert('API key copied to clipboard!')
  }).catch(() => {
    alert('Failed to copy to clipboard')
  })
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString()
}

onMounted(() => {
  loadKeys()
  loadAssets()
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-foreground">API Keys</h1>
        <p class="text-muted-foreground mt-1">Manage API keys for programmatic access</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium"
      >
        + Create API Key
      </button>
    </div>

    <!-- Info Card -->
    <div class="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
      <h3 class="font-medium text-foreground mb-2">Using API Keys</h3>
      <p class="text-sm text-muted-foreground mb-3">
        Use API keys to access the public configuration endpoint. Include the key in the <code class="px-1 py-0.5 bg-muted rounded text-xs">X-API-Key</code> header.
      </p>
      <div class="bg-muted/50 rounded p-3 font-mono text-xs overflow-x-auto">
        <div>curl https://api.configmat.com/public/{{ authStore.user?.tenant?.slug || 'your-org' }}/asset-slug/prod \</div>
        <div class="ml-4">-H "X-API-Key: your_api_key_here"</div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="bg-card border border-border rounded-lg p-12 text-center">
      <div class="text-muted-foreground">Loading API keys...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-card border border-border rounded-lg p-12 text-center">
      <div class="text-destructive mb-4">{{ error }}</div>
      <button @click="loadKeys" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
        Retry
      </button>
    </div>

    <!-- Empty State -->
    <div v-else-if="apiKeys.length === 0" class="bg-card border border-border rounded-lg p-12 text-center">
      <p class="text-muted-foreground mb-4">No API keys yet.</p>
      <button @click="showCreateModal = true" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
        Create Your First API Key
      </button>
    </div>

    <!-- API Keys List -->
    <div v-else class="bg-card border border-border rounded-lg overflow-hidden">
      <table class="w-full">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Label</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Scope</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Environment</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Key Prefix</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Created</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="key in apiKeys" :key="key.id" class="hover:bg-muted/30">
            <td class="px-6 py-4">
              <div class="font-medium text-foreground">{{ key.label }}</div>
              <div v-if="key.asset_name" class="text-sm text-muted-foreground">Asset: {{ key.asset_name }}</div>
            </td>
            <td class="px-6 py-4">
              <span :class="[
                'px-2 py-1 text-xs font-medium rounded-full',
                key.scope === 'asset' ? 'bg-blue-500/10 text-blue-600' : 'bg-purple-500/10 text-purple-600'
              ]">
                {{ key.scope_display || key.scope }}
              </span>
            </td>
            <td class="px-6 py-4">
              <span class="px-2 py-1 text-xs font-medium rounded-full bg-secondary text-secondary-foreground uppercase">
                {{ key.environment }}
              </span>
            </td>
            <td class="px-6 py-4 font-mono text-sm text-muted-foreground">
              {{ key.key_prefix }}...
            </td>
            <td class="px-6 py-4 text-sm text-muted-foreground">
              {{ formatDate(key.created_at) }}
            </td>
            <td class="px-6 py-4">
              <span
                :class="[
                  'px-2 py-1 text-xs font-medium rounded-full',
                  !key.revoked
                    ? 'bg-green-500/10 text-green-600'
                    : 'bg-red-500/10 text-red-600'
                ]"
              >
                {{ !key.revoked ? 'Active' : 'Revoked' }}
              </span>
            </td>
            <td class="px-6 py-4">
              <button
                v-if="!key.revoked"
                @click="handleRevoke(key)"
                class="text-sm text-destructive hover:underline"
              >
                Revoke
              </button>
              <span v-else class="text-sm text-muted-foreground">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showCreateModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold text-foreground mb-4">Create API Key</h2>
        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">
              Label <span class="text-destructive">*</span>
            </label>
            <input
              v-model="createForm.label"
              type="text"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg"
              placeholder="e.g., Production API Key"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Scope</label>
            <select v-model="createForm.scope" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="tenant">Tenant-wide (all assets)</option>
              <option value="asset">Asset-specific</option>
            </select>
            <p class="text-xs text-muted-foreground mt-1">
              Tenant-wide keys can access all assets. Asset-specific keys are limited to one asset.
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Environment</label>
            <select v-model="createForm.environment" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="local">Local</option>
              <option value="stage">Stage</option>
              <option value="prod">Production</option>
            </select>
            <p class="text-xs text-muted-foreground mt-1">
              The environment this key is allowed to access.
            </p>
          </div>
          
          <div v-if="createForm.scope === 'asset'">
            <label class="block text-sm font-medium text-foreground mb-2">
              Asset <span class="text-destructive">*</span>
            </label>
            <select 
              v-model="createForm.asset_slug" 
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg"
            >
              <option :value="null">Select an asset...</option>
              <option v-for="asset in assets" :key="asset.id" :value="asset.slug">
                {{ asset.name }}
              </option>
            </select>
          </div>
          
          <div class="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-sm text-yellow-600">
            ⚠️ The API key will only be shown once. Make sure to copy it!
          </div>
          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg">
              Create Key
            </button>
            <button type="button" @click="showCreateModal = false" class="px-4 py-2 bg-background border border-input rounded-lg">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Show New Key Modal -->
    <div v-if="showKeyModal && newKeyData" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-lg">
        <h2 class="text-xl font-bold text-foreground mb-4">API Key Created!</h2>
        <div class="space-y-4">
          <div class="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-sm text-yellow-600">
            ⚠️ Copy this key now. You won't be able to see it again!
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Your API Key</label>
            <div class="flex gap-2">
              <input
                :value="newKeyData.key"
                readonly
                class="flex-1 px-4 py-2 bg-muted border border-input rounded-lg font-mono text-sm"
              />
              <button
                @click="copyToClipboard(newKeyData.key)"
                class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
              >
                Copy
              </button>
            </div>
          </div>
          <div class="bg-muted/50 rounded p-3 text-sm">
            <div class="font-medium text-foreground mb-1">{{ newKeyData.label }}</div>
            <div v-if="newKeyData.scope_display" class="text-muted-foreground">Scope: {{ newKeyData.scope_display }}</div>
            <div class="text-muted-foreground">Environment: {{ newKeyData.environment }}</div>
            <div v-if="newKeyData.asset_name" class="text-muted-foreground">Asset: {{ newKeyData.asset_name }}</div>
          </div>
          <button
            @click="showKeyModal = false; newKeyData = null"
            class="w-full px-4 py-2 bg-background border border-input rounded-lg hover:bg-muted"
          >
            I've Copied the Key
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
