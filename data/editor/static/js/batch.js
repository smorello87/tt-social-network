/**
 * Batch Operations for Network Data Editor
 * Handles multi-select and bulk actions
 */

const BatchOps = {
    /**
     * Get array of selected item IDs
     */
    getSelectedIds() {
        return Array.from(Editor.state.selectedItems);
    },

    /**
     * Set subtype for all selected nodes (institutions only)
     */
    async setSubtype() {
        const ids = this.getSelectedIds();
        const subtype = document.getElementById('batch-subtype').value;

        if (!ids.length) {
            Editor.showToast('No items selected', 'error');
            return;
        }

        if (!subtype) {
            Editor.showToast('Please select a subtype', 'error');
            return;
        }

        try {
            const result = await API.batchUpdateSubtype(ids, subtype);
            Editor.showToast(`Updated ${result.updated} nodes to "${subtype}"`, 'success');
            Editor.clearSelection();
            await Editor.loadStats();
            await Editor.loadSubtypes();
            await Editor.loadData();
        } catch (error) {
            Editor.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Set type for all selected edges
     */
    async setType() {
        const ids = this.getSelectedIds();
        const type = document.getElementById('batch-type').value;

        if (!ids.length) {
            Editor.showToast('No items selected', 'error');
            return;
        }

        if (!type) {
            Editor.showToast('Please select a type', 'error');
            return;
        }

        try {
            const result = await API.batchUpdateType(ids, type);
            Editor.showToast(`Updated ${result.updated} edges to "${type}"`, 'success');
            Editor.clearSelection();
            await Editor.loadStats();
            await Editor.loadData();
        } catch (error) {
            Editor.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Mark all selected edges as reviewed
     */
    async markReviewed() {
        const ids = this.getSelectedIds();

        if (!ids.length) {
            Editor.showToast('No items selected', 'error');
            return;
        }

        try {
            const result = await API.batchMarkReviewed(ids, true);
            Editor.showToast(`Marked ${result.updated} edges as reviewed`, 'success');
            Editor.clearSelection();
            await Editor.loadStats();
            await Editor.loadData();
        } catch (error) {
            Editor.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Delete all selected items
     */
    async deleteSelected() {
        const ids = this.getSelectedIds();

        if (!ids.length) {
            Editor.showToast('No items selected', 'error');
            return;
        }

        const confirmMsg = Editor.state.currentTab === 'nodes'
            ? `Delete ${ids.length} nodes? This will also delete all their connections.`
            : `Delete ${ids.length} edges?`;

        if (!confirm(confirmMsg)) {
            return;
        }

        try {
            if (Editor.state.currentTab === 'nodes') {
                // Delete nodes one by one (cascade deletes edges)
                let deleted = 0;
                let failed = 0;
                for (const id of ids) {
                    try {
                        await API.deleteNode(id);
                        deleted++;
                    } catch (e) {
                        failed++;
                    }
                }
                if (failed > 0) {
                    Editor.showToast(`Deleted ${deleted} nodes (${failed} failed)`, deleted > 0 ? 'success' : 'error');
                } else {
                    Editor.showToast(`Deleted ${deleted} nodes`, 'success');
                }
            } else {
                const result = await API.batchDeleteEdges(ids);
                Editor.showToast(`Deleted ${result.deleted} edges`, 'success');
            }

            Editor.clearSelection();
            await Editor.loadStats();
            await Editor.loadData();
        } catch (error) {
            Editor.clearSelection();
            await Editor.loadStats();
            await Editor.loadData();
            Editor.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Show modal to create connections from selected nodes to a target
     */
    showConnectModal() {
        const ids = this.getSelectedIds();

        if (!ids.length) {
            Editor.showToast('No nodes selected', 'error');
            return;
        }

        document.getElementById('batch-source-count').textContent = ids.length;
        Editor.showModal('batch-connect-modal');
        Editor.loadTargetNodes();
    },

    /**
     * Create connections from selected nodes to target
     */
    async createConnections() {
        const sourceIds = this.getSelectedIds();
        const targetSelect = document.getElementById('batch-target-select');
        const targetId = targetSelect.value;
        const type = document.getElementById('batch-connect-type').value;

        if (!sourceIds.length) {
            Editor.showToast('No nodes selected', 'error');
            return;
        }

        if (!targetId) {
            Editor.showToast('Please select a target node', 'error');
            return;
        }

        try {
            const result = await API.batchCreateEdges(sourceIds, parseInt(targetId), type);
            Editor.showToast(`Created ${result.created} new connections`, 'success');
            Editor.closeModal('batch-connect-modal');
            Editor.clearSelection();
            await Editor.loadStats();
            await Editor.loadData();
        } catch (error) {
            Editor.showToast(`Error: ${error.message}`, 'error');
        }
    },
};
