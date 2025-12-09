<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'

const router = useRouter()
const email = ref('')
const isLoading = ref(false)
const error = ref('')
const successMessage = ref('')
const mockLink = ref('')

async function handleSubmit() {
  isLoading.value = true
  error.value = ''
  successMessage.value = ''

  try {
    const response = await api.post('/auth/password-reset/', {
      email: email.value
    })
    successMessage.value = 'If an account exists with this email, you will receive a password reset link.'
    
    if (response.data?.mock_link) {
      mockLink.value = response.data.mock_link
    }
    
    email.value = ''
  } catch (err) {
    console.error('Password reset request failed:', err)
    error.value = 'Failed to request password reset. Please try again.'
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
          Reset Password
        </h2>
        <p class="mt-2 text-center text-sm text-muted-foreground">
          Enter your email address and we'll send you a link to reset your password.
        </p>
      </div>

      <div v-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded relative">
        {{ error }}
      </div>

      <div v-if="successMessage" class="bg-green-500/10 border border-green-500/20 text-green-600 px-4 py-3 rounded relative">
        {{ successMessage }}
      </div>

      <div v-if="mockLink" class="bg-blue-500/10 border border-blue-500/20 text-blue-600 px-4 py-3 rounded relative mt-4 break-all">
        <p class="font-bold text-xs uppercase mb-1">Dev Mode: Mock Link</p>
        <a :href="mockLink" class="underline">{{ mockLink }}</a>
      </div>

      <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div>
          <label for="email" class="sr-only">Email address</label>
          <input
            id="email"
            v-model="email"
            name="email"
            type="email"
            required
            class="appearance-none rounded-lg relative block w-full px-3 py-2 border border-input bg-background placeholder-muted-foreground text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm"
            placeholder="Email address"
          />
        </div>

        <div>
          <button
            type="submit"
            :disabled="isLoading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-lg text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
          >
            {{ isLoading ? 'Sending...' : 'Send Reset Link' }}
          </button>
        </div>

        <div class="text-center">
          <router-link to="/login" class="font-medium text-primary hover:text-primary/90">
            Back to Login
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>
