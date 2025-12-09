import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import AssetList from '@/views/assets/AssetList.vue'
import { assetService, organizationService } from '@/api/services'

// Mock Services
vi.mock('@/api/services', () => ({
    assetService: {
        getAssets: vi.fn(),
        deleteAsset: vi.fn()
    },
    organizationService: {
        getContextTypes: vi.fn()
    }
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    }),
    useRoute: () => ({
        query: {}
    })
}))

describe('AssetList.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()

        // Defaults
        assetService.getAssets.mockResolvedValue({
            results: [],
            count: 0,
            next: null,
            previous: null
        })
        organizationService.getContextTypes.mockResolvedValue(['app', 'db'])
    })

    it('renders and loads assets', async () => {
        const assets = [{ id: 1, name: 'A1', slug: 'a1', context: 'c1', context_type: 'app', updated_at: new Date().toISOString() }]
        assetService.getAssets.mockResolvedValue({ results: assets, count: 1 })

        const wrapper = mount(AssetList, { global: { plugins: [pinia] } })

        // Wait for mount
        await new Promise(resolve => setTimeout(resolve, 0))
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('A1')
        expect(wrapper.text()).toContain('a1')
    })

    it('handles pagination', async () => {
        const assets = [{ id: 1, name: 'A1', slug: 'a1' }]
        // Must return items so the list (and pagination) is rendered, not empty state
        assetService.getAssets.mockResolvedValue({
            results: assets,
            count: 20,
            next: 'page=2',
            previous: null
        })

        const wrapper = mount(AssetList, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        // Find Next button
        const buttons = wrapper.findAll('button')
        const nextBtn = buttons.find(b => b.text() === 'Next')
        if (!nextBtn) throw new Error('Next button not found - maybe empty state shown?')
        expect(nextBtn.attributes('disabled')).toBeUndefined()

        await nextBtn.trigger('click')

        expect(assetService.getAssets).toHaveBeenCalledTimes(2)
    })

    it('handles delete with confirmation', async () => {
        const assets = [{ id: 1, name: 'A1', slug: 'a1', updated_at: new Date().toISOString() }]
        assetService.getAssets.mockResolvedValue({ results: assets, count: 1 })

        // Mock confirm
        vi.spyOn(window, 'confirm').mockReturnValue(true)

        const wrapper = mount(AssetList, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        const deleteBtn = wrapper.findAll('button').find(b => b.text() === 'Delete')
        await deleteBtn.trigger('click')

        expect(window.confirm).toHaveBeenCalled()
        expect(assetService.deleteAsset).toHaveBeenCalledWith('a1')
        expect(assetService.getAssets).toHaveBeenCalledTimes(2)
    })

    it('filters assets', async () => {
        const wrapper = mount(AssetList, { global: { plugins: [pinia] } })

        const searchInput = wrapper.find('input[type="text"]')
        await searchInput.setValue('test-query')

        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 500))

        expect(assetService.getAssets).toHaveBeenCalled()
        const lastCall = assetService.getAssets.mock.calls.at(-1)
        expect(lastCall[0]).toMatchObject({ search: 'test-query' })
    })
})
