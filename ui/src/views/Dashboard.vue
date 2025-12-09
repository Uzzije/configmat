<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useEnvironmentStore } from '../stores/environment'
import { assetService } from '../api/services'

const router = useRouter()
const authStore = useAuthStore()
const environmentStore = useEnvironmentStore()

const assets = ref([])
const isLoading = ref(true)
const error = ref('')

const stats = computed(() => ({
  totalAssets: assets.value.length,
  environments: 3, // local, stage, prod
  recentChanges: assets.value.filter(a => {
    const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
    return new Date(a.updated_at) > dayAgo
  }).length
}))

const filteredAssets = computed(() => {
  return assets.value
    .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
    .slice(0, 5) // Show 5 most recent
})

async function loadAssets() {
  isLoading.value = true
  error.value = ''
  
  try {
    const response = await assetService.getAssets()
    // Handle both paginated and non-paginated responses
    assets.value = response.results || response
  } catch (err) {
    console.error('Failed to load assets:', err)
    error.value = 'Failed to load assets'
  } finally {
    isLoading.value = false
  }
}

function viewAsset(asset) {
  router.push(`/assets/${asset.slug}`)
}

function createAsset() {
  router.push('/assets/create')
}

function formatDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) return `${diffMins} minutes ago`
  if (diffHours < 24) return `${diffHours} hours ago`
  if (diffDays < 7) return `${diffDays} days ago`
  
  return date.toLocaleDateString()
}

onMounted(() => {
  loadAssets()
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-foreground">Dashboard</h1>
        <p class="text-muted-foreground mt-1">Welcome back, {{ authStore.user?.first_name || authStore.user?.email }}</p>
      </div>
      <button
        @click="createAsset"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium"
      >
        + Create Config Asset
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="text-sm text-muted-foreground mb-1">Total Assets</div>
        <div class="text-3xl font-bold text-foreground">{{ stats.totalAssets }}</div>
      </div>
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="text-sm text-muted-foreground mb-1">Environments</div>
        <div class="text-3xl font-bold text-foreground">{{ stats.environments }}</div>
      </div>
      <div 
        @click="router.push('/settings/activity')"
        class="bg-card border border-border rounded-lg p-6 cursor-pointer hover:bg-muted/50 transition-colors"
      >
        <div class="text-sm text-muted-foreground mb-1">Recent Changes (24h)</div>
        <div class="text-3xl font-bold text-foreground">{{ stats.recentChanges }}</div>
      </div>
    </div>

    <!-- Recent Assets -->
    <div class="bg-card border border-border rounded-lg">
      <div class="p-6 border-b border-border flex items-center justify-between">
        <h2 class="text-xl font-semibold text-foreground">Recent Assets</h2>
        <select
          v-model="environmentStore.currentEnvironment"
          class="px-3 py-1.5 bg-background border border-input rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="local">Local</option>
          <option value="stage">Stage</option>
          <option value="prod">Production</option>
        </select>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="p-8 text-center text-muted-foreground">
        Loading assets...
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="p-8 text-center text-destructive">
        {{ error }}
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredAssets.length === 0" class="p-8 text-center text-muted-foreground">
        No assets found. Create your first config asset to get started!
      </div>

      <!-- Assets Table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-muted/50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Name</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Context</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Type</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Last Updated</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="asset in filteredAssets" :key="asset.id" class="hover:bg-muted/30 transition-colors">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-foreground">{{ asset.name }}</div>
                <div class="text-xs text-muted-foreground">{{ asset.slug }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                {{ asset.context || 'global' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-1 text-xs font-medium rounded-full bg-primary/10 text-primary">
                  {{ asset.context_type }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                {{ formatDate(asset.updated_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button
                  @click="viewAsset(asset)"
                  class="text-primary hover:underline"
                >
                  View
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
