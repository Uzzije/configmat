<script setup>
import { ref, onMounted } from 'vue'
import { teamService } from '../../api/services'

const activeTab = ref(0)
const members = ref([])
const invitations = ref([])
const isLoading = ref(true)
const error = ref('')

// Invite modal
const showInviteModal = ref(false)
const inviteForm = ref({
  email: '',
  role: 'user'
})
const inviteError = ref('')
const isSending = ref(false)

async function loadMembers() {
  try {
    const response = await teamService.getMembers()
    members.value = response.results || response
  } catch (err) {
    console.error('Failed to load members:', err)
    error.value = 'Failed to load team members'
  }
}

async function loadInvitations() {
  try {
    const response = await teamService.getInvitations()
    invitations.value = response.results || response
  } catch (err) {
    console.error('Failed to load invitations:', err)
  }
}

async function loadData() {
  isLoading.value = true
  error.value = ''
  await Promise.all([loadMembers(), loadInvitations()])
  isLoading.value = false
}

async function handleInvite() {
  inviteError.value = ''
  isSending.value = true

  try {
    await teamService.createInvitation(inviteForm.value.email, inviteForm.value.role)
    
    // Reset form
    inviteForm.value = { email: '', role: 'user' }
    showInviteModal.value = false
    
    // Reload invitations
    await loadInvitations()
  } catch (err) {
    console.error('Failed to send invitation:', err)
    inviteError.value = err.response?.data?.error || 'Failed to send invitation'
  } finally {
    isSending.value = false
  }
}

async function handleUpdateRole(member, newRole) {
  if (!confirm(`Change ${member.user.email}'s role to ${newRole}?`)) {
    return
  }

  try {
    await teamService.updateMemberRole(member.id, newRole)
    await loadMembers()
  } catch (err) {
    console.error('Failed to update role:', err)
    alert(err.response?.data?.error || 'Failed to update role')
  }
}

async function handleRemoveMember(member) {
  if (!confirm(`Remove ${member.user.first_name} ${member.user.last_name} (${member.user.email}) from the organization?`)) {
    return
  }

  try {
    await teamService.removeMember(member.id)
    await loadMembers()
  } catch (err) {
    console.error('Failed to remove member:', err)
    alert(err.response?.data?.error || 'Failed to remove member')
  }
}

async function handleRevokeInvite(invitation) {
  if (!confirm(`Revoke invitation for ${invitation.email}?`)) {
    return
  }

  try {
    await teamService.revokeInvitation(invitation.id)
    await loadInvitations()
  } catch (err) {
    console.error('Failed to revoke invitation:', err)
    alert('Failed to revoke invitation')
  }
}

async function handleResendInvite(invitation) {
  try {
    await teamService.resendInvitation(invitation.id)
    alert('Invitation resent successfully')
  } catch (err) {
    console.error('Failed to resend invitation:', err)
    alert('Failed to resend invitation')
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-foreground">Team Management</h1>
        <p class="text-muted-foreground mt-1">Manage team members and invitations</p>
      </div>
      <button 
        @click="showInviteModal = true"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 font-medium"
      >
        + Invite Member
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-12">
      <div class="text-muted-foreground">Loading team data...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4">
      {{ error }}
    </div>

    <!-- Content -->
    <div v-else class="bg-card border border-border rounded-lg">
      <!-- Tabs -->
      <div class="border-b border-border flex">
        <button
          @click="activeTab = 0"
          :class="[
            'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === 0
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          ]"
        >
          Members ({{ members.length }})
        </button>
        <button
          @click="activeTab = 1"
          :class="[
            'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === 1
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          ]"
        >
          Pending Invitations ({{ invitations.filter(i => i.status === 'pending').length }})
        </button>
      </div>

      <!-- Members Tab -->
      <div v-show="activeTab === 0" class="p-6">
        <div v-if="members.length === 0" class="text-center py-8 text-muted-foreground">
          No team members yet
        </div>
        <div v-else class="space-y-4">
          <div 
            v-for="member in members" 
            :key="member.id"
            class="flex items-center justify-between p-4 bg-background border border-border rounded-lg"
          >
            <div class="flex-1">
              <div class="font-medium text-foreground">
                {{ member.user.first_name }} {{ member.user.last_name }}
              </div>
              <div class="text-sm text-muted-foreground">{{ member.user.email }}</div>
              <div class="text-xs text-muted-foreground mt-1">
                Joined {{ formatDate(member.joined_at) }}
              </div>
            </div>
            <div class="flex items-center gap-3">
              <select
                :value="member.role"
                @change="handleUpdateRole(member, $event.target.value)"
                class="px-3 py-1.5 bg-background border border-input rounded text-sm"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <button
                @click="handleRemoveMember(member)"
                class="px-3 py-1.5 bg-destructive/10 text-destructive rounded text-sm hover:bg-destructive/20"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Invitations Tab -->
      <div v-show="activeTab === 1" class="p-6">
        <div v-if="invitations.filter(i => i.status === 'pending').length === 0" class="text-center py-8 text-muted-foreground">
          No pending invitations
        </div>
        <div v-else class="space-y-4">
          <div 
            v-for="invitation in invitations.filter(i => i.status === 'pending')" 
            :key="invitation.id"
            class="flex items-center justify-between p-4 bg-background border border-border rounded-lg"
          >
            <div class="flex-1">
              <div class="font-medium text-foreground">{{ invitation.email }}</div>
              <div class="text-sm text-muted-foreground">
                Role: {{ invitation.role }} • Invited by {{ invitation.invited_by.first_name }} {{ invitation.invited_by.last_name }}
              </div>
              <div class="text-xs text-muted-foreground mt-1">
                Expires {{ formatDate(invitation.expires_at) }}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="handleResendInvite(invitation)"
                class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm hover:opacity-90"
              >
                Resend
              </button>
              <button
                @click="handleRevokeInvite(invitation)"
                class="px-3 py-1.5 bg-destructive/10 text-destructive rounded text-sm hover:bg-destructive/20"
              >
                Revoke
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Invite Modal -->
    <div v-if="showInviteModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showInviteModal = false">
      <div class="bg-card border border-border rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold text-foreground mb-4">Invite Team Member</h2>
        <form @submit.prevent="handleInvite" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Email Address *</label>
            <input
              v-model="inviteForm.email"
              type="email"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg"
              placeholder="colleague@example.com"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Role</label>
            <select v-model="inviteForm.role" class="w-full px-4 py-2 bg-background border border-input rounded-lg">
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div v-if="inviteError" class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-3 text-sm">
            {{ inviteError }}
          </div>

          <div class="flex gap-2 pt-2">
            <button 
              type="submit" 
              :disabled="isSending"
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50"
            >
              {{ isSending ? 'Sending...' : 'Send Invitation' }}
            </button>
            <button 
              type="button" 
              @click="showInviteModal = false"
              :disabled="isSending"
              class="px-4 py-2 bg-background border border-input rounded-lg disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
