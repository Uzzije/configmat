import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import OrganizationSettings from '@/views/settings/OrganizationSettings.vue'
import { organizationService } from '@/api/services'

vi.mock('@/api/services', () => ({
    organizationService: {
        getTenant: vi.fn(),
        updateTenant: vi.fn(),
        getContextTypes: vi.fn(),
        createContextType: vi.fn(),
        deleteContextType: vi.fn(),
        getEnvironments: vi.fn(),
        createEnvironment: vi.fn(),
        deleteEnvironment: vi.fn(),
        reorderEnvironments: vi.fn()
    }
}))

describe('OrganizationSettings.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        organizationService.getTenant.mockResolvedValue({
            name: 'Test Org',
            slug: 'test-org'
        })
        organizationService.getContextTypes.mockResolvedValue({ results: [{ id: 1, type: 'app', category: 'Software' }] })
        organizationService.getEnvironments.mockResolvedValue({ results: [{ id: 1, name: 'Local', slug: 'local' }] })

        vi.spyOn(window, 'confirm').mockReturnValue(true)
    })

    it('loads and displays org details', async () => {
        const wrapper = mount(OrganizationSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(organizationService.getTenant).toHaveBeenCalled()
        expect(wrapper.find('input[placeholder="My Organization"]').element.value).toBe('Test Org')
        expect(wrapper.text()).toContain('app')
    })

    it('updates organization name', async () => {
        const wrapper = mount(OrganizationSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        await wrapper.find('input[placeholder="My Organization"]').setValue('New Name')
        // Find form inside 'Organization Details' section
        const forms = wrapper.findAll('form')
        await forms[0].trigger('submit.prevent')

        expect(organizationService.updateTenant).toHaveBeenCalledWith({ name: 'New Name' })
    })

    it('adds environment', async () => {
        const wrapper = mount(OrganizationSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        // Find inputs for environment
        // They are in the 3rd card (Environments).
        // Or find by placeholder.
        const nameInput = wrapper.findAll('input').find(i => i.attributes('placeholder')?.includes('Development'))
        const slugInput = wrapper.findAll('input').find(i => i.attributes('placeholder')?.includes('dev'))

        if (!nameInput || !slugInput) throw new Error('Environment inputs not found')

        await nameInput.setValue('Staging')
        await slugInput.setValue('stage')

        // Find Add button in that section.
        // It's in the same div as the inputs.
        // Or specific text. "Add". There are 2 "Add" buttons.
        // The second "Add" button is likely for environments.
        const buttons = wrapper.findAll('button').filter(b => b.text() === 'Add')
        const addEnvBtn = buttons[1] // 0 is Context, 1 is Environment

        if (!addEnvBtn) throw new Error('Add Environment button not found')
        await addEnvBtn.trigger('click')

        expect(organizationService.createEnvironment).toHaveBeenCalledWith({
            name: 'Staging',
            slug: 'stage',
            order: 1 // existing length was 1
        })
    })

    it('removes environment', async () => {
        const wrapper = mount(OrganizationSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        // Find remove button for environment (3rd section)
        // Environment list is the last one.
        // It has a "Remove" button.
        // There are 2 "Remove" buttons (Context Type, Environment).
        const removeBtns = wrapper.findAll('button').filter(b => b.text() === 'Remove')
        const removeEnvBtn = removeBtns[1]

        await removeEnvBtn.trigger('click')
        expect(window.confirm).toHaveBeenCalled()
        expect(organizationService.deleteEnvironment).toHaveBeenCalledWith(1) // Existing env id
    })

    it('moves environment', async () => {
        // Setup 2 environments
        organizationService.getEnvironments.mockResolvedValue({
            results: [
                { id: 1, name: 'Dev', slug: 'dev', order: 0 },
                { id: 2, name: 'Prod', slug: 'prod', order: 1 }
            ]
        })

        const wrapper = mount(OrganizationSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        // Move "Dev" down (index 0)
        // Buttons with arrows. ▲ ▼
        // Dev is first. ▲ disabled. ▼ enabled.
        const downBtn = wrapper.findAll('button').find(b => b.text().includes('▼'))
        await downBtn.trigger('click')

        expect(organizationService.reorderEnvironments).toHaveBeenCalled()
        // Order should be [2, 1] (Prod id, Dev id)
        expect(organizationService.reorderEnvironments).toHaveBeenCalledWith([2, 1])
    })
})
