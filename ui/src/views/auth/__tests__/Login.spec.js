import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import Login from '@/views/auth/Login.vue'
import { useAuthStore } from '@/stores/auth'

// Mock Router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush,
        currentRoute: { value: { path: '/login' } }
    })
}))

describe('Login.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
    })

    it('renders login form', () => {
        const wrapper = mount(Login, {
            global: {
                plugins: [pinia],
                stubs: {
                    RouterLink: RouterLinkStub
                }
            }
        })

        expect(wrapper.find('input[type="email"]').exists()).toBe(true)
        expect(wrapper.find('input[type="password"]').exists()).toBe(true)
        expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
    })

    it('calls login action with credentials', async () => {
        const authStore = useAuthStore()
        authStore.login = vi.fn().mockResolvedValue(true) // Mock successful login

        const wrapper = mount(Login, {
            global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
        })

        // Fill form
        await wrapper.find('input[type="email"]').setValue('user@test.com')
        await wrapper.find('input[type="password"]').setValue('password123')

        // Submit
        await wrapper.find('form').trigger('submit.prevent')

        expect(authStore.login).toHaveBeenCalledWith('user@test.com', 'password123')
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
    })

    it('displays error message on failure', async () => {
        const authStore = useAuthStore()
        authStore.login = vi.fn().mockRejectedValue(new Error('Invalid credentials'))

        const wrapper = mount(Login, {
            global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
        })

        await wrapper.find('input[type="email"]').setValue('user@test.com')
        await wrapper.find('input[type="password"]').setValue('wrong')
        await wrapper.find('form').trigger('submit.prevent')

        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 10))
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('Invalid credentials')
    })
})
