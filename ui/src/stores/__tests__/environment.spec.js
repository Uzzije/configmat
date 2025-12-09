import { setActivePinia, createPinia } from 'pinia'
import { useEnvironmentStore } from '@/stores/environment'
import { describe, it, expect, beforeEach } from 'vitest'

describe('Environment Store', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('initializes with local', () => {
        const store = useEnvironmentStore()
        expect(store.currentEnvironment).toBe('local')
    })

    it('can set environment', () => {
        const store = useEnvironmentStore()
        store.setEnvironment('prod')
        expect(store.currentEnvironment).toBe('prod')
    })

    it('has predefined environments', () => {
        const store = useEnvironmentStore()
        expect(store.environments).toHaveLength(3)
        expect(store.environments[0].value).toBe('local')
    })
})
