import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import Register from '@/views/auth/Register.vue'
import { useAuthStore } from '@/stores/auth'

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    })
}))

describe('Register.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
    })

    it('renders register form', () => {
        const wrapper = mount(Register, {
            global: {
                plugins: [pinia],
                stubs: { RouterLink: RouterLinkStub }
            }
        })
        expect(wrapper.find('input[type="email"]').exists()).toBe(true)
        expect(wrapper.find('input#tenant_name').exists()).toBe(true)
    })

    it('validates passwords mismatch', async () => {
        const wrapper = mount(Register, { global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } } })

        await wrapper.find('input#email').setValue('user@test.com')
        await wrapper.find('input#tenant_name').setValue('Org')
        await wrapper.find('input#password').setValue('password123')
        await wrapper.find('input#confirmPassword').setValue('password456') // mismatch

        await wrapper.find('form').trigger('submit.prevent')

        expect(wrapper.text()).toContain('Passwords do not match')
    })

    it('registers successfully', async () => {
        const authStore = useAuthStore()
        authStore.register = vi.fn().mockResolvedValue(true)

        const wrapper = mount(Register, { global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } } })

        await wrapper.find('input#tenant_name').setValue('Org')
        await wrapper.find('input#email').setValue('user@test.com')
        await wrapper.find('input#password').setValue('password123')
        await wrapper.find('input#confirmPassword').setValue('password123')

        await wrapper.find('form').trigger('submit.prevent')

        expect(authStore.register).toHaveBeenCalledWith({
            email: 'user@test.com',
            password: 'password123',
            tenant_name: 'Org',
            first_name: '',
            last_name: ''
        })
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
    })
})
