<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { assetService } from '../../api/services'

const route = useRoute()
const router = useRouter()

const formData = ref({
  name: '',
  slug: '',
  description: '',
  context_type: 'default',
  context: 'global'
})

const isLoading = ref(true)
const isSaving = ref(false)
const error = ref('')

async function loadAsset() {
  isLoading.value = true
  error.value = ''
  
  try {
    const slug = route.params.slug
    const asset = await assetService.getAsset(slug)
    
    formData.value = {
      name: asset.name,
      slug: asset.slug,
      description: asset.description || '',
      context_type: asset.context_type,
      context: asset.context
    }
  } catch (err) {
    console.error('Failed to load asset:', err)
    error.value = 'Failed to load asset. Please try again.'
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  error.value = ''
  isSaving.value = true

  try {
    const slug = route.params.slug
    const updatedAsset = await assetService.updateAsset(slug, formData.value)
    
    // Redirect to detail page
    router.push(`/assets/${updatedAsset.slug}`)
  } catch (err) {
    console.error('Failed to update asset:', err)
    const errorData = err.response?.data
    if (errorData) {
      if (errorData.name) {
        error.value = `Name: ${errorData.name[0]}`
      } else if (errorData.slug) {
        error.value = `Slug: ${errorData.slug[0]}`
      } else {
        error.value = errorData.detail || 'Failed to update asset. Please try again.'
      }
    } else {
      error.value = 'Failed to update asset. Please try again.'
    }
  } finally {
    isSaving.value = false
  }
}

function cancel() {
  router.push(`/assets/${route.params.slug}`)
}

onMounted(() => {
  loadAsset()
})
</script>

<template>
  <div class="p-6">
    <div class="max-w-2xl mx-auto">
      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="text-muted-foreground">Loading asset...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error && !formData.name" class="text-center py-12">
        <div class="text-destructive mb-4">{{ error }}</div>
        <button @click="loadAsset" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
          Retry
        </button>
      </div>

      <!-- Form -->
      <template v-else>
        <!-- Header -->
        <div class="mb-6">
          <h1 class="text-3xl font-bold text-foreground">Edit Config Asset</h1>
          <p class="text-muted-foreground mt-1">Update asset metadata and settings</p>
        </div>

        <form @submit.prevent="handleSubmit" class="bg-card border border-border rounded-lg p-6 space-y-6">
          <!-- Name -->
          <div>
            <label for="name" class="block text-sm font-medium text-foreground mb-2">
              Asset Name <span class="text-destructive">*</span>
            </label>
            <input
              id="name"
              v-model="formData.name"
              type="text"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g., Payment Service Config"
            />
          </div>

          <!-- Slug (Read-only) -->
          <div>
            <label for="slug" class="block text-sm font-medium text-foreground mb-2">
              Slug
            </label>
            <input
              id="slug"
              v-model="formData.slug"
              type="text"
              disabled
              class="w-full px-4 py-2 bg-muted border border-input rounded-lg text-muted-foreground font-mono cursor-not-allowed"
            />
            <p class="text-xs text-muted-foreground mt-1">Slug cannot be changed after creation</p>
          </div>

          <!-- Description -->
          <div>
            <label for="description" class="block text-sm font-medium text-foreground mb-2">
              Description
            </label>
            <textarea
              id="description"
              v-model="formData.description"
              rows="3"
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              placeholder="Describe what this configuration asset is used for..."
            ></textarea>
          </div>

          <!-- Context Type -->
          <div>
            <label for="context_type" class="block text-sm font-medium text-foreground mb-2">
              Context Type
            </label>
            <select
              id="context_type"
              v-model="formData.context_type"
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="default">Default</option>
              <option value="team">Team</option>
              <option value="product">Product</option>
            </select>
          </div>

          <!-- Context -->
          <div>
            <label for="context" class="block text-sm font-medium text-foreground mb-2">
              Context
            </label>
            <input
              id="context"
              v-model="formData.context"
              type="text"
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g., billing, auth, global"
            />
          </div>

          <!-- Error Message -->
          <div v-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-3 text-sm">
            {{ error }}
          </div>

          <!-- Actions -->
          <div class="flex gap-3 pt-4">
            <button
              type="submit"
              :disabled="isSaving"
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {{ isSaving ? 'Saving...' : 'Save Changes' }}
            </button>
            <button
              type="button"
              @click="cancel"
              :disabled="isSaving"
              class="px-4 py-2 bg-background border border-input rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </template>
    </div>
  </div>
</template>
