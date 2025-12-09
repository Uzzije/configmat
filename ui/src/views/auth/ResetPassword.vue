<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../../api/client'

const router = useRouter()
const route = useRoute()

const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref('')
const success = ref(false)

const uid = route.query.uid
const token = route.query.token

onMounted(() => {
  if (!uid || !token) {
    error.value = 'Invalid password reset link.'
  }
})

async function handleSubmit() {
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match.'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    await api.post('/auth/password-reset/confirm/', {
      uidb64: uid,
      token: token,
      password: password.value
    })
    success.value = true
    setTimeout(() => {
      router.push('/login')
    }, 3000)
  } catch (err) {
    console.error('Password reset failed:', err)
    error.value = err.response?.data?.error || 'Failed to reset password. The link may be invalid or expired.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background px-4">
    <div class="max-w-md w-full space-y-8 bg-card p-8 rounded-lg border border-border">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-foreground">
          Set New Password
        </h2>
      </div>

      <div v-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded relative">
        {{ error }}
      </div>

      <div v-if="success" class="bg-green-500/10 border border-green-500/20 text-green-600 px-4 py-3 rounded relative">
        Password reset successfully! Redirecting to login...
      </div>

      <form v-if="!success && !error.includes('Invalid password reset link')" class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <div>
            <label for="password" class="sr-only">New Password</label>
            <input
              id="password"
              v-model="password"
              name="password"
              type="password"
              required
              class="appearance-none rounded-lg relative block w-full px-3 py-2 border border-input bg-background placeholder-muted-foreground text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm"
              placeholder="New Password"
            />
          </div>
          <div>
            <label for="confirm-password" class="sr-only">Confirm Password</label>
            <input
              id="confirm-password"
              v-model="confirmPassword"
              name="confirm-password"
              type="password"
              required
              class="appearance-none rounded-lg relative block w-full px-3 py-2 border border-input bg-background placeholder-muted-foreground text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm"
              placeholder="Confirm New Password"
            />
          </div>
        </div>

        <div>
          <button
            type="submit"
            :disabled="isLoading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-lg text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
          >
            {{ isLoading ? 'Resetting...' : 'Reset Password' }}
          </button>
        </div>
      </form>
      
      <div v-if="error.includes('Invalid password reset link')" class="text-center">
        <router-link to="/forgot-password" class="font-medium text-primary hover:text-primary/90">
          Request a new link
        </router-link>
      </div>
    </div>
  </div>
</template>
