import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import AssetEdit from '@/views/assets/AssetEdit.vue'
import { assetService } from '@/api/services'

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    }),
    useRoute: () => ({
        params: { slug: 'test-asset' }
    })
}))

vi.mock('@/api/services', () => ({
    assetService: {
        getAsset: vi.fn(),
        updateAsset: vi.fn()
    }
}))

describe('AssetEdit.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        assetService.getAsset.mockResolvedValue({
            name: 'Test Asset',
            slug: 'test-asset',
            context_type: 'default',
            context: 'global'
        })
    })

    it('loads asset on mount', async () => {
        const wrapper = mount(AssetEdit, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(assetService.getAsset).toHaveBeenCalledWith('test-asset')
        expect(wrapper.find('input#name').element.value).toBe('Test Asset')
    })

    it('updates asset', async () => {
        assetService.updateAsset.mockResolvedValue({ slug: 'test-asset' })

        const wrapper = mount(AssetEdit, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        await wrapper.find('input#name').setValue('Updated Name')
        await wrapper.find('form').trigger('submit.prevent')

        expect(assetService.updateAsset).toHaveBeenCalled()
        expect(mockPush).toHaveBeenCalledWith('/assets/test-asset')
    })
})
