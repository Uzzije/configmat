<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import { organizationService } from '../api/services'

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref(false)
const showTenantMenu = ref(false)
const tenants = ref([])
const currentTenant = ref(null)

async function loadTenants() {
  if (authStore.isAuthenticated && authStore.user) {
    // Initialize from store immediately
    if (authStore.user.current_tenant) {
      currentTenant.value = authStore.user.current_tenant
    }

    try {
      tenants.value = await organizationService.getMyTenants()
      // Fetch fresh tenant data if needed, or update existing
      const freshTenant = await organizationService.getTenant()
      if (freshTenant) {
        currentTenant.value = freshTenant
      }
    } catch (e) {
      console.error('Failed to load tenants', e)
      // Don't clear currentTenant if we have it from store
      if (!currentTenant.value) {
        currentTenant.value = null
      }
      tenants.value = []
    }
  } else {
    tenants.value = []
    currentTenant.value = null
  }
}

async function handleSwitchTenant(tenant) {
  if (tenant.id === currentTenant.value?.id) {
    showTenantMenu.value = false
    return
  }
  try {
    await organizationService.switchTenant(tenant.id)
    currentTenant.value = tenant
    showTenantMenu.value = false
    
    // Update authStore and localStorage to persist the switch across reload
    if (authStore.user) {
      const updatedUser = { ...authStore.user, current_tenant: tenant }
      authStore.user = updatedUser
      localStorage.setItem('user', JSON.stringify(updatedUser))
    }
    
    // Redirect to dashboard to ensure clean state and avoid stale data on current page
    router.push('/dashboard')
  } catch (e) {
    console.error('Failed to switch tenant', e)
  }
}

// Watch for authentication state changes
watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth && authStore.user) {
    loadTenants()
  } else {
    tenants.value = []
    currentTenant.value = null
  }
}, { immediate: true })

onMounted(() => {
  // Ensure tenants are loaded if already authenticated
  if (authStore.isAuthenticated && authStore.user) {
    loadTenants()
  }
})

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

function navigateToProfile() {
  router.push('/settings/profile')
  showUserMenu.value = false
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

const searchQuery = ref('')

function handleSearch() {
  if (!searchQuery.value.trim()) return
  router.push({ path: '/assets', query: { search: searchQuery.value } })
}
</script>

<template>
  <nav class="fixed top-0 left-0 right-0 h-16 bg-card border-b border-border z-50">
    <div class="flex items-center justify-between h-full px-4">
      <!-- Left Section: Logo and Workspace -->
      <div class="flex items-center space-x-4">
        <h1 class="text-xl font-bold text-primary cursor-pointer" @click="router.push('/')">ConfigMat</h1>
        
        <!-- Tenant Switcher -->
        <div class="relative" v-if="currentTenant">
            <button @click="showTenantMenu = !showTenantMenu" class="flex items-center space-x-2 px-2 py-1 rounded hover:bg-accent text-sm font-medium transition-colors border border-transparent hover:border-border">
                <span>{{ currentTenant.name }}</span>
                <svg class="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            
            <div v-if="showTenantMenu" class="absolute top-full left-0 mt-1 w-56 bg-card border border-border rounded-lg shadow-lg py-1 z-50">
                <div class="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Organizations</div>
                <button 
                    v-for="tenant in tenants" 
                    :key="tenant.id"
                    @click="handleSwitchTenant(tenant)"
                    class="w-full text-left px-4 py-2 text-sm hover:bg-accent transition-colors flex justify-between items-center"
                    :class="{'text-primary font-medium bg-accent/50': tenant.id === currentTenant.id}"
                >
                    <span class="truncate">{{ tenant.name }}</span>
                    <svg v-if="tenant.id === currentTenant.id" class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                </button>
            </div>
        </div>
      </div>

      <!-- Center: Global Search -->
      <div class="flex-1 max-w-2xl mx-8 flex items-center gap-2">
        <div class="relative flex-1">
          <input
            v-model="searchQuery"
            @keyup.enter="handleSearch"
            type="text"
            placeholder="Search assets..."
            class="w-full px-4 py-2 pl-10 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <svg
            class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <button 
            @click="router.push('/help')" 
            class="p-2 text-muted-foreground hover:text-foreground rounded-full hover:bg-accent transition-colors" 
            title="Help"
        >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>
        </button>
      </div>

      <!-- Right Section: User Menu -->
      <div class="relative">
        <button
          @click="toggleUserMenu"
          class="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-accent transition-colors"
        >
          <div class="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium">
            {{ (authStore.user?.first_name?.[0] || authStore.user?.email?.[0] || 'U').toUpperCase() }}
          </div>
          <span class="text-sm font-medium text-foreground">{{ authStore.user?.first_name || authStore.user?.email || 'User' }}</span>
          <svg class="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- User Dropdown Menu -->
        <div
          v-if="showUserMenu"
          class="absolute right-0 mt-2 w-48 bg-card border border-border rounded-lg shadow-lg py-1"
        >
          <button
            @click="navigateToProfile"
            class="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-accent transition-colors"
          >
            Profile
          </button>
          <button
            @click="handleLogout"
            class="w-full text-left px-4 py-2 text-sm text-destructive hover:bg-accent transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
