import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEnvironmentStore = defineStore('environment', () => {
    // State
    const currentEnvironment = ref('local')
    const environments = ref([
        { value: 'local', label: 'Local' },
        { value: 'stage', label: 'Stage' },
        { value: 'prod', label: 'Production' }
    ])

    // Actions
    function setEnvironment(env) {
        currentEnvironment.value = env
    }

    return {
        currentEnvironment,
        environments,
        setEnvironment
    }
})
