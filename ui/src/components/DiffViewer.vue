<script setup>
import { computed } from 'vue'
import { diffLines, diffJson } from 'diff'

const props = defineProps({
  oldValue: {
    type: [Object, String, Number, Boolean, Array, null],
    default: null
  },
  newValue: {
    type: [Object, String, Number, Boolean, Array, null],
    default: null
  },
  mode: {
    type: String,
    default: 'visual', // 'visual' | 'code'
    validator: (value) => ['visual', 'code'].includes(value)
  },
  title: {
    type: String,
    default: 'Changes'
  }
})

// === VISUAL MODE LOGIC (for KV Objects) ===
const visualDiff = computed(() => {
  if (props.mode !== 'visual') return null

  // Normalize inputs to objects
  const oldObj = props.oldValue && typeof props.oldValue === 'object' ? props.oldValue : {}
  const newObj = props.newValue && typeof props.newValue === 'object' ? props.newValue : {}

  const allKeys = new Set([...Object.keys(oldObj), ...Object.keys(newObj)])
  const changes = []

  allKeys.forEach(key => {
    const oldVal = oldObj[key]
    const newVal = newObj[key]

    // Added
    if (oldVal === undefined && newVal !== undefined) {
      changes.push({ key, type: 'added', value: newVal })
    }
    // Removed
    else if (oldVal !== undefined && newVal === undefined) {
      changes.push({ key, type: 'removed', value: oldVal })
    }
    // Modified
    else if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
      changes.push({ key, type: 'modified', oldValue: oldVal, newValue: newVal })
    }
    // Unchanged (ignored in visual mode usually, but could be added if needed)
  })

  // Sort by key
  return changes.sort((a, b) => a.key.localeCompare(b.key))
})

// === CODE MODE LOGIC (for JSON/YAML Blobs) ===
const codeDiff = computed(() => {
  if (props.mode !== 'code') return []

  const oldText = typeof props.oldValue === 'string' ? props.oldValue : JSON.stringify(props.oldValue, null, 2)
  const newText = typeof props.newValue === 'string' ? props.newValue : JSON.stringify(props.newValue, null, 2)

  // Use 'diff' library
  return diffLines(oldText || '', newText || '')
})

const additionsCount = computed(() => {
  if (props.mode === 'visual') return visualDiff.value.filter(c => c.type === 'added').length
  return codeDiff.value.filter(part => part.added).length // Rough line count
})

const deletionsCount = computed(() => {
  if (props.mode === 'visual') return visualDiff.value.filter(c => c.type === 'removed').length
  return codeDiff.value.filter(part => part.removed).length
})

const modificationsCount = computed(() => {
  if (props.mode === 'visual') return visualDiff.value.filter(c => c.type === 'modified').length
  return 0 // Code diffs don't explicitly track "modified", just add/remove lines
})
</script>

<template>
  <div class="border border-border rounded-lg overflow-hidden bg-white/50 dark:bg-black/20">
    <!-- Header Summary -->
    <div class="px-4 py-3 bg-muted/30 border-b border-border flex justify-between items-center">
      <div class="font-medium text-sm text-foreground">{{ title }}</div>
      <div class="flex gap-3 text-xs font-mono">
        <span v-if="additionsCount > 0" class="text-green-600 font-bold bg-green-500/10 px-2 py-0.5 rounded">
          +{{ additionsCount }} types
        </span>
        <span v-if="deletionsCount > 0" class="text-red-600 font-bold bg-red-500/10 px-2 py-0.5 rounded">
          -{{ deletionsCount }} types
        </span>
        <span v-if="modificationsCount > 0" class="text-yellow-600 font-bold bg-yellow-500/10 px-2 py-0.5 rounded">
          ~{{ modificationsCount }} changed
        </span>
        <span v-if="additionsCount === 0 && deletionsCount === 0 && modificationsCount === 0" class="text-muted-foreground">
          No changes
        </span>
      </div>
    </div>

    <!-- Visual Mode (Table) -->
    <div v-if="mode === 'visual'" class="divide-y divide-border">
      <div v-if="visualDiff.length === 0" class="p-8 text-center text-muted-foreground text-sm">
        Values are identical.
      </div>
      
      <div v-for="change in visualDiff" :key="change.key" class="grid grid-cols-12 text-sm font-mono">
        <!-- Key Column -->
        <div class="col-span-4 p-3 border-r border-border truncate font-semibold" 
             :class="{
               'bg-green-500/5 text-green-700': change.type === 'added',
               'bg-red-500/5 text-red-700 decoration-line-through': change.type === 'removed',
               'bg-yellow-500/5 text-yellow-700': change.type === 'modified'
             }">
          {{ change.key }}
        </div>

        <!-- Value Column -->
        <div class="col-span-8 p-3 flex items-center gap-3">
          <!-- Added -->
          <template v-if="change.type === 'added'">
            <span class="text-green-700 bg-green-500/10 px-1.5 py-0.5 rounded">{{ change.value }}</span>
          </template>

          <!-- Removed -->
          <template v-if="change.type === 'removed'">
            <span class="text-red-700 bg-red-500/10 px-1.5 py-0.5 rounded decoration-line-through">{{ change.value }}</span>
          </template>

          <!-- Modified -->
          <template v-if="change.type === 'modified'">
            <span class="text-red-700 bg-red-500/10 px-1.5 py-0.5 rounded decoration-line-through text-xs">{{ change.oldValue }}</span>
            <span class="text-muted-foreground">&rarr;</span>
            <span class="text-green-700 bg-green-500/10 px-1.5 py-0.5 rounded">{{ change.newValue }}</span>
          </template>
        </div>
      </div>
    </div>

    <!-- Code Mode (Text Diff) -->
    <div v-else class="text-xs font-mono p-4 overflow-x-auto bg-muted/10 h-64 overflow-y-auto">
      <div v-if="codeDiff.length === 0 || (codeDiff.length === 1 && !codeDiff[0].added && !codeDiff[0].removed)" class="text-center text-muted-foreground p-4">
        Content is identical.
      </div>

      <template v-else>
        <div v-for="(part, index) in codeDiff" :key="index" 
             :class="{
               'bg-green-500/20 text-green-800 dark:text-green-400 block': part.added,
               'bg-red-500/20 text-red-800 dark:text-red-400 block': part.removed,
               'text-muted-foreground': !part.added && !part.removed
             }">
          <span class="select-none opacity-50 w-4 inline-block text-right mr-2">
            {{ part.added ? '+' : part.removed ? '-' : ' ' }}
          </span>
          <span>{{ part.value }}</span>
        </div>
      </template>
    </div>
  </div>
</template>
