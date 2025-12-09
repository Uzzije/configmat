import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import Dashboard from '@/views/Dashboard.vue'
import { assetService } from '@/api/services'
import { useAuthStore } from '@/stores/auth'

// Mock Services
vi.mock('@/api/services', () => ({
    assetService: {
        getAssets: vi.fn()
    }
}))

// Mock Router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    })
}))

describe('Dashboard.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        assetService.getAssets.mockResolvedValue([])
    })

    it('renders user welcome message', async () => {
        const authStore = useAuthStore()
        authStore.user = { first_name: 'Alice', email: 'alice@test.com' }

        const wrapper = mount(Dashboard, { global: { plugins: [pinia] } })

        expect(wrapper.text()).toContain('Welcome back, Alice')
    })

    it('loads and displays assets', async () => {
        const assets = [
            { id: 1, name: 'Asset1', slug: 'asset-1', context_type: 'app', updated_at: new Date().toISOString() },
            { id: 2, name: 'Asset2', slug: 'asset-2', context_type: 'db', updated_at: new Date(Date.now() - 100000).toISOString() }
        ]
        assetService.getAssets.mockResolvedValue(assets)

        const wrapper = mount(Dashboard, { global: { plugins: [pinia] } })

        // Wait for async load
        await new Promise(resolve => setTimeout(resolve, 10))
        await wrapper.vm.$nextTick()

        // Stats
        expect(wrapper.text()).toContain('Total Assets')
        // We expect stats.totalAssets to be 2
        // finding text '2' might be ambiguous, finding element structure is better
        // The stats card value has class text-3xl
        const statsValues = wrapper.findAll('.text-3xl').map(el => el.text())
        expect(statsValues).toContain('2')

        // Table
        expect(wrapper.text()).toContain('Asset1')
        expect(wrapper.text()).toContain('Asset2')
    })

    it('handles create asset navigation', async () => {
        const wrapper = mount(Dashboard, { global: { plugins: [pinia] } })

        const createBtn = wrapper.find('button.bg-primary') // "+ Create Config Asset"
        await createBtn.trigger('click')

        expect(mockPush).toHaveBeenCalledWith('/assets/create')
    })

    it('shows empty state', async () => {
        assetService.getAssets.mockResolvedValue([])
        const wrapper = mount(Dashboard, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 10))
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('No assets found')
    })
})
