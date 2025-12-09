import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import AssetCreate from '@/views/assets/AssetCreate.vue'
import { assetService } from '@/api/services'

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    })
}))

vi.mock('@/api/services', () => ({
    assetService: {
        createAsset: vi.fn()
    }
}))

describe('AssetCreate.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
    })

    it('validates required fields', async () => {
        const wrapper = mount(AssetCreate, { global: { plugins: [pinia] } })

        await wrapper.find('form').trigger('submit.prevent')
        expect(wrapper.text()).toContain('Name and slug are required')
        expect(assetService.createAsset).not.toHaveBeenCalled()
    })

    it('auto-generates slug', async () => {
        const wrapper = mount(AssetCreate, { global: { plugins: [pinia] } })

        const nameInput = wrapper.find('input#name')
        await nameInput.setValue('Test Service Config')
        await nameInput.trigger('blur')

        const slugInput = wrapper.find('input#slug')
        expect(slugInput.element.value).toBe('test-service-config')
    })

    it('creates asset successfully', async () => {
        assetService.createAsset.mockResolvedValue({ slug: 'new-asset' })

        const wrapper = mount(AssetCreate, { global: { plugins: [pinia] } })

        await wrapper.find('input#name').setValue('New Asset')
        await wrapper.find('input#slug').setValue('new-asset')

        await wrapper.find('form').trigger('submit.prevent')

        expect(assetService.createAsset).toHaveBeenCalledWith(expect.objectContaining({
            name: 'New Asset',
            slug: 'new-asset'
        }))
        expect(mockPush).toHaveBeenCalledWith('/assets/new-asset')
    })
})
