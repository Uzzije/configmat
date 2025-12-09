<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import api from '../api/client'

const isOpen = ref(false)
const messages = ref([])
const newMessage = ref('')
const isLoading = ref(false)
const unreadCount = ref(0)
let pollInterval = null

async function loadMessages() {
  try {
    const response = await api.get('/chat/messages/')
    // If pagination, use results. If list, use data.
    const newMessages = response.data.results || response.data
    
    // Only scroll if new message added? Or always?
    // Simple check: if length changed.
    if (newMessages.length !== messages.value.length) {
        messages.value = newMessages
        scrollToBottom()
    } else {
        messages.value = newMessages
    }
  } catch (err) {
    console.error('Failed to load messages:', err)
  }
}

async function sendMessage() {
  if (!newMessage.value.trim()) return
  
  const text = newMessage.value
  newMessage.value = '' // Optimistic clear
  
  try {
    const response = await api.post('/chat/messages/', { message: text })
    messages.value.push(response.data)
    scrollToBottom()
  } catch (err) {
    console.error('Failed to send message:', err)
  }
}

async function checkUnread() {
  try {
    const response = await api.get('/chat/messages/unread_count/')
    unreadCount.value = response.data.count
  } catch (err) {
    console.error('Failed to check unread:', err)
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = document.getElementById('chat-messages')
    if (el) el.scrollTop = el.scrollHeight
  })
}

function toggleChat() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    loadMessages()
    api.post('/chat/messages/mark_read/').then(() => {
        unreadCount.value = 0
    })
  }
}

onMounted(() => {
  checkUnread()
  pollInterval = setInterval(() => {
    if (isOpen.value) {
      loadMessages()
      // Also mark read if open?
      api.post('/chat/messages/mark_read/').then(() => {
          unreadCount.value = 0
      })
    } else {
      checkUnread()
    }
  }, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="fixed bottom-6 right-6 z-50 flex flex-col items-end">
    <!-- Chat Window -->
    <div 
      v-if="isOpen" 
      class="mb-4 w-80 h-96 bg-card border border-border rounded-lg shadow-xl flex flex-col overflow-hidden"
    >
      <!-- Header -->
      <div class="p-3 bg-primary text-primary-foreground flex justify-between items-center">
        <h3 class="font-bold">Support Chat</h3>
        <button @click="isOpen = false" class="hover:opacity-80">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>
      
      <!-- Messages -->
      <div id="chat-messages" class="flex-1 p-4 overflow-y-auto space-y-3 bg-background">
        <div 
          v-for="msg in messages" 
          :key="msg.id" 
          class="flex flex-col"
          :class="msg.is_from_admin ? 'items-start' : 'items-end'"
        >
          <div 
            class="max-w-[80%] px-3 py-2 rounded-lg text-sm"
            :class="msg.is_from_admin ? 'bg-muted text-foreground' : 'bg-primary text-primary-foreground'"
          >
            {{ msg.message }}
          </div>
          <span class="text-[10px] text-muted-foreground mt-1">
            {{ new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }}
          </span>
        </div>
        <div v-if="messages.length === 0" class="text-center text-muted-foreground text-sm mt-4">
          No messages yet. Ask us anything!
        </div>
      </div>
      
      <!-- Input -->
      <div class="p-3 border-t border-border bg-card">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input 
            v-model="newMessage" 
            type="text" 
            placeholder="Type a message..." 
            class="flex-1 px-3 py-2 bg-background border border-input rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button 
            type="submit" 
            class="p-2 bg-primary text-primary-foreground rounded hover:opacity-90 disabled:opacity-50"
            :disabled="!newMessage.trim()"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </form>
      </div>
    </div>

    <!-- Toggle Button -->
    <button
      @click="toggleChat"
      class="w-14 h-14 bg-primary text-primary-foreground rounded-full shadow-lg flex items-center justify-center hover:bg-primary/90 transition-colors relative"
      title="Contact Support"
    >
      <svg v-if="!isOpen" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      
      <!-- Badge -->
      <span 
        v-if="unreadCount > 0 && !isOpen" 
        class="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground text-xs font-bold rounded-full flex items-center justify-center border-2 border-background"
      >
        {{ unreadCount }}
      </span>
    </button>
  </div>
</template>
