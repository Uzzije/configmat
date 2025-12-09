<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/client'
import { userService } from '../../api/services'

const authStore = useAuthStore()

const formData = ref({
  first_name: '',
  last_name: '',
  email: ''
})

const isLoading = ref(true)
const isSaving = ref(false)
const error = ref('')
const successMessage = ref('')

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordMessage = ref({ type: '', text: '' })
const isChangingPassword = ref(false)

async function handleChangePassword() {
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordMessage.value = { type: 'error', text: 'New passwords do not match.' }
    return
  }

  isChangingPassword.value = true
  passwordMessage.value = { type: '', text: '' }

  try {
    await userService.changePassword(
      passwordForm.value.oldPassword,
      passwordForm.value.newPassword
    )
    passwordMessage.value = { type: 'success', text: 'Password updated successfully.' }
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } catch (err) {
    console.error('Failed to change password:', err)
    const errorMsg = err.response?.data?.old_password?.[0] || 
                     err.response?.data?.detail || 
                     'Failed to update password.'
    passwordMessage.value = { type: 'error', text: errorMsg }
  } finally {
    isChangingPassword.value = false
  }
}

async function loadProfile() {
  isLoading.value = true
  error.value = ''
  
  try {
    const response = await api.get('/auth/me/')
    const user = response.data
    
    formData.value = {
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      email: user.email
    }
  } catch (err) {
    console.error('Failed to load profile:', err)
    error.value = 'Failed to load profile. Please try again.'
  } finally {
    isLoading.value = false
  }
}

async function handleSave() {
  error.value = ''
  successMessage.value = ''
  isSaving.value = true

  try {
    const response = await api.patch('/auth/me/', {
      first_name: formData.value.first_name,
      last_name: formData.value.last_name
    })
    
    // Update local user data
    const updatedUser = response.data
    localStorage.setItem('user', JSON.stringify(updatedUser))
    authStore.user = updatedUser
    
    successMessage.value = 'Profile updated successfully!'
    
    // Clear success message after 3 seconds
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (err) {
    console.error('Failed to update profile:', err)
    error.value = err.response?.data?.detail || 'Failed to update profile. Please try again.'
  } finally {
    isSaving.value = false
  }
}

function handleCancel() {
  loadProfile()
}

onMounted(() => {
  loadProfile()
})
</script>

<template>
  <div class="p-6">
    <div class="max-w-2xl mx-auto">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-foreground">Profile Settings</h1>
        <p class="text-muted-foreground mt-1">Manage your account information</p>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="bg-card border border-border rounded-lg p-12 text-center">
        <div class="text-muted-foreground">Loading profile...</div>
      </div>

      <!-- Form -->
      <form v-else @submit.prevent="handleSave" class="bg-card border border-border rounded-lg p-6 space-y-6">
        <!-- Organization Info (Read-only) -->
        <div class="pb-6 border-b border-border">
          <h2 class="text-lg font-semibold text-foreground mb-4">Organization</h2>
          <div class="bg-muted/30 rounded-lg p-4">
            <div class="text-sm text-muted-foreground mb-1">Organization Name</div>
            <div class="font-medium text-foreground">{{ authStore.user?.tenant?.name || 'N/A' }}</div>
          </div>
        </div>

        <!-- Personal Info -->
        <div>
          <h2 class="text-lg font-semibold text-foreground mb-4">Personal Information</h2>
          
          <div class="space-y-4">
            <!-- First Name -->
            <div>
              <label for="first_name" class="block text-sm font-medium text-foreground mb-2">
                First Name
              </label>
              <input
                id="first_name"
                v-model="formData.first_name"
                type="text"
                class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="John"
              />
            </div>

            <!-- Last Name -->
            <div>
              <label for="last_name" class="block text-sm font-medium text-foreground mb-2">
                Last Name
              </label>
              <input
                id="last_name"
                v-model="formData.last_name"
                type="text"
                class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Doe"
              />
            </div>

            <!-- Email (Read-only) -->
            <div>
              <label for="email" class="block text-sm font-medium text-foreground mb-2">
                Email
              </label>
              <input
                id="email"
                v-model="formData.email"
                type="email"
                disabled
                class="w-full px-4 py-2 bg-muted border border-input rounded-lg text-muted-foreground cursor-not-allowed"
              />
              <p class="text-xs text-muted-foreground mt-1">Email cannot be changed</p>
            </div>
          </div>
        </div>

        <!-- Success Message -->
        <div v-if="successMessage" class="bg-green-500/10 border border-green-500/20 text-green-600 rounded-lg p-3 text-sm">
          {{ successMessage }}
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
            class="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {{ isSaving ? 'Saving...' : 'Save Changes' }}
          </button>
          <button
            type="button"
            @click="handleCancel"
            :disabled="isSaving"
            class="px-6 py-2 bg-background border border-input rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>

    <!-- Change Password Section -->
    <div class="max-w-2xl mx-auto mt-8">
      <div class="bg-card border border-border rounded-lg p-6">
        <h2 class="text-lg font-semibold text-foreground mb-4">Change Password</h2>
        
        <div v-if="passwordMessage.text" :class="[
          'p-4 rounded-lg mb-6 text-sm',
          passwordMessage.type === 'success' ? 'bg-green-500/10 text-green-600 border border-green-500/20' : 'bg-destructive/10 text-destructive border border-destructive/20'
        ]">
          {{ passwordMessage.text }}
        </div>

        <form @submit.prevent="handleChangePassword" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Current Password</label>
            <input
              v-model="passwordForm.oldPassword"
              type="password"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">New Password</label>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-2">Confirm New Password</label>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          
          <div class="pt-2">
            <button
              type="submit"
              :disabled="isChangingPassword"
              class="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {{ isChangingPassword ? 'Updating...' : 'Update Password' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
