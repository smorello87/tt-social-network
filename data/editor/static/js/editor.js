/**
 * Main Editor Application
 * Network Data Editor for Italian-American Literary Network
 */

const Editor = {
    // Application state
    state: {
        currentTab: 'nodes',
        currentPage: 1,
        perPage: 50,
        totalPages: 1,
        selectedItems: new Set(),
        allNodes: [], // Cached for dropdowns
        searchTimeout: null,
        sortColumn: null,
        sortDirection: 'desc', // 'asc' or 'desc'
        selectedTargets: [], // For accumulative target selection in Add Edge modal
        sourceConnections: new Set(), // IDs of nodes already connected to source in Add Edge modal
    },

    /**
     * Initialize the editor
     */
    async init() {
        console.log('Initializing Network Data Editor...');

        // Load initial data
        await Promise.all([
            this.loadStats(),
            this.loadData(),
        ]);

        // Set up keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });

        console.log('Editor initialized');
    },

    // ==========================================================================
    // Data Loading
    // ==========================================================================

    /**
     * Load statistics
     */
    async loadStats() {
        try {
            const stats = await API.getStats();

            document.getElementById('stat-nodes').textContent = stats.nodes.total || 0;
            document.getElementById('stat-edges').textContent = stats.edges.total || 0;
            document.getElementById('stat-persons').textContent = stats.nodes.person || 0;
            document.getElementById('stat-institutions').textContent = stats.nodes.institution || 0;
            document.getElementById('stat-review').textContent = stats.needs_review || 0;
            document.getElementById('review-badge').textContent = stats.needs_review || 0;
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    },

    /**
     * Load data for current tab
     */
    async loadData() {
        this.setLoading(true);

        try {
            if (this.state.currentTab === 'nodes') {
                await this.loadNodes();
            } else {
                await this.loadEdges();
            }
        } catch (error) {
            console.error('Failed to load data:', error);
            this.showToast(`Error loading data: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Load nodes data
     */
    async loadNodes() {
        const params = {
            page: this.state.currentPage,
            per_page: this.state.perPage,
        };

        const typeFilter = document.getElementById('filter-node-type').value;
        const search = document.getElementById('filter-node-search').value;

        if (typeFilter) params.type = typeFilter;
        if (search) params.search = search;

        // Add sorting parameters
        if (this.state.sortColumn) {
            params.sort_by = this.state.sortColumn;
            params.sort_dir = this.state.sortDirection;
        }

        const result = await API.getNodes(params);

        this.state.totalPages = result.pages;
        this.renderNodesTable(result.nodes);
        this.updatePagination(result);
    },

    /**
     * Load edges data
     */
    async loadEdges() {
        const params = {
            page: this.state.currentPage,
            per_page: this.state.perPage,
        };

        // Different filters for edges vs review tab
        if (this.state.currentTab === 'review') {
            // Show all edges with type "unknown" - these need classification
            params.type = 'unknown';
            const search = document.getElementById('filter-review-search').value;
            if (search) params.search = search;
        } else {
            const typeFilter = document.getElementById('filter-edge-type').value;
            const sharedFilter = document.getElementById('filter-shared').value;
            const search = document.getElementById('filter-edge-search').value;

            if (typeFilter) params.type = typeFilter;
            if (search) params.search = search;

            if (sharedFilter === '0') {
                params.min_shared = 0;
                params.max_shared = 0;
            } else if (sharedFilter === '1-2') {
                params.min_shared = 1;
                params.max_shared = 2;
            } else if (sharedFilter === '3+') {
                params.min_shared = 3;
            }
        }

        // Add sorting parameters
        if (this.state.sortColumn) {
            params.sort_by = this.state.sortColumn;
            params.sort_dir = this.state.sortDirection;
        }

        const result = await API.getEdges(params);

        this.state.totalPages = result.pages;
        this.renderEdgesTable(result.edges);
        this.updatePagination(result);
    },

    // ==========================================================================
    // Table Rendering
    // ==========================================================================

    /**
     * Render nodes table
     */
    renderNodesTable(nodes) {
        const header = document.getElementById('table-header');
        const body = document.getElementById('table-body');

        header.innerHTML = `
            <tr>
                <th><input type="checkbox" onchange="Editor.toggleSelectAll(this.checked)"></th>
                <th class="${this.getSortClass('name')}" onclick="Editor.sortBy('name')">Name</th>
                <th class="${this.getSortClass('type')}" onclick="Editor.sortBy('type')">Type</th>
                <th class="${this.getSortClass('connections')}" onclick="Editor.sortBy('connections')">Connections</th>
                <th>Actions</th>
            </tr>
        `;

        if (nodes.length === 0) {
            this.showEmptyState('No nodes found');
            return;
        }

        this.hideEmptyState();

        body.innerHTML = nodes.map(node => `
            <tr>
                <td>
                    <input type="checkbox" data-id="${node.id}"
                           ${this.state.selectedItems.has(node.id) ? 'checked' : ''}
                           onchange="Editor.toggleSelect(${node.id}, this.checked)">
                </td>
                <td>${this.escapeHtml(node.name)}</td>
                <td><span class="badge badge-${node.type}">${node.type}</span></td>
                <td>
                    <span class="connection-count" onclick="Editor.showConnections(${node.id}, '${this.escapeHtml(node.name).replace(/'/g, "\\'")}')">${node.connection_count || 0}</span>
                </td>
                <td>
                    <button class="btn btn-small btn-add-edge" onclick="Editor.addEdgeFromNode(${node.id}, '${this.escapeHtml(node.name).replace(/'/g, "\\'")}')" title="Add edge from this node">+</button>
                    <button class="btn btn-small" onclick="Editor.editNode(${node.id})">Edit</button>
                </td>
            </tr>
        `).join('');
    },

    /**
     * Render edges table
     */
    renderEdgesTable(edges) {
        const header = document.getElementById('table-header');
        const body = document.getElementById('table-body');

        header.innerHTML = `
            <tr>
                <th><input type="checkbox" onchange="Editor.toggleSelectAll(this.checked)"></th>
                <th class="${this.getSortClass('source')}" onclick="Editor.sortBy('source')">Source</th>
                <th class="${this.getSortClass('target')}" onclick="Editor.sortBy('target')">Target</th>
                <th class="${this.getSortClass('type')}" onclick="Editor.sortBy('type')">Type</th>
                <th class="${this.getSortClass('shared')}" onclick="Editor.sortBy('shared')">Shared</th>
                <th class="${this.getSortClass('review')}" onclick="Editor.sortBy('review')">Review</th>
                <th>Actions</th>
            </tr>
        `;

        if (edges.length === 0) {
            this.showEmptyState(this.state.currentTab === 'review'
                ? 'No edges need review'
                : 'No edges found');
            return;
        }

        this.hideEmptyState();

        body.innerHTML = edges.map(edge => `
            <tr class="${edge.needs_review ? 'needs-review' : ''}">
                <td>
                    <input type="checkbox" data-id="${edge.id}"
                           ${this.state.selectedItems.has(edge.id) ? 'checked' : ''}
                           onchange="Editor.toggleSelect(${edge.id}, this.checked)">
                </td>
                <td>
                    ${this.escapeHtml(edge.source_name)}
                    <span class="badge badge-${edge.source_type}" style="font-size: 0.65rem; padding: 2px 6px; margin-left: 4px;">${edge.source_type.charAt(0).toUpperCase()}</span>
                </td>
                <td>
                    ${this.escapeHtml(edge.target_name)}
                    <span class="badge badge-${edge.target_type}" style="font-size: 0.65rem; padding: 2px 6px; margin-left: 4px;">${edge.target_type.charAt(0).toUpperCase()}</span>
                </td>
                <td><span class="badge badge-${edge.type}">${edge.type}</span></td>
                <td>${edge.shared_count || 0}</td>
                <td>${edge.needs_review ? '<span class="review-flag">!</span>' : '-'}</td>
                <td>
                    <button class="btn btn-small" onclick="Editor.editEdge(${edge.id})">Edit</button>
                </td>
            </tr>
        `).join('');
    },

    // ==========================================================================
    // Tab Navigation
    // ==========================================================================

    /**
     * Switch to a different tab
     */
    switchTab(tab) {
        this.state.currentTab = tab;
        this.state.currentPage = 1;
        this.state.sortColumn = null;
        this.state.sortDirection = 'desc';
        this.clearSelection();

        // Update tab buttons
        document.querySelectorAll('.tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // Show/hide filter groups
        document.querySelectorAll('.filter-group').forEach(group => {
            group.style.display = group.dataset.for === tab ? 'flex' : 'none';
        });

        // Load data
        this.loadData();
    },

    // ==========================================================================
    // Filters
    // ==========================================================================

    /**
     * Apply current filters
     */
    applyFilters() {
        this.state.currentPage = 1;
        this.loadData();
    },

    /**
     * Debounced search
     */
    debounceSearch() {
        clearTimeout(this.state.searchTimeout);
        this.state.searchTimeout = setTimeout(() => {
            this.applyFilters();
        }, 300);
    },

    /**
     * Show autocomplete dropdown with matching nodes
     */
    async showAutocomplete(inputId, dropdownId) {
        const input = document.getElementById(inputId);
        const dropdown = document.getElementById(dropdownId);
        const search = input.value.trim().toLowerCase();

        // Also trigger debounced search for table
        this.debounceSearch();

        if (search.length < 1) {
            dropdown.classList.remove('visible');
            return;
        }

        // Ensure nodes are loaded
        if (this.state.allNodes.length === 0) {
            this.state.allNodes = await API.getAllNodes();
        }

        // Filter matching nodes
        const matches = this.state.allNodes.filter(node =>
            node.name.toLowerCase().includes(search)
        ).slice(0, 15);

        if (matches.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-empty">No matches found</div>';
        } else {
            dropdown.innerHTML = matches.map(node => `
                <div class="autocomplete-item" onclick="Editor.selectAutocompleteNode('${this.escapeHtml(node.name).replace(/'/g, "\\'")}', '${inputId}', '${dropdownId}')">
                    <span class="node-name">${this.escapeHtml(node.name)}</span>
                    <span class="node-type ${node.type}">${node.type}</span>
                </div>
            `).join('');
        }

        dropdown.classList.add('visible');
    },

    /**
     * Hide autocomplete dropdown
     */
    hideAutocomplete(dropdownId) {
        document.getElementById(dropdownId).classList.remove('visible');
    },

    /**
     * Select node from autocomplete
     */
    selectAutocompleteNode(name, inputId, dropdownId) {
        document.getElementById(inputId).value = name;
        this.hideAutocomplete(dropdownId);
        this.applyFilters();
    },

    // ==========================================================================
    // Sorting
    // ==========================================================================

    /**
     * Sort by a column
     */
    sortBy(column) {
        if (this.state.sortColumn === column) {
            // Toggle direction
            this.state.sortDirection = this.state.sortDirection === 'desc' ? 'asc' : 'desc';
        } else {
            // New column, start with descending
            this.state.sortColumn = column;
            this.state.sortDirection = 'desc';
        }
        this.state.currentPage = 1;
        this.loadData();
    },

    /**
     * Sort data array by current sort settings
     */
    sortData(data, columns) {
        if (!this.state.sortColumn || !columns[this.state.sortColumn]) {
            return data;
        }

        const sortKey = columns[this.state.sortColumn];
        const direction = this.state.sortDirection === 'asc' ? 1 : -1;

        return [...data].sort((a, b) => {
            let aVal = a[sortKey];
            let bVal = b[sortKey];

            // Handle nulls
            if (aVal == null) aVal = '';
            if (bVal == null) bVal = '';

            // Numeric comparison
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return (aVal - bVal) * direction;
            }

            // String comparison (case-insensitive)
            return String(aVal).toLowerCase().localeCompare(String(bVal).toLowerCase()) * direction;
        });
    },

    /**
     * Get sort class for a column header
     */
    getSortClass(column) {
        if (this.state.sortColumn !== column) return 'sortable';
        return `sortable sort-${this.state.sortDirection}`;
    },

    /**
     * Clear all filters
     */
    clearFilters() {
        if (this.state.currentTab === 'nodes') {
            document.getElementById('filter-node-type').value = '';
            document.getElementById('filter-node-search').value = '';
        } else if (this.state.currentTab === 'edges') {
            document.getElementById('filter-edge-type').value = '';
            document.getElementById('filter-shared').value = '';
            document.getElementById('filter-edge-search').value = '';
        } else {
            document.getElementById('filter-review-search').value = '';
        }
        this.applyFilters();
    },

    // ==========================================================================
    // Selection
    // ==========================================================================

    /**
     * Toggle selection of an item
     */
    toggleSelect(id, checked) {
        if (checked) {
            this.state.selectedItems.add(id);
        } else {
            this.state.selectedItems.delete(id);
        }
        this.updateBatchBar();
    },

    /**
     * Toggle select all visible items
     */
    toggleSelectAll(checked) {
        document.querySelectorAll('#table-body input[type="checkbox"]').forEach(cb => {
            const id = parseInt(cb.dataset.id);
            if (checked) {
                this.state.selectedItems.add(id);
            } else {
                this.state.selectedItems.delete(id);
            }
            cb.checked = checked;
        });
        this.updateBatchBar();
    },

    /**
     * Clear all selections
     */
    clearSelection() {
        this.state.selectedItems.clear();
        document.querySelectorAll('#table-body input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        this.updateBatchBar();
    },

    /**
     * Update batch action bar visibility
     */
    updateBatchBar() {
        const bar = document.getElementById('batch-bar');
        const count = this.state.selectedItems.size;

        document.getElementById('selected-count').textContent = count;

        if (count > 0) {
            bar.classList.add('visible');
        } else {
            bar.classList.remove('visible');
        }
    },

    // ==========================================================================
    // Pagination
    // ==========================================================================

    /**
     * Update pagination display
     */
    updatePagination(result) {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');

        prevBtn.disabled = result.page <= 1;
        nextBtn.disabled = result.page >= result.pages;

        pageInfo.textContent = `Page ${result.page} of ${result.pages} (${result.total} total)`;
    },

    /**
     * Go to previous page
     */
    prevPage() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
            this.loadData();
        }
    },

    /**
     * Go to next page
     */
    nextPage() {
        if (this.state.currentPage < this.state.totalPages) {
            this.state.currentPage++;
            this.loadData();
        }
    },

    // ==========================================================================
    // Connections View
    // ==========================================================================

    /**
     * Show connections for a node
     */
    async showConnections(nodeId, nodeName) {
        try {
            const connections = await API.getNodeConnections(nodeId);

            document.getElementById('connections-modal-title').textContent =
                `Connections for ${nodeName}`;

            const list = document.getElementById('connections-list');

            if (connections.length === 0) {
                list.innerHTML = '<div class="connections-empty">No connections found</div>';
            } else {
                list.innerHTML = connections.map(conn => `
                    <div class="connection-item" onclick="Editor.searchForNode('${this.escapeHtml(conn.name).replace(/'/g, "\\'")}')">
                        <span class="connection-name">${this.escapeHtml(conn.name)}</span>
                        <div class="connection-badges">
                            <span class="badge badge-${conn.type}">${conn.type}</span>
                            <span class="badge badge-${conn.edge_type}">${conn.edge_type}</span>
                        </div>
                    </div>
                `).join('');
            }

            this.showModal('connections-modal');
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Search for a specific node (from connections click)
     */
    searchForNode(name) {
        this.closeModal('connections-modal');
        this.switchTab('nodes');
        document.getElementById('filter-node-search').value = name;
        this.applyFilters();
    },

    // ==========================================================================
    // Node Merge
    // ==========================================================================

    /**
     * Show merge nodes modal
     */
    async showMergeModal() {
        document.getElementById('merge-primary-search').value = '';
        document.getElementById('merge-secondary-search').value = '';

        // Load all nodes
        await this.loadTargetNodes();
        this.filterMergeNodes('primary', '');
        this.filterMergeNodes('secondary', '');

        this.showModal('merge-modal');
    },

    /**
     * Search for nodes in merge modal
     */
    searchMergeNode(which) {
        const search = document.getElementById(`merge-${which}-search`).value.toLowerCase();
        this.filterMergeNodes(which, search);
    },

    /**
     * Filter nodes in merge modal dropdowns
     */
    filterMergeNodes(which, search) {
        const select = document.getElementById(`merge-${which}-select`);
        const filtered = this.state.allNodes.filter(node =>
            node.name.toLowerCase().includes(search)
        ).slice(0, 100);

        select.innerHTML = filtered.map(node =>
            `<option value="${node.id}">${this.escapeHtml(node.name)} (${node.type})</option>`
        ).join('');
    },

    /**
     * Merge two nodes
     */
    async mergeNodes() {
        const primaryId = document.getElementById('merge-primary-select').value;
        const secondaryId = document.getElementById('merge-secondary-select').value;

        if (!primaryId || !secondaryId) {
            this.showToast('Please select both nodes', 'error');
            return;
        }

        if (primaryId === secondaryId) {
            this.showToast('Cannot merge a node with itself', 'error');
            return;
        }

        const primaryName = document.getElementById('merge-primary-select').selectedOptions[0]?.text || 'Primary';
        const secondaryName = document.getElementById('merge-secondary-select').selectedOptions[0]?.text || 'Secondary';

        if (!confirm(`Merge "${secondaryName}" into "${primaryName}"?\n\nThis will transfer all edges and delete the secondary node. This cannot be undone.`)) {
            return;
        }

        try {
            const result = await API.mergeNodes(parseInt(primaryId), parseInt(secondaryId));
            this.showToast(`Merged "${result.secondary_name}" into "${result.primary_name}" (${result.edges_transferred} edges transferred)`, 'success');
            this.closeModal('merge-modal');

            // Refresh node cache and data
            this.state.allNodes = [];
            await this.loadStats();
            await this.loadData();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    // ==========================================================================
    // Node CRUD
    // ==========================================================================

    /**
     * Show add node modal
     */
    showAddNodeModal() {
        document.getElementById('new-node-name').value = '';
        document.getElementById('new-node-type').value = 'person';
        this.showModal('add-node-modal');
    },

    /**
     * Create a new node
     */
    async createNode() {
        const name = document.getElementById('new-node-name').value.trim();
        const type = document.getElementById('new-node-type').value;

        if (!name) {
            this.showToast('Please enter a name', 'error');
            return;
        }

        try {
            const newNode = await API.createNode(name, type);
            this.showToast(`Created node "${name}"`, 'success');
            this.closeModal('add-node-modal');
            // Clear cache so new node appears in dropdowns
            this.state.allNodes = [];
            await this.loadData();
            await this.loadStats();
            return newNode;
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
            return null;
        }
    },

    /**
     * Open edit node modal
     */
    async editNode(id) {
        try {
            const node = await API.getNode(id);

            document.getElementById('edit-node-id').value = node.id;
            document.getElementById('edit-node-name').value = node.name;
            document.getElementById('edit-node-type').value = node.type;

            this.showModal('edit-node-modal');
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Update a node
     */
    async updateNode() {
        const id = document.getElementById('edit-node-id').value;
        const name = document.getElementById('edit-node-name').value.trim();
        const type = document.getElementById('edit-node-type').value;

        if (!name) {
            this.showToast('Please enter a name', 'error');
            return;
        }

        try {
            await API.updateNode(id, { name, type });
            this.showToast('Node updated', 'success');
            this.closeModal('edit-node-modal');
            this.loadData();
            this.loadStats();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Delete a node
     */
    async deleteNode() {
        const id = document.getElementById('edit-node-id').value;

        if (!confirm('Delete this node? This will also delete all its connections.')) {
            return;
        }

        try {
            await API.deleteNode(id);
            this.showToast('Node deleted', 'success');
            this.closeModal('edit-node-modal');
            this.loadData();
            this.loadStats();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    // ==========================================================================
    // Edge CRUD
    // ==========================================================================

    /**
     * Open edit edge modal
     */
    async editEdge(id) {
        try {
            const edge = await API.getEdge(id);

            // Load all nodes for dropdowns
            await this.loadTargetNodes();

            document.getElementById('edit-edge-id').value = edge.id;
            document.getElementById('edit-edge-type').value = edge.type;

            // Populate source dropdown and select current
            document.getElementById('edit-edge-source-search').value = '';
            this.filterEditEdgeNodes('edit-edge-source-select', '', edge.source_id);

            // Populate target dropdown and select current
            document.getElementById('edit-edge-target-search').value = '';
            this.filterEditEdgeNodes('edit-edge-target-select', '', edge.target_id);

            // Show shared institutions
            const sharedList = document.getElementById('shared-institutions-list');
            if (edge.shared_institutions && edge.shared_institutions.length > 0) {
                sharedList.innerHTML = edge.shared_institutions.map(inst =>
                    `<div class="shared-list-item">${this.escapeHtml(inst.name)}</div>`
                ).join('');
            } else {
                sharedList.innerHTML = '<div class="shared-list-empty">No shared institutions</div>';
            }

            this.showModal('edit-edge-modal');
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Search source nodes for edit edge
     */
    searchEditEdgeSource() {
        const search = document.getElementById('edit-edge-source-search').value.toLowerCase();
        const currentId = parseInt(document.getElementById('edit-edge-source-select').value);
        this.filterEditEdgeNodes('edit-edge-source-select', search, currentId);
    },

    /**
     * Search target nodes for edit edge
     */
    searchEditEdgeTarget() {
        const search = document.getElementById('edit-edge-target-search').value.toLowerCase();
        const currentId = parseInt(document.getElementById('edit-edge-target-select').value);
        this.filterEditEdgeNodes('edit-edge-target-select', search, currentId);
    },

    /**
     * Filter nodes in edit edge dropdowns
     */
    filterEditEdgeNodes(selectId, search, selectedId) {
        const select = document.getElementById(selectId);
        let filtered = this.state.allNodes.filter(node =>
            node.name.toLowerCase().includes(search)
        );

        // Ensure selected node is always in the list
        if (selectedId && !filtered.find(n => n.id === selectedId)) {
            const selectedNode = this.state.allNodes.find(n => n.id === selectedId);
            if (selectedNode) {
                filtered = [selectedNode, ...filtered];
            }
        }

        filtered = filtered.slice(0, 100);

        select.innerHTML = filtered.map(node =>
            `<option value="${node.id}" ${node.id === selectedId ? 'selected' : ''}>${this.escapeHtml(node.name)} (${node.type})</option>`
        ).join('');
    },

    /**
     * Update an edge
     */
    async updateEdge() {
        const id = document.getElementById('edit-edge-id').value;
        const sourceId = document.getElementById('edit-edge-source-select').value;
        const targetId = document.getElementById('edit-edge-target-select').value;
        const type = document.getElementById('edit-edge-type').value;

        if (!sourceId || !targetId) {
            this.showToast('Please select both source and target', 'error');
            return;
        }

        if (sourceId === targetId) {
            this.showToast('Source and target must be different', 'error');
            return;
        }

        try {
            await API.updateEdge(id, {
                source_id: parseInt(sourceId),
                target_id: parseInt(targetId),
                type: type
            });
            this.showToast('Edge updated', 'success');
            this.closeModal('edit-edge-modal');
            await this.loadStats();
            await this.loadData();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Delete an edge
     */
    async deleteEdge() {
        const id = document.getElementById('edit-edge-id').value;

        if (!confirm('Delete this edge?')) {
            return;
        }

        try {
            await API.deleteEdge(id);
            this.showToast('Edge deleted', 'success');
            this.closeModal('edit-edge-modal');
            this.loadData();
            this.loadStats();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Show add edge modal
     */
    async showAddEdgeModal(preselectedSourceId = null, preselectedSourceName = null) {
        document.getElementById('add-edge-source-search').value = preselectedSourceName || '';
        document.getElementById('add-edge-target-search').value = '';
        document.getElementById('add-edge-type').value = 'affiliation';

        // Clear selected targets and source connections
        this.state.selectedTargets = [];
        this.state.sourceConnections = new Set();
        this.renderSelectedTargets();

        // Load all nodes for selection
        await this.loadTargetNodes();

        if (preselectedSourceId && preselectedSourceName) {
            // Pre-select the source node
            this.filterAddEdgeNodes('add-edge-source-select', preselectedSourceName.toLowerCase(), false);
            // Select the node in the dropdown
            const select = document.getElementById('add-edge-source-select');
            for (let option of select.options) {
                if (parseInt(option.value) === preselectedSourceId) {
                    option.selected = true;
                    break;
                }
            }
            // Load existing connections for this source
            await this.loadSourceConnections(preselectedSourceId);
        } else {
            this.filterAddEdgeNodes('add-edge-source-select', '', false);
        }

        // Render empty target results
        this.renderTargetResults('');

        // Update button text
        this.updateCreateEdgesButton();

        this.showModal('add-edge-modal');
    },

    /**
     * Load existing connections for the source node
     */
    async loadSourceConnections(sourceId) {
        try {
            const connections = await API.getNodeConnections(sourceId);
            this.state.sourceConnections = new Set(connections.map(c => c.id));
        } catch (e) {
            this.state.sourceConnections = new Set();
        }
    },

    /**
     * Handle source selection change - reload connections
     */
    async onSourceChange() {
        const sourceId = document.getElementById('add-edge-source-select').value;
        if (sourceId) {
            await this.loadSourceConnections(parseInt(sourceId));
        } else {
            this.state.sourceConnections = new Set();
        }
        // Re-render targets to update linked indicators
        const searchRaw = document.getElementById('add-edge-target-search').value;
        this.renderTargetResults(searchRaw);
    },

    /**
     * Add edge from a specific node (opens modal with node pre-selected)
     */
    addEdgeFromNode(nodeId, nodeName) {
        this.showAddEdgeModal(nodeId, nodeName);
    },

    /**
     * Update the create edges button text
     */
    updateCreateEdgesButton() {
        const count = this.state.selectedTargets.length;
        const btn = document.getElementById('create-edges-btn');
        btn.textContent = count === 0 ? 'Create Edge(s)' : `Create ${count} Edge${count !== 1 ? 's' : ''}`;
    },

    /**
     * Search source nodes for add edge
     */
    searchAddEdgeSource() {
        const search = document.getElementById('add-edge-source-search').value.toLowerCase();
        this.filterAddEdgeNodes('add-edge-source-select', search, false);
    },

    /**
     * Search target nodes for add edge (accumulative selection)
     */
    searchAddEdgeTarget() {
        const searchRaw = document.getElementById('add-edge-target-search').value;
        this.renderTargetResults(searchRaw);
    },

    /**
     * Render target results list with + buttons
     */
    renderTargetResults(searchRaw) {
        const container = document.getElementById('target-results-list');
        const selectedIds = new Set(this.state.selectedTargets.map(t => t.id));
        const search = searchRaw.toLowerCase();

        let filtered = this.state.allNodes.filter(node =>
            node.name.toLowerCase().includes(search) && !selectedIds.has(node.id)
        ).slice(0, 50);

        let html = '';

        // Show "Create new node" option if search has text (use original casing for display/creation)
        if (searchRaw.length > 0) {
            const exactMatch = this.state.allNodes.find(n => n.name.toLowerCase() === search);
            if (!exactMatch) {
                html += `
                    <div class="target-result-item create-new">
                        <span class="result-name">Create "<strong>${this.escapeHtml(searchRaw)}</strong>" as new node</span>
                        <button class="add-btn create-btn" onclick="Editor.createAndAddTarget('${this.escapeHtml(searchRaw).replace(/'/g, "\\'")}')" title="Create and add">+ New</button>
                    </div>
                `;
            }
        }

        if (filtered.length === 0 && search.length > 0 && html === '') {
            container.innerHTML = '<div class="target-result-empty">No matches found</div>';
        } else if (filtered.length === 0 && html === '') {
            container.innerHTML = '';
        } else {
            html += filtered.map(node => {
                const isLinked = this.state.sourceConnections.has(node.id);
                return `
                    <div class="target-result-item ${isLinked ? 'already-linked' : ''}">
                        <span class="result-name">${this.escapeHtml(node.name)}${isLinked ? ' <span class="linked-badge">linked</span>' : ''}</span>
                        <span class="result-type ${node.type}">${node.type}</span>
                        ${isLinked ? '<span class="add-btn disabled">✓</span>' : `<button class="add-btn" onclick="Editor.addTarget(${node.id}, '${this.escapeHtml(node.name).replace(/'/g, "\\'")}', '${node.type}')" title="Add target">+</button>`}
                    </div>
                `;
            }).join('');
            container.innerHTML = html;
        }
    },

    /**
     * Create a new node and add it as target
     */
    async createAndAddTarget(name) {
        // Show quick dialog for type selection
        const type = prompt(`Create "${name}" as which type?\n\nEnter: person, institution, or unknown`, 'person');
        if (!type || !['person', 'institution', 'unknown'].includes(type.toLowerCase())) {
            this.showToast('Invalid type. Use: person, institution, or unknown', 'error');
            return;
        }

        try {
            const result = await API.createNode(name, type.toLowerCase());
            // Clear cache and reload
            this.state.allNodes = [];
            await this.loadTargetNodes();
            // Add to selected targets
            this.addTarget(result.id, result.name, result.type);
            this.showToast(`Created "${name}" and added as target`, 'success');
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Add a target to the selection
     */
    addTarget(id, name, type) {
        // Check if already selected
        if (this.state.selectedTargets.find(t => t.id === id)) {
            return;
        }

        this.state.selectedTargets.push({ id, name, type });
        this.renderSelectedTargets();
        this.updateCreateEdgesButton();

        // Re-render results to remove the added item
        const searchRaw = document.getElementById('add-edge-target-search').value;
        this.renderTargetResults(searchRaw);
    },

    /**
     * Remove a target from the selection
     */
    removeTarget(id) {
        this.state.selectedTargets = this.state.selectedTargets.filter(t => t.id !== id);
        this.renderSelectedTargets();
        this.updateCreateEdgesButton();

        // Re-render results to add the removed item back
        const searchRaw = document.getElementById('add-edge-target-search').value;
        this.renderTargetResults(searchRaw);
    },

    /**
     * Render selected targets as chips
     */
    renderSelectedTargets() {
        const container = document.getElementById('selected-targets-container');

        if (this.state.selectedTargets.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = this.state.selectedTargets.map(target => `
            <span class="target-chip ${target.type}">
                ${this.escapeHtml(target.name)}
                <button class="chip-remove" onclick="Editor.removeTarget(${target.id})" title="Remove">&times;</button>
            </span>
        `).join('');
    },

    /**
     * Filter nodes in add edge source dropdown
     */
    filterAddEdgeNodes(selectId, search, isMultiple = false, preserveSelected = new Set()) {
        const select = document.getElementById(selectId);
        let filtered = this.state.allNodes.filter(node =>
            node.name.toLowerCase().includes(search)
        ).slice(0, 100);

        select.innerHTML = filtered.map(node => {
            const isSelected = preserveSelected.has(String(node.id));
            return `<option value="${node.id}" ${isSelected ? 'selected' : ''}>${this.escapeHtml(node.name)} (${node.type})</option>`;
        }).join('');
    },

    /**
     * Create new edge(s) - supports multiple targets via accumulative selection
     */
    async createEdges() {
        const sourceId = document.getElementById('add-edge-source-select').value;
        const targetIds = this.state.selectedTargets.map(t => t.id);
        const type = document.getElementById('add-edge-type').value;

        if (!sourceId) {
            this.showToast('Please select a source node', 'error');
            return;
        }

        if (targetIds.length === 0) {
            this.showToast('Please add at least one target node', 'error');
            return;
        }

        // Filter out self-connections
        const validTargets = targetIds.filter(id => id !== parseInt(sourceId));
        if (validTargets.length === 0) {
            this.showToast('Source and target must be different', 'error');
            return;
        }

        try {
            let created = 0;
            let errors = 0;

            for (const targetId of validTargets) {
                try {
                    await API.createEdge(parseInt(sourceId), targetId, type);
                    created++;
                } catch (e) {
                    errors++;
                }
            }

            if (created > 0) {
                this.showToast(`Created ${created} edge${created !== 1 ? 's' : ''}${errors > 0 ? ` (${errors} failed/existed)` : ''}`, 'success');
            } else {
                this.showToast('No edges created (may already exist)', 'error');
            }

            this.closeModal('add-edge-modal');
            await this.loadStats();
            await this.loadData();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    },

    // ==========================================================================
    // Import
    // ==========================================================================

    /**
     * Show import modal
     */
    showImportModal() {
        this.showModal('import-modal');
    },

    /**
     * Import from disk
     */
    async importFromDisk() {
        try {
            this.setLoading(true);
            const result = await API.importFromDisk();
            this.showToast(
                `Imported ${result.nodes_created} nodes and ${result.edges_created} edges`,
                'success'
            );
            this.closeModal('import-modal');
            this.loadData();
            this.loadStats();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Import from uploaded files
     */
    async importFromUpload() {
        const typesFile = document.getElementById('upload-types').files[0];
        const edgesFile = document.getElementById('upload-edges').files[0];

        if (!typesFile || !edgesFile) {
            this.showToast('Please select both files', 'error');
            return;
        }

        try {
            this.setLoading(true);
            const result = await API.importFromUpload(typesFile, edgesFile);
            this.showToast(
                `Imported ${result.nodes_created} nodes and ${result.edges_created} edges`,
                'success'
            );
            this.closeModal('import-modal');
            this.loadData();
            this.loadStats();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Recalculate shared institutions
     */
    async recalculateShared() {
        try {
            this.setLoading(true);
            const result = await API.recalculateShared();
            this.showToast(`Recalculated ${result.edges_processed} edges`, 'success');
            this.loadData();
            this.loadStats();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    },

    // ==========================================================================
    // Target Node Search (for batch connect)
    // ==========================================================================

    /**
     * Load all nodes for dropdown
     */
    async loadTargetNodes() {
        if (this.state.allNodes.length === 0) {
            this.state.allNodes = await API.getAllNodes();
        }
        this.filterTargetNodes('');
    },

    /**
     * Filter target nodes based on search
     */
    searchTargetNode() {
        const search = document.getElementById('batch-target-search').value.toLowerCase();
        this.filterTargetNodes(search);
    },

    /**
     * Update target node dropdown
     */
    filterTargetNodes(search) {
        const select = document.getElementById('batch-target-select');
        const filtered = this.state.allNodes.filter(node =>
            node.name.toLowerCase().includes(search)
        ).slice(0, 100); // Limit to 100 results

        select.innerHTML = filtered.map(node =>
            `<option value="${node.id}">${this.escapeHtml(node.name)} (${node.type})</option>`
        ).join('');
    },

    // ==========================================================================
    // Modals
    // ==========================================================================

    /**
     * Show a modal
     */
    showModal(id) {
        document.getElementById(id).classList.add('visible');
    },

    /**
     * Close a modal
     */
    closeModal(id) {
        document.getElementById(id).classList.remove('visible');
    },

    /**
     * Close all modals
     */
    closeAllModals() {
        document.querySelectorAll('.modal.visible').forEach(modal => {
            modal.classList.remove('visible');
        });
    },

    // ==========================================================================
    // UI Helpers
    // ==========================================================================

    /**
     * Show/hide loading state
     */
    setLoading(loading) {
        const loadingEl = document.getElementById('loading-state');
        const tableEl = document.getElementById('data-table');

        if (loading) {
            loadingEl.style.display = 'flex';
            tableEl.style.display = 'none';
        } else {
            loadingEl.style.display = 'none';
            tableEl.style.display = 'table';
        }
    },

    /**
     * Show empty state
     */
    showEmptyState(message) {
        const emptyEl = document.getElementById('empty-state');
        const tableEl = document.getElementById('data-table');
        const msgEl = document.getElementById('empty-message');

        msgEl.textContent = message || 'No data found';
        emptyEl.style.display = 'flex';
        tableEl.style.display = 'none';
    },

    /**
     * Hide empty state
     */
    hideEmptyState() {
        const emptyEl = document.getElementById('empty-state');
        const tableEl = document.getElementById('data-table');

        emptyEl.style.display = 'none';
        tableEl.style.display = 'table';
    },

    /**
     * Show a toast notification
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    async exportGraph() {
        try {
            const res = await fetch('/api/export-graph', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                alert(`Exported graph.json: ${data.nodes} nodes, ${data.links} edges`);
            } else {
                alert('Export failed');
            }
        } catch (err) {
            alert('Export error: ' + err.message);
        }
    },
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Editor.init();
});
