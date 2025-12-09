<script setup>
</script>

<template>
  <div class="min-h-screen bg-background flex flex-col items-center justify-center p-4">
    <div class="text-center space-y-4">
      <h1 class="text-6xl font-bold text-foreground">404</h1>
      <h2 class="text-2xl font-semibold text-foreground">Page Not Found</h2>
      <p class="text-muted-foreground">The page you're looking for doesn't exist.</p>
      <router-link
        to="/dashboard"
        class="inline-block mt-6 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity font-medium"
      >
        Back to Dashboard
      </router-link>
    </div>
  </div>
</template>
