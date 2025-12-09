import api from './client';

export const assetService = {
    // Get all assets
    async getAssets(params = {}) {
        const response = await api.get('/assets/', { params });
        return response.data;
    },

    // Get single asset by slug
    async getAsset(slug) {
        const response = await api.get(`/assets/${slug}/`);
        return response.data;
    },

    // Create new asset
    async createAsset(data) {
        const response = await api.post('/assets/', data);
        return response.data;
    },

    // Update asset
    async updateAsset(slug, data) {
        const response = await api.put(`/assets/${slug}/`, data);
        return response.data;
    },

    // Delete asset
    async deleteAsset(slug) {
        await api.delete(`/assets/${slug}/`);
    },

    // Promote asset
    async promoteAsset(slug, fromEnv, toEnv) {
        const response = await api.post(`/assets/${slug}/promote/`, {
            from_env: fromEnv,
            to_env: toEnv
        });
        return response.data;
    }
};

export const configObjectService = {
    // Get all objects for an asset
    async getObjects(assetId) {
        const response = await api.get(`/objects/?asset=${assetId}`);
        return response.data;
    },

    // Get single object
    async getObject(objectId) {
        const response = await api.get(`/objects/${objectId}/`);
        return response.data;
    },

    // Create new object
    async createObject(data) {
        const response = await api.post('/objects/', data);
        return response.data;
    },


    // Update object values
    async updateObjectValues(objectId, environment, values) {
        const response = await api.post(`/objects/${objectId}/update-values/`, {
            environment,
            values
        });
        return response.data;
    },

    // Update object metadata (name, description, etc.)
    async updateObject(objectId, data) {
        const response = await api.patch(`/objects/${objectId}/`, data);
        return response.data;
    },

    // Delete object
    async deleteObject(objectId) {
        await api.delete(`/objects/${objectId}/`);
    },

    // Get versions
    async getVersions(objectId, environment) {
        let url = `/versions/?config_object=${objectId}`;
        if (environment) {
            url += `&environment=${environment}`;
        }
        const response = await api.get(url);
        return response.data;
    },

    // Rollback to version
    async rollbackVersion(versionId) {
        const response = await api.post(`/versions/${versionId}/rollback/`);
        return response.data;
    }
};

export const apiKeyService = {
    // Get all API keys
    async getKeys() {
        const response = await api.get('/api-keys/');
        return response.data;
    },

    // Create new API key
    async createKey(data) {
        const response = await api.post('/api-keys/', data);
        return response.data;
    },

    // Revoke API key
    async revokeKey(keyId) {
        const response = await api.delete(`/api-keys/${keyId}/`);
        return response.data;
    }
};

export const publicConfigService = {
    // Get public config (uses API key, not JWT)
    async getConfig(tenantSlug, assetSlug, environment, apiKey) {
        const response = await api.get(`/public/${tenantSlug}/${assetSlug}/${environment}/`, {
            headers: {
                'X-API-Key': apiKey
            }
        });
        return response.data;
    }
};

export const teamService = {
    // Get team members
    async getMembers() {
        const response = await api.get('/team/members/');
        return response.data;
    },

    // Update member role
    async updateMemberRole(memberId, role) {
        const response = await api.patch(`/team/members/${memberId}/`, { role });
        return response.data;
    },

    // Remove member
    async removeMember(memberId) {
        await api.delete(`/team/members/${memberId}/`);
    },

    // Get invitations
    async getInvitations() {
        const response = await api.get('/team/invitations/');
        return response.data;
    },

    // Create invitation
    async createInvitation(email, role = 'user') {
        const response = await api.post('/team/invitations/', { email, role });
        return response.data;
    },

    // Resend invitation
    async resendInvitation(invitationId) {
        const response = await api.post(`/team/invitations/${invitationId}/resend/`);
        return response.data;
    },

    // Revoke invitation
    async revokeInvitation(invitationId) {
        await api.delete(`/team/invitations/${invitationId}/`);
    }
};

export const organizationService = {
    // Get tenant info
    async getTenant() {
        const response = await api.get('/organization/tenant/');
        const data = response.data.results || response.data;
        return Array.isArray(data) ? data[0] : data;
    },

    async getMyTenants() {
        const response = await api.get('/organization/tenant/my_tenants/');
        return response.data;
    },

    async switchTenant(tenantId) {
        const response = await api.post(`/organization/tenant/${tenantId}/switch/`);
        return response.data;
    },

    // Update tenant
    async updateTenant(data) {
        const tenant = await this.getTenant();
        const response = await api.patch(`/organization/tenant/${tenant.id}/`, data);
        return response.data;
    },

    // Context Types
    async getContextTypes() {
        const response = await api.get('/organization/context-types/');
        return response.data;
    },

    async createContextType(data) {
        const response = await api.post('/organization/context-types/', data);
        return response.data;
    },

    async deleteContextType(id) {
        await api.delete(`/organization/context-types/${id}/`);
    },

    // Environments
    async getEnvironments() {
        const response = await api.get('/organization/environments/');
        return response.data;
    },

    async createEnvironment(data) {
        const response = await api.post('/organization/environments/', data);
        return response.data;
    },

    async updateEnvironment(id, data) {
        const response = await api.patch(`/organization/environments/${id}/`, data);
        return response.data;
    },

    async deleteEnvironment(id) {
        await api.delete(`/organization/environments/${id}/`);
    },

    async reorderEnvironments(order) {
        const response = await api.post('/organization/environments/reorder/', { order });
        return response.data;
    }
};

export const userService = {
    async changePassword(oldPassword, newPassword) {
        const response = await api.put('/auth/password-change/', {
            old_password: oldPassword,
            new_password: newPassword
        });
        return response.data;
    }
};

export const auditService = {
    async getLogs(params = {}) {
        const response = await api.get('/audit-logs/', { params });
        return response.data;
    }
};
