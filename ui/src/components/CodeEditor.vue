<script setup>
import { ref, watch, onMounted } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { json } from '@codemirror/lang-json'
import { yaml } from '@codemirror/lang-yaml'
import { oneDark } from '@codemirror/theme-one-dark'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'json', // 'json' or 'yaml'
    validator: (value) => ['json', 'yaml'].includes(value)
  },
  placeholder: {
    type: String,
    default: ''
  },
  height: {
    type: String,
    default: '300px'
  }
})

const emit = defineEmits(['update:modelValue'])

const code = ref(props.modelValue)

// CodeMirror extensions based on language
const extensions = ref([])

function setupExtensions() {
  const baseExtensions = []
  
  if (props.language === 'json') {
    baseExtensions.push(json())
  } else if (props.language === 'yaml') {
    baseExtensions.push(yaml())
  }
  
  // Add dark theme
  baseExtensions.push(oneDark)
  
  extensions.value = baseExtensions
}

// Watch for language changes
watch(() => props.language, () => {
  setupExtensions()
})

// Watch for external value changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== code.value) {
    code.value = newValue
  }
})

// Emit changes to parent
watch(code, (newValue) => {
  emit('update:modelValue', newValue)
})

onMounted(() => {
  setupExtensions()
})
</script>

<template>
  <div class="code-editor-wrapper">
    <Codemirror
      v-model="code"
      :placeholder="placeholder"
      :style="{ height: height }"
      :autofocus="false"
      :indent-with-tab="true"
      :tab-size="2"
      :extensions="extensions"
      class="code-editor"
    />
  </div>
</template>

<style scoped>
.code-editor-wrapper {
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  overflow: hidden;
}

.code-editor {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 13px;
}

/* Override CodeMirror styles to match our theme */
:deep(.cm-editor) {
  background-color: hsl(var(--muted) / 0.3);
}

:deep(.cm-gutters) {
  background-color: hsl(var(--muted) / 0.5);
  border-right: 1px solid hsl(var(--border));
}

:deep(.cm-activeLineGutter) {
  background-color: hsl(var(--muted));
}

:deep(.cm-activeLine) {
  background-color: hsl(var(--muted) / 0.2);
}

:deep(.cm-cursor) {
  border-left-color: hsl(var(--foreground));
}

:deep(.cm-selectionBackground) {
  background-color: hsl(var(--primary) / 0.3) !important;
}

:deep(.cm-focused .cm-selectionBackground) {
  background-color: hsl(var(--primary) / 0.3) !important;
}
</style>
