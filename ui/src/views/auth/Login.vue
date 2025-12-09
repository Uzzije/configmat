<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)

async function handleLogin() {
  error.value = ''
  
  if (!email.value || !password.value) {
    error.value = 'Please enter both email and password'
    return
  }

  isLoading.value = true

  try {

    await authStore.login(email.value, password.value)
    
    
    // Redirect to intended route or dashboard
    const intendedRoute = localStorage.getItem('intendedRoute')
    localStorage.removeItem('intendedRoute')
    
    const targetRoute = intendedRoute || '/dashboard'
    console.log('Attempting to redirect to:', targetRoute)
    
    await router.push(targetRoute)
    
    console.log('After router.push, current route:', router.currentRoute.value.path)
  } catch (err) {
    console.error('Login error:', err)
    console.error('Error response:', err.response)
    error.value = err.response?.data?.detail || 'Invalid credentials. Please try again.'
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
          <p class="text-muted-foreground">Configuration Management Platform</p>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="space-y-6">
          <!-- Email Field -->
          <div>
            <label for="email" class="block text-sm font-medium text-foreground mb-2">
              Email
            </label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              class="w-full px-4 py-2 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>

          <!-- Password Field -->
          <div>
            <label for="password" class="block text-sm font-medium text-foreground mb-2">
              Password
            </label>
            <input
              id="password"
              v-model="password"
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
            {{ isLoading ? 'Signing in...' : 'Sign In' }}
          </button>

          <!-- Links -->
          <div class="text-center space-y-2">
            <div>
              <router-link to="/forgot-password" class="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Forgot password?
              </router-link>
            </div>
            <div class="text-sm text-muted-foreground">
              Don't have an account? 
              <router-link to="/register" class="text-primary hover:underline">
                Sign up
              </router-link>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
