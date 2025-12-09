<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { assetService } from '../../api/services'

const router = useRouter()

const formData = ref({
  name: '',
  slug: '',
  description: '',
  context_type: 'default',
  context: 'global'
})

const isLoading = ref(false)
const error = ref('')

// Auto-generate slug from name
function generateSlug() {
  if (!formData.value.slug && formData.value.name) {
    formData.value.slug = formData.value.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }
}

async function handleSubmit() {
  error.value = ''
  
  // Validation
  if (!formData.value.name || !formData.value.slug) {
    error.value = 'Name and slug are required'
    return
  }

  isLoading.value = true

  try {
    const asset = await assetService.createAsset(formData.value)
    router.push(`/assets/${asset.slug}`)
  } catch (err) {
    console.error('Failed to create asset:', err)
    const errorData = err.response?.data
    if (errorData) {
      if (errorData.slug) {
        error.value = `Slug: ${errorData.slug[0]}`
      } else if (errorData.name) {
        error.value = `Name: ${errorData.name[0]}`
      } else {
        error.value = errorData.detail || 'Failed to create asset. Please try again.'
      }
    } else {
      error.value = 'Failed to create asset. Please try again.'
    }
  } finally {
    isLoading.value = false
  }
}

function cancel() {
  router.push('/assets')
}
</script>

<template>
  <div class="p-6">
    <div class="max-w-2xl mx-auto">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-foreground">Create Config Asset</h1>
        <p class="text-muted-foreground mt-1">Define a new configuration asset for your application</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="bg-card border border-border rounded-lg p-6 space-y-6">
        <!-- Name -->
        <div>
          <label for="name" class="block text-sm font-medium text-foreground mb-2">
            Asset Name <span class="text-destructive">*</span>
          </label>
          <input
            id="name"
            v-model="formData.name"
            @blur="generateSlug"
            type="text"
            required
            class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="e.g., Payment Service Config"
          />
          <p class="text-xs text-muted-foreground mt-1">A descriptive name for this configuration asset</p>
        </div>

        <!-- Slug -->
        <div>
          <label for="slug" class="block text-sm font-medium text-foreground mb-2">
            Slug <span class="text-destructive">*</span>
          </label>
          <input
            id="slug"
            v-model="formData.slug"
            type="text"
            required
            pattern="[a-z0-9-]+"
            class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring font-mono"
            placeholder="e.g., payment-service-config"
          />
          <p class="text-xs text-muted-foreground mt-1">URL-friendly identifier (lowercase, hyphens only)</p>
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
          <p class="text-xs text-muted-foreground mt-1">Categorize this asset by its organizational scope</p>
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
          <p class="text-xs text-muted-foreground mt-1">Functional area or domain (e.g., billing, auth)</p>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-3 text-sm">
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-4">
          <button
            type="submit"
            :disabled="isLoading"
            class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {{ isLoading ? 'Creating...' : 'Create Asset' }}
          </button>
          <button
            type="button"
            @click="cancel"
            :disabled="isLoading"
            class="px-4 py-2 bg-background border border-input rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
