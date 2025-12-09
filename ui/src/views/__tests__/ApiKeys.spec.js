import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ApiKeys from '@/views/ApiKeys.vue'
import { apiKeyService, assetService } from '@/api/services'
import { createPinia, setActivePinia } from 'pinia'

// Mock Services
vi.mock('@/api/services', () => ({
    apiKeyService: {
        getKeys: vi.fn(),
        createKey: vi.fn(),
        revokeKey: vi.fn()
    },
    assetService: {
        getAssets: vi.fn()
    }
}))

// Ensure navigator clipboard exists
if (!navigator.clipboard) {
    Object.assign(navigator, {
        clipboard: {
            writeText: vi.fn().mockResolvedValue()
        }
    })
}

describe('ApiKeys.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        // Provide safer default return values
        apiKeyService.getKeys.mockResolvedValue({ results: [] })
        assetService.getAssets.mockResolvedValue({ results: [] })

        // Mock clipboard spy if existing
        if (navigator.clipboard && navigator.clipboard.writeText) {
            vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()
        }
    })

    it('loads and displays keys', async () => {
        const keys = [{ id: 1, label: 'Prod Key', key_prefix: 'sk_live', created_at: new Date().toISOString() }]
        apiKeyService.getKeys.mockResolvedValue(keys)
        // Note: Logic allows response to be array OR obj with results.

        const wrapper = mount(ApiKeys, { global: { plugins: [pinia] } })

        // Wait for onMounted async
        await new Promise(resolve => setTimeout(resolve, 0))
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('Prod Key')
    })

    it('creates a new key flow', async () => {
        const wrapper = mount(ApiKeys, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()

        // Create button
        const buttons = wrapper.findAll('button')
        const createBtn = buttons.find(b => b.text().includes('Create API Key'))
        if (!createBtn) throw new Error('Create button not found')
        await createBtn.trigger('click')

        // Verify modal
        expect(wrapper.text()).toContain('Create API Key')

        // Fill label
        await wrapper.find('input[placeholder="e.g., Production API Key"]').setValue('New Key')

        // Submit
        apiKeyService.createKey.mockResolvedValue({ key: 'sk_123', label: 'New Key' })
        await wrapper.find('form').trigger('submit.prevent')

        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0)) // Wait for Async logic

        expect(apiKeyService.createKey).toHaveBeenCalled()
        expect(wrapper.text()).toContain('Copy this key now')
    })
})
