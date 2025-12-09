import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import ProfileSettings from '@/views/settings/ProfileSettings.vue'
import { userService } from '@/api/services'
// It imports api from '../../api/client'. We need to mock that module.
// And userService.
import api from '@/api/client'

vi.mock('@/api/services', () => ({
    userService: {
        changePassword: vi.fn()
    }
}))

vi.mock('@/api/client', () => ({
    default: {
        get: vi.fn(),
        patch: vi.fn()
    }
}))

describe('ProfileSettings.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        api.get.mockResolvedValue({ data: { first_name: 'John', last_name: 'Doe', email: 'john@test.com' } })
    })

    it('loads profile on mount', async () => {
        const wrapper = mount(ProfileSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(api.get).toHaveBeenCalledWith('/auth/me/')
        expect(wrapper.find('input#first_name').element.value).toBe('John')
    })

    it('updates profile', async () => {
        const wrapper = mount(ProfileSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        await wrapper.find('input#first_name').setValue('Jane')
        api.patch.mockResolvedValue({ data: { first_name: 'Jane' } })

        // Find save button (first submit button)
        await wrapper.find('form').trigger('submit.prevent')

        expect(api.patch).toHaveBeenCalledWith('/auth/me/', { first_name: 'Jane', last_name: 'Doe' })
        expect(wrapper.text()).toContain('Profile updated successfully')
    })

    it('validates password mismatch', async () => {
        const wrapper = mount(ProfileSettings, { global: { plugins: [pinia] } })

        // Find password form inputs
        // Inputs 4, 5, 6 usually (Current, New, Confirm)
        const passwordInputs = wrapper.findAll('input[type="password"]')
        await passwordInputs[0].setValue('old')
        await passwordInputs[1].setValue('new')
        await passwordInputs[2].setValue('mismatch')

        const changeBtn = wrapper.findAll('button').find(b => b.text().includes('Update Password'))
        await changeBtn.trigger('click') // Inside form? It's a separate form.
        // It's in a form @submit.prevent="handleChangePassword"
        // We can trigger submit on the SECOND form.
        const forms = wrapper.findAll('form')
        await forms[1].trigger('submit.prevent')

        expect(wrapper.text()).toContain('New passwords do not match')
        expect(userService.changePassword).not.toHaveBeenCalled()
    })
})
