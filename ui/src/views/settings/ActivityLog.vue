<script setup>
import { ref, onMounted, watch } from 'vue'
import { auditService, teamService } from '../../api/services'

const logs = ref([])
const teamMembers = ref([])
const selectedUser = ref('')
const timeRange = ref('all')
const isLoading = ref(true)
const error = ref('')
const page = ref(1)
const hasNext = ref(false)
const hasPrev = ref(false)

async function loadLogs() {
  isLoading.value = true
  error.value = ''
  
  try {
    const params = {
      page: page.value
    }
    if (selectedUser.value) {
      params.user = selectedUser.value
    }
    
    if (timeRange.value !== 'all') {
      const now = new Date()
      const past = new Date()
      if (timeRange.value === '24h') past.setHours(now.getHours() - 24)
      if (timeRange.value === '7d') past.setDate(now.getDate() - 7)
      if (timeRange.value === '30d') past.setDate(now.getDate() - 30)
      
      params.created_at__gte = past.toISOString()
    }
    
    const response = await auditService.getLogs(params)
    logs.value = response.results || response
    hasNext.value = !!response.next
    hasPrev.value = !!response.previous
  } catch (err) {
    console.error('Failed to load logs:', err)
    error.value = 'Failed to load activity logs.'
  } finally {
    isLoading.value = false
  }
}

async function loadTeam() {
  try {
    const response = await teamService.getMembers()
    teamMembers.value = response.results || response
  } catch (err) {
    console.error('Failed to load team:', err)
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString()
}

function formatDetails(details) {
  if (!details || Object.keys(details).length === 0) return '-'
  return Object.entries(details)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ')
}

watch([selectedUser, timeRange], () => {
  page.value = 1
  loadLogs()
})

onMounted(() => {
  loadLogs()
  loadTeam()
})
</script>

<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-3xl font-bold text-foreground">Activity Log</h1>
        <p class="text-muted-foreground mt-1">Audit trail of user activities</p>
      </div>
      
      <!-- Filter -->
      <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-foreground">Filter by User:</label>
        <select 
          v-model="selectedUser" 
          class="px-3 py-2 bg-background border border-input rounded-lg text-sm min-w-[200px]"
        >
          <option value="">All Users</option>
          <option v-for="member in teamMembers" :key="member.id" :value="member.user.id">
            {{ member.user.first_name }} {{ member.user.last_name }} ({{ member.user.email }})
          </option>
        </select>

        <label class="text-sm font-medium text-foreground ml-4">Time Range:</label>
        <select 
          v-model="timeRange" 
          class="px-3 py-2 bg-background border border-input rounded-lg text-sm min-w-[150px]"
        >
          <option value="all">All Time</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive p-4 rounded-lg mb-6">
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="text-center py-12 text-muted-foreground">
      Loading activities...
    </div>

    <!-- Table -->
    <div v-else class="bg-card border border-border rounded-lg overflow-hidden">
      <table class="w-full">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Time</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">User</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Action</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Target</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Details</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-if="logs.length === 0">
            <td colspan="5" class="px-6 py-12 text-center text-muted-foreground">
              No activities found.
            </td>
          </tr>
          <tr v-for="log in logs" :key="log.id" class="hover:bg-muted/30">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
              {{ formatDate(log.created_at) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
              {{ log.user_name }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-foreground">
              <span class="px-2 py-1 bg-primary/10 text-primary rounded text-xs font-bold">
                {{ log.action }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-foreground">
              {{ log.target || '-' }}
            </td>
            <td class="px-6 py-4 text-sm text-muted-foreground max-w-xs truncate" :title="formatDetails(log.details)">
              {{ formatDetails(log.details) }}
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <div class="px-6 py-4 border-t border-border flex items-center justify-between">
        <button 
          @click="page--; loadLogs()" 
          :disabled="!hasPrev || isLoading"
          class="px-4 py-2 bg-background border border-input rounded-lg disabled:opacity-50"
        >
          Previous
        </button>
        <span class="text-sm text-muted-foreground">Page {{ page }}</span>
        <button 
          @click="page++; loadLogs()" 
          :disabled="!hasNext || isLoading"
          class="px-4 py-2 bg-background border border-input rounded-lg disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>
