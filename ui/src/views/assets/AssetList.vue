<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { assetService } from '../../api/services'

const router = useRouter()
const route = useRoute()

const assets = ref([])
const isLoading = ref(true)
const error = ref('')
const searchQuery = ref(route.query.search || '')
const selectedContext = ref('all')

const page = ref(1)
const hasNext = ref(false)
const hasPrev = ref(false)
const totalCount = ref(0)

const contextTypes = ['all', 'product', 'team', 'default']

watch(() => route.query.search, (newSearch) => {
  if (newSearch !== undefined && newSearch !== searchQuery.value) {
    searchQuery.value = newSearch || ''
  }
})

watch([searchQuery, selectedContext], () => {
  page.value = 1
  loadAssets()
})

async function loadAssets() {
  isLoading.value = true
  error.value = ''
  
  try {
    const params = {
      page: page.value,
      search: searchQuery.value
    }
    
    if (selectedContext.value !== 'all') {
      params.context_type = selectedContext.value
    }

    const response = await assetService.getAssets(params)
    assets.value = response.results || response
    hasNext.value = !!response.next
    hasPrev.value = !!response.previous
    totalCount.value = response.count
  } catch (err) {
    console.error('Failed to load assets:', err)
    error.value = 'Failed to load assets. Please try again.'
  } finally {
    isLoading.value = false
  }
}

function viewAsset(asset) {
  router.push(`/assets/${asset.slug}`)
}

function editAsset(asset) {
  router.push(`/assets/${asset.slug}/edit`)
}

function createAsset() {
  router.push('/assets/create')
}

async function deleteAsset(asset) {
  if (!confirm(`Are you sure you want to delete "${asset.name}"?`)) {
    return
  }

  try {
    await assetService.deleteAsset(asset.slug)
    await loadAssets() // Reload list
  } catch (err) {
    console.error('Failed to delete asset:', err)
    alert('Failed to delete asset. Please try again.')
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString()
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
        <h1 class="text-3xl font-bold text-foreground">Config Assets</h1>
        <p class="text-muted-foreground mt-1">Manage your configuration assets</p>
      </div>
      <button
        @click="createAsset"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium"
      >
        + Create Asset
      </button>
    </div>

    <!-- Filters -->
    <div class="bg-card border border-border rounded-lg p-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Search</label>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by name, slug, or context..."
            class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Context Type</label>
          <select
            v-model="selectedContext"
            class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option v-for="type in contextTypes" :key="type" :value="type">
              {{ type === 'all' ? 'All Types' : type }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="bg-card border border-border rounded-lg p-12 text-center">
      <div class="text-muted-foreground">Loading assets...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-card border border-border rounded-lg p-12 text-center">
      <div class="text-destructive">{{ error }}</div>
      <button
        @click="loadAssets"
        class="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
      >
        Retry
      </button>
    </div>

    <!-- Empty State -->
    <!-- Empty State -->
    <div v-else-if="assets.length === 0" class="bg-card border border-border rounded-lg p-12 text-center">
      <div class="text-muted-foreground mb-4">
        {{ searchQuery || selectedContext !== 'all' ? 'No assets match your filters' : 'No assets found' }}
      </div>
      <button
        v-if="!searchQuery && selectedContext === 'all'"
        @click="createAsset"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
      >
        Create Your First Asset
      </button>
    </div>

    <!-- Assets List (Table) -->
    <div v-else class="bg-card border border-border rounded-lg overflow-hidden">
      <table class="w-full">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Name</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Context Type</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Context</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Updated</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr 
            v-for="asset in assets" 
            :key="asset.id" 
            class="hover:bg-muted/30 cursor-pointer"
            @click="viewAsset(asset)"
          >
            <td class="px-6 py-4">
              <div class="font-medium text-foreground">{{ asset.name }}</div>
              <div class="text-sm text-muted-foreground">{{ asset.slug }}</div>
              <div v-if="asset.description" class="text-xs text-muted-foreground mt-1 line-clamp-1">{{ asset.description }}</div>
            </td>
            <td class="px-6 py-4">
              <span class="px-2 py-1 text-xs font-medium rounded-full bg-primary/10 text-primary">
                {{ asset.context_type }}
              </span>
            </td>
            <td class="px-6 py-4 text-sm text-foreground">
              {{ asset.context }}
            </td>
            <td class="px-6 py-4 text-sm text-muted-foreground">
              {{ formatDate(asset.updated_at) }}
            </td>
            <td class="px-6 py-4 text-right" @click.stop>
              <div class="flex justify-end gap-2">
                <button
                  @click="editAsset(asset)"
                  class="px-3 py-1.5 bg-background border border-input rounded text-sm hover:bg-muted transition-colors"
                >
                  Edit
                </button>
                <button
                  @click="deleteAsset(asset)"
                  class="px-3 py-1.5 bg-destructive/10 text-destructive border border-destructive/20 rounded text-sm hover:bg-destructive/20 transition-colors"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="px-6 py-4 border-t border-border flex items-center justify-between">
        <button 
          @click="page--; loadAssets()" 
          :disabled="!hasPrev || isLoading"
          class="px-4 py-2 bg-background border border-input rounded-lg disabled:opacity-50"
        >
          Previous
        </button>
        <span class="text-sm text-muted-foreground">
            Page {{ page }} (Total: {{ totalCount }})
        </span>
        <button 
          @click="page++; loadAssets()" 
          :disabled="!hasNext || isLoading"
          class="px-4 py-2 bg-background border border-input rounded-lg disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>
