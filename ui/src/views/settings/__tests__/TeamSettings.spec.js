import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import TeamSettings from '@/views/settings/TeamSettings.vue'
import { teamService } from '@/api/services'

vi.mock('@/api/services', () => ({
    teamService: {
        getMembers: vi.fn(),
        getInvitations: vi.fn(),
        createInvitation: vi.fn(),
        updateMemberRole: vi.fn(),
        removeMember: vi.fn(),
        revokeInvitation: vi.fn(),
        resendInvitation: vi.fn()
    }
}))

describe('TeamSettings.vue', () => {
    let pinia

    beforeEach(() => {
        pinia = createPinia()
        setActivePinia(pinia)
        vi.clearAllMocks()
        teamService.getMembers.mockResolvedValue([])
        teamService.getInvitations.mockResolvedValue([])
        vi.spyOn(window, 'confirm').mockReturnValue(true)
    })

    it('loads members and invitations', async () => {
        teamService.getMembers.mockResolvedValue([{ id: 1, user: { first_name: 'Alice', email: 'alice@test' }, role: 'admin' }])

        const wrapper = mount(TeamSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(wrapper.text()).toContain('Alice')
        expect(wrapper.text()).toContain('alice@test')
        expect(teamService.getMembers).toHaveBeenCalled()
        expect(teamService.getInvitations).toHaveBeenCalled()
    })

    it('invites a member', async () => {
        const wrapper = mount(TeamSettings, { global: { plugins: [pinia] } })

        // Open modal
        await wrapper.find('button').trigger('click') // + Invite Member
        expect(wrapper.text()).toContain('Invite Team Member')

        await wrapper.find('input[type="email"]').setValue('bob@test.com')
        await wrapper.find('form').trigger('submit.prevent')

        expect(teamService.createInvitation).toHaveBeenCalledWith('bob@test.com', 'user')
    })

    it('removes member', async () => {
        teamService.getMembers.mockResolvedValue([{ id: 1, user: { name: 'Alice' }, role: 'user' }])
        const wrapper = mount(TeamSettings, { global: { plugins: [pinia] } })
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        const removeBtn = wrapper.findAll('button').find(b => b.text() === 'Remove')
        await removeBtn.trigger('click')

        expect(window.confirm).toHaveBeenCalled()
        expect(teamService.removeMember).toHaveBeenCalledWith(1)
    })
})
