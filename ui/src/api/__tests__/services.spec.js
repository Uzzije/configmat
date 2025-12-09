import { describe, it, expect, vi, beforeEach } from 'vitest'
import api from '@/api/client'
import {
    assetService,
    organizationService,
    teamService,
    userService
} from '@/api/services'

// Mock api client
vi.mock('@/api/client', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn()
    }
}))

describe('Services', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    describe('assetService', () => {
        it('getAssets calls correct endpoint', async () => {
            api.get.mockResolvedValue({ data: [] })
            await assetService.getAssets({ search: 'foo' })
            expect(api.get).toHaveBeenCalledWith('/assets/', { params: { search: 'foo' } })
        })

        it('createAsset posts data', async () => {
            const payload = { name: 'Asset' }
            api.post.mockResolvedValue({ data: { id: 1 } })
            await assetService.createAsset(payload)
            expect(api.post).toHaveBeenCalledWith('/assets/', payload)
        })

        it('promoteAsset payload', async () => {
            api.post.mockResolvedValue({ data: {} })
            await assetService.promoteAsset('slug-1', 'local', 'prod')
            expect(api.post).toHaveBeenCalledWith('/assets/slug-1/promote/', {
                from_env: 'local',
                to_env: 'prod'
            })
        })
    })

    describe('organizationService', () => {
        it('getMyTenants calls endpoint', async () => {
            api.get.mockResolvedValue({ data: [] })
            await organizationService.getMyTenants()
            expect(api.get).toHaveBeenCalledWith('/organization/tenant/my_tenants/')
        })

        it('switchTenant calls correct endpoint', async () => {
            api.post.mockResolvedValue({ data: {} })
            await organizationService.switchTenant('t-123')
            expect(api.post).toHaveBeenCalledWith('/organization/tenant/t-123/switch/')
        })
    })

    describe('teamService', () => {
        it('createInvitation calls endpoint', async () => {
            api.post.mockResolvedValue({ data: {} })
            await teamService.createInvitation('test@test.com', 'admin')
            expect(api.post).toHaveBeenCalledWith('/team/invitations/', {
                email: 'test@test.com',
                role: 'admin'
            })
        })
    })

    describe('userService', () => {
        it('changePassword posts data', async () => {
            api.put.mockResolvedValue({ data: {} })
            await userService.changePassword('old', 'new')
            expect(api.put).toHaveBeenCalledWith('/auth/password-change/', {
                old_password: 'old',
                new_password: 'new'
            })
        })
    })
})
