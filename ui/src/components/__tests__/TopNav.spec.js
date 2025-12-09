import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import TopNav from '@/components/TopNav.vue'
import { organizationService } from '@/api/services'
import { useAuthStore } from '@/stores/auth'

// Mocks
vi.mock('@/api/client', () => ({ default: { post: vi.fn() } }))
vi.mock('@/api/services', () => ({
    organizationService: {
        getMyTenants: vi.fn(),
        getTenant: vi.fn(),
        switchTenant: vi.fn()
    }
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    })
}))

describe('TopNav.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        organizationService.getMyTenants.mockResolvedValue([])
        organizationService.getTenant.mockResolvedValue(null)
    })

    it('renders user info when authenticated', async () => {
        const authStore = useAuthStore()
        authStore.user = { email: 'test@user.com', first_name: 'TestUser' }

        const wrapper = mount(TopNav, {
            global: {
                plugins: [pinia]
            }
        })

        // Wait for mount and watchers
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('TestUser')
        expect(wrapper.text()).toContain('ConfigMat')
    })

    it('logout calls auth store and redirects', async () => {
        const authStore = useAuthStore()
        authStore.user = { email: 'test@user.com' }
        // Mock logout action if we want to spy on it, or just spy on store
        // Since store is real, we spy on the action wrapper?
        // Easier: Spy on router push. Real logout clears state.

        const wrapper = mount(TopNav, { global: { plugins: [pinia] } })

        // Find user menu button (User name or initial 'T')
        // Selector: button with text containing 'T' (from TestUser, wait no name set -> 'T')
        // Using class logic
        const userBtn = wrapper.findAll('button').find(b => b.text().includes('U') || b.text().includes('test@user.com'))
        await userBtn.trigger('click')

        // Find logout
        const logoutBtn = wrapper.findAll('button').find(b => b.text() === 'Logout')
        await logoutBtn.trigger('click')

        expect(authStore.user).toBeNull()
        expect(mockPush).toHaveBeenCalledWith('/login')
    })

    it('search navigation', async () => {
        const wrapper = mount(TopNav, { global: { plugins: [pinia] } })
        const input = wrapper.find('input[type="text"]')
        await input.setValue('my-asset')
        await input.trigger('keyup.enter')

        expect(mockPush).toHaveBeenCalledWith({ path: '/assets', query: { search: 'my-asset' } })
    })

    it('loads tenants on mount if authenticated', async () => {
        const authStore = useAuthStore()
        authStore.user = { email: 'test@user.com', current_tenant: { id: 1, name: 'T1' } }
        organizationService.getMyTenants.mockResolvedValue([{ id: 1, name: 'T1' }, { id: 2, name: 'T2' }])

        const wrapper = mount(TopNav, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        // wait for async loadTenants
        await new Promise(resolve => setTimeout(resolve, 10))

        expect(organizationService.getMyTenants).toHaveBeenCalled()
        // Check if tenants are populated in component state? (Not easily accessible unless exposed)
        // Check if tenant menu shows items
        expect(wrapper.vm.tenants).toHaveLength(2)
    })
})
