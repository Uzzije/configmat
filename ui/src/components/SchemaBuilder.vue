<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object, // The schema object { key: { type: 'number', min: 10 } }
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue'])

const schema = computed({
  get() {
    return props.modelValue
  },
  set(val) {
    emit('update:modelValue', val)
  }
})

const newFieldKey = ref('')
const selectedFieldKey = ref(null)

const fieldTypes = [
  { value: 'string', label: 'String (Text)' },
  { value: 'number', label: 'Number (Integer/Float)' },
  { value: 'boolean', label: 'Boolean (True/False)' },
  { value: 'json', label: 'JSON Object' }
]

const activeRule = computed(() => {
  if (!selectedFieldKey.value) return null
  return schema.value[selectedFieldKey.value]
})

function addField() {
  if (!newFieldKey.value) return
  const key = newFieldKey.value.trim()
  
  if (schema.value[key]) {
    alert('Field already exists')
    return
  }

  // Add new field with default rule
  const newSchema = { ...schema.value }
  newSchema[key] = {
    type: 'string',
    required: false,
    description: ''
  }
  
  schema.value = newSchema
  selectedFieldKey.value = key
  newFieldKey.value = ''
}

function removeField(key) {
  if (!confirm(`Remove validation rule for "${key}"?`)) return
  
  const newSchema = { ...schema.value }
  delete newSchema[key]
  schema.value = newSchema
  
  if (selectedFieldKey.value === key) {
    selectedFieldKey.value = null
  }
}

function updateRule(updates) {
  if (!selectedFieldKey.value) return
  const key = selectedFieldKey.value
  
  const newSchema = { ...schema.value }
  newSchema[key] = { ...newSchema[key], ...updates }
  schema.value = newSchema
}
</script>

<template>
  <div class="flex h-[500px] border border-border rounded-lg overflow-hidden bg-card">
    
    <!-- Left: Field List -->
    <div class="w-1/3 border-r border-border flex flex-col bg-muted/10">
      <div class="p-3 border-b border-border">
        <h3 class="text-sm font-semibold mb-2">Schema Fields</h3>
        <div class="flex gap-2">
          <input 
            v-model="newFieldKey" 
            @keyup.enter="addField"
            placeholder="Field Key (e.g. max_retries)" 
            class="flex-1 px-2 py-1.5 text-sm rounded border border-input bg-background"
          />
          <button 
            @click="addField"
            :disabled="!newFieldKey"
            class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm disabled:opacity-50"
          >
            +
          </button>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div v-if="Object.keys(schema).length === 0" class="text-center py-8 text-xs text-muted-foreground">
          No fields defined. <br>Add a key to verify.
        </div>
        
        <div 
          v-for="(rule, key) in schema" 
          :key="key"
          @click="selectedFieldKey = key"
          class="flex items-center justify-between px-3 py-2 rounded cursor-pointer text-sm group transition-colors"
          :class="selectedFieldKey === key ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted text-foreground'"
        >
          <div class="flex items-center gap-2 truncate">
            <span>{{ key }}</span>
            <span class="text-[10px] uppercase px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
                {{ rule.type }}
            </span>
            <span v-if="rule.required" class="text-red-500 text-xs" title="Required">*</span>
          </div>
          <button 
            @click.stop="removeField(key)"
            class="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive px-1"
          >
            ×
          </button>
        </div>
      </div>
    </div>

    <!-- Right: Rule Editor -->
    <div class="flex-1 p-6 overflow-y-auto bg-card">
      <div v-if="!activeRule" class="h-full flex flex-col items-center justify-center text-muted-foreground">
        <div class="text-4xl mb-2">⚙️</div>
        <p>Select a field to configure its validation rules.</p>
      </div>
      
      <div v-else class="space-y-6">
        <div class="flex items-center justify-between border-b border-border pb-4">
          <div>
            <h2 class="text-lg font-bold">{{ selectedFieldKey }}</h2>
            <p class="text-sm text-muted-foreground">Configure validation logic</p>
          </div>
          <div class="flex items-center gap-2">
             <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
                <input 
                    type="checkbox" 
                    :checked="activeRule.required"
                    @change="e => updateRule({ required: e.target.checked })"
                    class="rounded border-input text-primary focus:ring-primary"
                >
                <span class="font-medium">Required</span>
             </label>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-6">
            <!-- Type Selection -->
            <div class="col-span-2">
                <label class="block text-sm font-medium mb-1.5">Data Type</label>
                <div class="flex gap-2">
                    <button 
                        v-for="type in fieldTypes" 
                        :key="type.value"
                        @click="updateRule({ type: type.value })"
                        class="px-3 py-2 rounded text-sm border transition-all"
                        :class="activeRule.type === type.value 
                            ? 'bg-primary text-primary-foreground border-primary' 
                            : 'bg-background border-input hover:bg-muted'"
                    >
                        {{ type.label }}
                    </button>
                </div>
            </div>

            <!-- Description -->
            <div class="col-span-2">
                <label class="block text-sm font-medium mb-1.5">Description (Tooltip)</label>
                <input 
                    :value="activeRule.description"
                    @input="e => updateRule({ description: e.target.value })"
                    type="text" 
                    class="w-full px-3 py-2 bg-background border border-input rounded text-sm"
                    placeholder="Helper text for the user..."
                >
            </div>

            <!-- Type Specific Rules: Number -->
            <template v-if="activeRule.type === 'number'">
                <div>
                    <label class="block text-sm font-medium mb-1.5">Minimum Value</label>
                    <input 
                        :value="activeRule.min"
                        @input="e => updateRule({ min: e.target.value ? Number(e.target.value) : undefined })"
                        type="number" 
                        class="w-full px-3 py-2 bg-background border border-input rounded text-sm"
                        placeholder="No min"
                    >
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1.5">Maximum Value</label>
                    <input 
                        :value="activeRule.max"
                        @input="e => updateRule({ max: e.target.value ? Number(e.target.value) : undefined })"
                        type="number" 
                        class="w-full px-3 py-2 bg-background border border-input rounded text-sm"
                        placeholder="No max"
                    >
                </div>
            </template>

            <!-- Type Specific Rules: String -->
            <template v-if="activeRule.type === 'string'">
                <div class="col-span-2">
                    <label class="block text-sm font-medium mb-1.5">Regex Pattern</label>
                    <div class="flex gap-2">
                        <span class="px-3 py-2 bg-muted border border-border rounded-l text-sm font-mono text-muted-foreground">/</span>
                        <input 
                            :value="activeRule.regex"
                            @input="e => updateRule({ regex: e.target.value })"
                            type="text" 
                            class="flex-1 px-3 py-2 bg-background border border-input text-sm font-mono"
                            placeholder="^[a-zA-Z0-9]+$"
                        >
                        <span class="px-3 py-2 bg-muted border border-border rounded-r text-sm font-mono text-muted-foreground">/</span>
                    </div>
                    <p class="text-xs text-muted-foreground mt-1">Javascript RegExp format.</p>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-1.5">Min Length</label>
                    <input 
                        :value="activeRule.min"
                        @input="e => updateRule({ min: e.target.value ? Number(e.target.value) : undefined })"
                        type="number" 
                        class="w-full px-3 py-2 bg-background border border-input rounded text-sm"
                    >
                </div>
                <div>
                    <label class="block text-sm font-medium mb-1.5">Max Length</label>
                    <input 
                        :value="activeRule.max"
                        @input="e => updateRule({ max: e.target.value ? Number(e.target.value) : undefined })"
                        type="number" 
                        class="w-full px-3 py-2 bg-background border border-input rounded text-sm"
                    >
                </div>
            </template>

        </div>

        <!-- Live Preview -->
        <div class="mt-8 pt-4 border-t border-border">
            <h4 class="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Generated Rule JSON</h4>
            <div class="bg-muted/50 p-3 rounded font-mono text-xs overflow-x-auto">
                {{ JSON.stringify(activeRule, null, 2) }}
            </div>
        </div>
      </div>
    </div>
  </div>
</template>
