/**
 * API Client for Network Data Editor
 * Handles all communication with the Flask backend
 */

const API = {
    baseUrl: '/api',

    /**
     * Make an API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options,
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // ==========================================================================
    // Nodes
    // ==========================================================================

    async getNodes(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/nodes?${query}`);
    },

    async getAllNodes() {
        return this.request('/nodes/all');
    },

    async getNode(id) {
        return this.request(`/nodes/${id}`);
    },

    async createNode(name, type, subtype = null) {
        return this.request('/nodes', {
            method: 'POST',
            body: { name, type, subtype },
        });
    },

    async updateNode(id, data) {
        return this.request(`/nodes/${id}`, {
            method: 'PUT',
            body: data,
        });
    },

    async deleteNode(id) {
        return this.request(`/nodes/${id}`, {
            method: 'DELETE',
        });
    },

    async getNodeConnections(id) {
        return this.request(`/nodes/${id}/connections`);
    },

    async mergeNodes(primaryId, secondaryId) {
        return this.request('/nodes/merge', {
            method: 'POST',
            body: { primary_id: primaryId, secondary_id: secondaryId },
        });
    },

    // ==========================================================================
    // Edges
    // ==========================================================================

    async getEdges(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/edges?${query}`);
    },

    async getEdge(id) {
        return this.request(`/edges/${id}`);
    },

    async createEdge(sourceId, targetId, type) {
        return this.request('/edges', {
            method: 'POST',
            body: { source_id: sourceId, target_id: targetId, type },
        });
    },

    async updateEdge(id, data) {
        return this.request(`/edges/${id}`, {
            method: 'PUT',
            body: data,
        });
    },

    async deleteEdge(id) {
        return this.request(`/edges/${id}`, {
            method: 'DELETE',
        });
    },

    // ==========================================================================
    // Batch Operations
    // ==========================================================================

    async batchUpdateSubtype(nodeIds, subtype) {
        return this.request('/batch/nodes/subtype', {
            method: 'POST',
            body: { node_ids: nodeIds, subtype },
        });
    },

    async batchUpdateType(edgeIds, type) {
        return this.request('/batch/edges/type', {
            method: 'POST',
            body: { edge_ids: edgeIds, type },
        });
    },

    async batchMarkReviewed(edgeIds, reviewed = true) {
        return this.request('/batch/edges/reviewed', {
            method: 'POST',
            body: { edge_ids: edgeIds, reviewed },
        });
    },

    async batchCreateEdges(sourceIds, targetId, type) {
        return this.request('/batch/edges/create', {
            method: 'POST',
            body: { source_ids: sourceIds, target_id: targetId, type },
        });
    },

    async batchDeleteEdges(edgeIds) {
        return this.request('/batch/edges/delete', {
            method: 'POST',
            body: { edge_ids: edgeIds },
        });
    },

    // ==========================================================================
    // Import/Export
    // ==========================================================================

    async importFromDisk() {
        return this.request('/import/csv', {
            method: 'POST',
        });
    },

    async importFromUpload(typesFile, edgesFile) {
        const formData = new FormData();
        formData.append('types_file', typesFile);
        formData.append('edges_file', edgesFile);

        const response = await fetch(`${this.baseUrl}/import/csv`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    },

    async recalculateShared() {
        return this.request('/recalculate', {
            method: 'POST',
        });
    },

    // ==========================================================================
    // Statistics
    // ==========================================================================

    async getStats() {
        return this.request('/stats');
    },

    async getSubtypes() {
        return this.request('/subtypes');
    },
};
