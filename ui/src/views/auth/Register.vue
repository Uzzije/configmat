<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formData = ref({
  email: '',
  password: '',
  confirmPassword: '',
  first_name: '',
  last_name: '',
  tenant_name: ''
})

const error = ref('')
const isLoading = ref(false)

async function handleRegister() {
  error.value = ''
  
  // Validation
  if (!formData.value.email || !formData.value.password || !formData.value.tenant_name) {
    error.value = 'Please fill in all required fields'
    return
  }

  if (formData.value.password !== formData.value.confirmPassword) {
    error.value = 'Passwords do not match'
    return
  }

  if (formData.value.password.length < 8) {
    error.value = 'Password must be at least 8 characters'
    return
  }

  isLoading.value = true

  try {
    const { confirmPassword, ...registerData } = formData.value
    await authStore.register(registerData)
    
    // Redirect to dashboard after successful registration
    router.push('/dashboard')
  } catch (err) {
    const errorData = err.response?.data
    if (errorData) {
      // Handle field-specific errors
      if (errorData.email) {
        error.value = `Email: ${errorData.email[0]}`
      } else if (errorData.tenant_name) {
        error.value = `Organization: ${errorData.tenant_name[0]}`
      } else {
        error.value = errorData.detail || 'Registration failed. Please try again.'
      }
    } else {
      error.value = 'Registration failed. Please try again.'
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-background flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="bg-card border border-border rounded-xl shadow-lg p-8">
        <!-- Logo/Header -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-primary mb-2">ConfigMat</h1>
          <p class="text-muted-foreground">Create your account</p>
        </div>

        <!-- Registration Form -->
        <form @submit.prevent="handleRegister" class="space-y-4">
          <!-- Organization Name -->
          <div>
            <label for="tenant_name" class="block text-sm font-medium text-foreground mb-2">
              Organization Name <span class="text-destructive">*</span>
            </label>
            <input
              id="tenant_name"
              v-model="formData.tenant_name"
              type="text"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              placeholder="Acme Inc"
            />
          </div>

          <!-- Name Fields -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="first_name" class="block text-sm font-medium text-foreground mb-2">
                First Name
              </label>
              <input
                id="first_name"
                v-model="formData.first_name"
                type="text"
                class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                placeholder="John"
              />
            </div>
            <div>
              <label for="last_name" class="block text-sm font-medium text-foreground mb-2">
                Last Name
              </label>
              <input
                id="last_name"
                v-model="formData.last_name"
                type="text"
                class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                placeholder="Doe"
              />
            </div>
          </div>

          <!-- Email Field -->
          <div>
            <label for="email" class="block text-sm font-medium text-foreground mb-2">
              Email <span class="text-destructive">*</span>
            </label>
            <input
              id="email"
              v-model="formData.email"
              type="email"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>

          <!-- Password Fields -->
          <div>
            <label for="password" class="block text-sm font-medium text-foreground mb-2">
              Password <span class="text-destructive">*</span>
            </label>
            <input
              id="password"
              v-model="formData.password"
              type="password"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              placeholder="••••••••"
            />
            <p class="text-xs text-muted-foreground mt-1">Minimum 8 characters</p>
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-foreground mb-2">
              Confirm Password <span class="text-destructive">*</span>
            </label>
            <input
              id="confirmPassword"
              v-model="formData.confirmPassword"
              type="password"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              placeholder="••••••••"
            />
          </div>

          <!-- Error Message -->
          <div v-if="error" class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-3 text-sm">
            {{ error }}
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="isLoading"
            class="w-full bg-primary text-primary-foreground font-medium py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isLoading ? 'Creating account...' : 'Create Account' }}
          </button>

          <!-- Login Link -->
          <div class="text-center text-sm text-muted-foreground">
            Already have an account? 
            <router-link to="/login" class="text-primary hover:underline">
              Sign in
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
