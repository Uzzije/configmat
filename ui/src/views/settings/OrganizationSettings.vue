<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { organizationService } from '../../api/services'

const authStore = useAuthStore()

const isLoading = ref(true)
const isSaving = ref(false)
const organization = ref(null)

const orgForm = ref({
  name: '',
  slug: ''
})

const contextTypes = ref([])
const newContextType = ref('')
const newContextCategory = ref('')

const environments = ref([])
const newEnvironment = ref({ name: '', slug: '' })

async function loadOrganization() {
  try {
    isLoading.value = true
    
    const [tenantData, contextResponse, envResponse] = await Promise.all([
      organizationService.getTenant(),
      organizationService.getContextTypes(),
      organizationService.getEnvironments()
    ])
    
    if (tenantData) {
      organization.value = tenantData
      orgForm.value = {
        name: organization.value.name,
        slug: organization.value.slug
      }
    }
    
    contextTypes.value = contextResponse.results || contextResponse
    environments.value = envResponse.results || envResponse
    
  } catch (err) {
    console.error('Failed to load organization:', err)
    console.error('Failed to load organization settings')
  } finally {
    isLoading.value = false
  }
}

async function handleUpdateOrg() {
  try {
    isSaving.value = true
    await organizationService.updateTenant({
      name: orgForm.value.name
    })
    console.log('Organization updated successfully!')
    await loadOrganization()
  } catch (err) {
    console.error('Failed to update organization:', err)
    console.error('Failed to update organization')
  } finally {
    isSaving.value = false
  }
}

async function addContextType() {
  if (!newContextType.value || !newContextCategory.value) {
    console.error('Please enter both type and category')
    return
  }
  
  try {
    await organizationService.createContextType({
      type: newContextType.value,
      category: newContextCategory.value
    })
    
    newContextType.value = ''
    newContextCategory.value = ''
    await loadOrganization()
  } catch (err) {
    console.error('Failed to add context type:', err)
    console.error(err.response?.data?.error || 'Failed to add context type')
  }
}

async function removeContextType(id) {
  if (!confirm('Remove this context type?')) return
  
  try {
    await organizationService.deleteContextType(id)
    await loadOrganization()
  } catch (err) {
    console.error('Failed to remove context type:', err)
    const errorMsg = err.response?.data?.error || 'Failed to remove context type'
    console.error(errorMsg)
  }
}

async function addEnvironment() {
  if (!newEnvironment.value.name || !newEnvironment.value.slug) {
    console.error('Please enter both name and slug')
    return
  }
  
  try {
    await organizationService.createEnvironment({
      name: newEnvironment.value.name,
      slug: newEnvironment.value.slug,
      order: environments.value.length
    })
    
    newEnvironment.value = { name: '', slug: '' }
    await loadOrganization()
  } catch (err) {
    console.error('Failed to add environment:', err)
    console.error(err.response?.data?.error || 'Failed to add environment')
  }
}

async function removeEnvironment(id) {
  if (!confirm('Remove this environment? This will affect all assets.')) return
  
  try {
    await organizationService.deleteEnvironment(id)
    await loadOrganization()
  } catch (err) {
    console.error('Failed to remove environment:', err)
    const errorMsg = err.response?.data?.error || 'Failed to remove environment'
    console.error(errorMsg)
  }
}

async function moveEnvironment(index, direction) {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= environments.value.length) return
  
  const temp = environments.value[index]
  environments.value[index] = environments.value[newIndex]
  environments.value[newIndex] = temp
  
  // Update order and save
  try {
    const order = environments.value.map(env => env.id)
    await organizationService.reorderEnvironments(order)
    await loadOrganization()
  } catch (err) {
    console.error('Failed to reorder environments:', err)
    console.error('Failed to reorder environments')
  }
}

onMounted(() => {
  loadOrganization()
})
</script>

<template>
  <div class="min-h-screen bg-background">
    <div class="max-w-4xl mx-auto p-6">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-foreground">Organization Settings</h1>
        <p class="text-muted-foreground mt-2">Manage your organization configuration</p>
      </div>

      <div v-if="isLoading" class="text-center py-12">
        <p class="text-muted-foreground">Loading...</p>
      </div>

      <div v-else class="space-y-6">
        <!-- Organization Details -->
        <div class="bg-card border border-border rounded-lg p-6">
          <h2 class="text-xl font-semibold text-foreground mb-4">Organization Details</h2>
          
          <form @submit.prevent="handleUpdateOrg" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">Organization Name</label>
              <input
                v-model="orgForm.name"
                type="text"
                required
                class="w-full px-4 py-2 bg-background border border-input rounded-lg"
                placeholder="My Organization"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-foreground mb-2">Slug</label>
              <input
                v-model="orgForm.slug"
                type="text"
                required
                disabled
                class="w-full px-4 py-2 bg-muted border border-input rounded-lg text-muted-foreground cursor-not-allowed"
                placeholder="my-org"
              />
              <p class="text-xs text-muted-foreground mt-1">Slug cannot be changed after creation</p>
            </div>

            <button
              type="submit"
              :disabled="isSaving"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {{ isSaving ? 'Saving...' : 'Save Changes' }}
            </button>
          </form>
        </div>

        <!-- Context Types -->
        <div class="bg-card border border-border rounded-lg p-6">
          <h2 class="text-xl font-semibold text-foreground mb-4">Context Types</h2>
          <p class="text-sm text-muted-foreground mb-4">
            Define context types for organizing your configuration assets
          </p>

          <div class="space-y-2 mb-4">
            <div
              v-for="ct in contextTypes"
              :key="ct.id"
              class="flex items-center justify-between p-3 bg-muted/30 border border-border rounded-lg"
            >
              <div>
                <span class="font-medium text-foreground">{{ ct.type }}</span>
                <span class="text-sm text-muted-foreground ml-2">→ {{ ct.category }}</span>
              </div>
              <button
                @click="removeContextType(ct.id)"
                class="text-destructive hover:underline text-sm"
              >
                Remove
              </button>
            </div>
          </div>

          <div class="flex gap-2">
            <select
              v-model="newContextType"
              class="flex-1 px-4 py-2 bg-background border border-input rounded-lg"
            >
              <option value="" disabled>Select Type</option>
              <option value="product">Product</option>
              <option value="team">Team</option>
            </select>
            <input
              v-model="newContextCategory"
              type="text"
              placeholder="Name (e.g., Mobile App, Backend Team)"
              class="flex-1 px-4 py-2 bg-background border border-input rounded-lg"
            />
            <button
              @click="addContextType"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
            >
              Add
            </button>
          </div>
        </div>

        <!-- Environments -->
        <div class="bg-card border border-border rounded-lg p-6">
          <h2 class="text-xl font-semibold text-foreground mb-4">Environments</h2>
          <p class="text-sm text-muted-foreground mb-4">
            Manage deployment environments for your configurations
          </p>

          <div class="space-y-2 mb-4">
            <div
              v-for="(env, index) in environments"
              :key="env.id"
              class="flex items-center justify-between p-3 bg-muted/30 border border-border rounded-lg"
            >
              <div class="flex items-center gap-3">
                <div class="flex flex-col gap-1">
                  <button
                    @click="moveEnvironment(index, 'up')"
                    :disabled="index === 0"
                    class="text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    ▲
                  </button>
                  <button
                    @click="moveEnvironment(index, 'down')"
                    :disabled="index === environments.length - 1"
                    class="text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    ▼
                  </button>
                </div>
                <div>
                  <span class="font-medium text-foreground">{{ env.name }}</span>
                  <span class="text-sm text-muted-foreground ml-2">({{ env.slug }})</span>
                </div>
              </div>
              <button
                @click="removeEnvironment(env.id)"
                class="text-destructive hover:underline text-sm"
              >
                Remove
              </button>
            </div>
          </div>

          <div class="flex gap-2">
            <input
              v-model="newEnvironment.name"
              type="text"
              placeholder="Name (e.g., Development)"
              class="flex-1 px-4 py-2 bg-background border border-input rounded-lg"
            />
            <input
              v-model="newEnvironment.slug"
              type="text"
              placeholder="Slug (e.g., dev)"
              class="flex-1 px-4 py-2 bg-background border border-input rounded-lg"
            />
            <button
              @click="addEnvironment"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
            >
              Add
            </button>
          </div>
          
          <p class="text-xs text-yellow-600 mt-3">
            ⚠️ Note: Changing environments will affect all existing assets. Use with caution.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
