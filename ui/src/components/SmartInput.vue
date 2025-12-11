<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean, Object],
    default: undefined
  },
  rule: {
    type: Object,
    default: () => ({})
  },
  placeholder: String,
  type: String // 'string', 'number', 'boolean', 'json', etc.
})

const emit = defineEmits(['update:modelValue', 'validation-error'])

const parsedValue = computed({
  get() {
    return props.modelValue
  },
  set(val) {
    emit('update:modelValue', val)
    validate(val)
  }
})

// Validation Logic
const error = computed(() => validate(props.modelValue))

function validate(val) {
  const { required, min, max, regex, type } = props.rule

  if (required && (val === null || val === undefined || val === '')) {
    const msg = 'This field is required'
    emit('validation-error', msg)
    return msg
  }

  // If empty and not required, no error
  if (!val && val !== 0 && val !== false) {
    emit('validation-error', null)
    return null
  }

  // Type: Number
  if (type === 'number') {
    const num = Number(val)
    if (isNaN(num)) {
      const msg = 'Must be a number'
      emit('validation-error', msg)
      return msg
    }
    if (min !== undefined && num < min) {
      const msg = `Must be at least ${min}`
      emit('validation-error', msg)
      return msg
    }
    if (max !== undefined && num > max) {
      const msg = `Must be no more than ${max}`
      emit('validation-error', msg)
      return msg
    }
  }

  // Type: String
  if (type === 'string' && typeof val === 'string') {
    if (regex) {
      try {
        const re = new RegExp(regex)
        if (!re.test(val)) {
          const msg = 'Invalid format (regex mismatch)'
          emit('validation-error', msg)
          return msg
        }
      } catch (e) {
        console.warn('Invalid regex in rule:', regex)
      }
    }
    if (min !== undefined && val.length < min) {
      const msg = `Must be at least ${min} characters`
      emit('validation-error', msg)
      return msg
    }
    if (max !== undefined && val.length > max) {
      const msg = `Must be no more than ${max} characters`
      emit('validation-error', msg)
      return msg
    }
  }

  // If we got here, it's valid
  emit('validation-error', null)
  return null
}
</script>

<template>
  <div>
    <!-- Render different inputs based on type -->
    
    <!-- Boolean -->
    <select
      v-if="type === 'boolean' || rule.type === 'boolean'"
      v-model="parsedValue"
      class="w-full px-3 py-2 bg-background border rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
      :class="error ? 'border-destructive focus:ring-destructive' : 'border-input'"
    >
      <option :value="true">true</option>
      <option :value="false">false</option>
    </select>

    <!-- Number or String -->
    <input
      v-else
      v-model="parsedValue"
      type="text"
      :placeholder="placeholder"
      class="w-full px-3 py-2 bg-background border rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono"
      :class="error ? 'border-destructive focus:ring-destructive' : 'border-input'"
    />

    <!-- Validation Message -->
    <p v-if="error" class="text-xs text-destructive mt-1 flex items-center gap-1">
      <span>⚠</span> {{ error }}
    </p>
    <p v-else-if="rule.description" class="text-xs text-muted-foreground mt-1">
        {{ rule.description }}
    </p>
  </div>
</template>
