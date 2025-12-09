import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import ForgotPassword from '@/views/auth/ForgotPassword.vue'

describe('ForgotPassword.vue', () => {
    it('renders email form', () => {
        const wrapper = mount(ForgotPassword, {
            global: {
                stubs: { RouterLink: RouterLinkStub }
            }
        })
        expect(wrapper.find('input[type="email"]').exists()).toBe(true)
        expect(wrapper.find('button').exists()).toBe(true)
    })
})
