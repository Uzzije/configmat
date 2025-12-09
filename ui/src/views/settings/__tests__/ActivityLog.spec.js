import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ActivityLog from '@/views/settings/ActivityLog.vue'
import { auditService, teamService } from '@/api/services'

vi.mock('@/api/services', () => ({
    auditService: {
        getLogs: vi.fn()
    },
    teamService: {
        getMembers: vi.fn()
    }
}))

describe('ActivityLog.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        auditService.getLogs.mockResolvedValue({ results: [], count: 0 })
        teamService.getMembers.mockResolvedValue([])
    })

    it('renders logs', async () => {
        const logs = [{
            id: 1,
            user_name: 'Alice',
            action: 'create',
            target: 'Asset1',
            created_at: new Date().toISOString()
        }]
        auditService.getLogs.mockResolvedValue({ results: logs, count: 1 })

        const wrapper = mount(ActivityLog)
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(wrapper.text()).toContain('Alice')
        expect(wrapper.text()).toContain('create')
        expect(wrapper.text()).toContain('Asset1')
    })

    it('filters by user', async () => {
        // Setup team members
        teamService.getMembers.mockResolvedValue([{ id: 1, user: { id: 101, first_name: 'Bob', last_name: 'Jones', email: 'bob@test' } }])

        const wrapper = mount(ActivityLog)
        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0)) // Load initial

        const selects = wrapper.findAll('select')
        const userSelect = selects[0]

        await userSelect.setValue('101')

        await wrapper.vm.$nextTick()
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(auditService.getLogs).toHaveBeenCalledTimes(2)
        const lastCall = auditService.getLogs.mock.calls.at(-1)
        // Expect number 101 because Vue v-model preserves number type from option value
        expect(lastCall[0]).toMatchObject({ user: 101 })
    })
})
