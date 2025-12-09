<script setup>
import { RouterView } from 'vue-router'
import TopNav from '../components/TopNav.vue'
import Sidebar from '../components/Sidebar.vue'
import ChatBox from '../components/ChatBox.vue'
</script>

<template>
  <div class="min-h-screen bg-background">
    <!-- Top Navigation -->
    <TopNav />

    <div class="flex">
      <!-- Sidebar -->
      <Sidebar />

      <!-- Main Content -->
      <main class="flex-1 ml-64 mt-16 p-6">
        <RouterView />
      </main>
    </div>

    <!-- Chat Component -->
    <ChatBox />
  </div>
</template>
