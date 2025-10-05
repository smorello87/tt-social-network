// Multi-Node Connection Finder JavaScript
// Handles autocomplete, node selection, and connection finding for up to 10 nodes

class MultiNodeConnectionFinder {
    constructor(nodesData) {
        this.nodes = nodesData;
        this.selectedNodes = new Set();
        this.autocompleteCache = new Map();
        this.initializeInputs();
        this.initializeButtons();
    }

    // Initialize all 10 input fields with autocomplete
    initializeInputs() {
        for (let i = 1; i <= 10; i++) {
            const input = document.getElementById(`node-${i}`);
            const dropdown = document.getElementById(`autocomplete-${i}`);

            if (input && dropdown) {
                this.setupAutocomplete(input, dropdown, i);
                this.setupInputValidation(input, i);
            }
        }
    }

    // Setup autocomplete functionality for each input
    setupAutocomplete(input, dropdown, index) {
        let debounceTimer;

        input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const value = e.target.value.trim();

            if (value.length === 0) {
                dropdown.classList.remove('active');
                dropdown.innerHTML = '';
                this.updateNodeSelection(index, null);
                return;
            }

            // Debounce search for better performance
            debounceTimer = setTimeout(() => {
                this.performAutocomplete(value, dropdown, input, index);
            }, 150);
        });

        // Handle focus events
        input.addEventListener('focus', () => {
            if (input.value.trim().length > 0) {
                this.performAutocomplete(input.value.trim(), dropdown, input, index);
            }
        });

        // Handle blur events
        input.addEventListener('blur', () => {
            // Delay to allow click on dropdown items
            setTimeout(() => {
                dropdown.classList.remove('active');
            }, 200);
        });

        // Handle keyboard navigation
        input.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e, dropdown, input, index);
        });
    }

    // Perform autocomplete search
    performAutocomplete(query, dropdown, input, index) {
        const lowerQuery = query.toLowerCase();

        // Check cache first
        if (this.autocompleteCache.has(lowerQuery)) {
            this.displayAutocompleteResults(this.autocompleteCache.get(lowerQuery), dropdown, input, index, query);
            return;
        }

        // Filter nodes
        const matches = this.nodes
            .filter(node => {
                const nodeName = node.id.toLowerCase();
                return nodeName.includes(lowerQuery) && !this.isNodeAlreadySelected(node.id, index);
            })
            .sort((a, b) => {
                // Prioritize exact matches and starts-with matches
                const aStarts = a.id.toLowerCase().startsWith(lowerQuery);
                const bStarts = b.id.toLowerCase().startsWith(lowerQuery);
                if (aStarts && !bStarts) return -1;
                if (!aStarts && bStarts) return 1;
                return a.id.localeCompare(b.id);
            })
            .slice(0, 10); // Limit to 10 suggestions

        // Cache results
        this.autocompleteCache.set(lowerQuery, matches);

        this.displayAutocompleteResults(matches, dropdown, input, index, query);
    }

    // Display autocomplete results in dropdown
    displayAutocompleteResults(matches, dropdown, input, index, query) {
        if (matches.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-item">No matches found</div>';
            dropdown.classList.add('active');
            return;
        }

        dropdown.innerHTML = '';
        matches.forEach((node, i) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            if (i === 0) item.classList.add('selected');

            // Highlight matching text
            item.innerHTML = this.highlightMatch(node.id, query);

            // Add type indicator
            const typeSpan = document.createElement('span');
            typeSpan.style.fontSize = '11px';
            typeSpan.style.color = '#a69b8c';
            typeSpan.style.marginLeft = '8px';
            typeSpan.textContent = `(${node.type})`;
            item.appendChild(typeSpan);

            item.addEventListener('click', () => {
                input.value = node.id;
                this.updateNodeSelection(index, node.id);
                dropdown.classList.remove('active');
            });

            dropdown.appendChild(item);
        });

        dropdown.classList.add('active');
    }

    // Highlight matching text in autocomplete results
    highlightMatch(text, query) {
        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    // Escape regex special characters
    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Handle keyboard navigation in dropdown
    handleKeyboardNavigation(e, dropdown, input, index) {
        if (!dropdown.classList.contains('active')) return;

        const items = dropdown.querySelectorAll('.autocomplete-item');
        const selected = dropdown.querySelector('.autocomplete-item.selected');
        let selectedIndex = Array.from(items).indexOf(selected);

        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (selectedIndex < items.length - 1) {
                    if (selected) selected.classList.remove('selected');
                    items[selectedIndex + 1].classList.add('selected');
                    items[selectedIndex + 1].scrollIntoView({ block: 'nearest' });
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (selectedIndex > 0) {
                    if (selected) selected.classList.remove('selected');
                    items[selectedIndex - 1].classList.add('selected');
                    items[selectedIndex - 1].scrollIntoView({ block: 'nearest' });
                }
                break;

            case 'Enter':
                e.preventDefault();
                if (selected && selected.textContent !== 'No matches found') {
                    const nodeText = selected.textContent.split('(')[0].trim();
                    input.value = nodeText;
                    this.updateNodeSelection(index, nodeText);
                    dropdown.classList.remove('active');
                }
                break;

            case 'Escape':
                dropdown.classList.remove('active');
                break;
        }
    }

    // Setup input validation
    setupInputValidation(input, index) {
        input.addEventListener('change', () => {
            const value = input.value.trim();
            if (value && !this.isValidNode(value)) {
                input.classList.add('error');
                this.showTooltip(input, 'Please select a valid node from the dropdown');
            } else {
                input.classList.remove('error');
            }
        });
    }

    // Check if a node is valid
    isValidNode(nodeName) {
        return this.nodes.some(node => node.id === nodeName);
    }

    // Check if a node is already selected in another input
    isNodeAlreadySelected(nodeName, currentIndex) {
        for (let i = 1; i <= 10; i++) {
            if (i === currentIndex) continue;
            const input = document.getElementById(`node-${i}`);
            if (input && input.value === nodeName) {
                return true;
            }
        }
        return false;
    }

    // Update node selection tracking
    updateNodeSelection(index, nodeName) {
        const input = document.getElementById(`node-${index}`);
        const inputGroup = input.closest('.node-input-group');

        if (nodeName && this.isValidNode(nodeName)) {
            inputGroup.classList.add('has-value');
            this.selectedNodes.add(nodeName);
        } else {
            inputGroup.classList.remove('has-value');
            // Remove previous value if any
            const previousValue = input.dataset.previousValue;
            if (previousValue) {
                this.selectedNodes.delete(previousValue);
            }
        }

        input.dataset.previousValue = nodeName || '';
        this.updateSelectedCount();
    }

    // Update the selected nodes counter
    updateSelectedCount() {
        const validNodes = this.getValidSelectedNodes();
        const countElement = document.getElementById('selected-count');
        if (countElement) {
            countElement.textContent = validNodes.length;
        }

        // Enable/disable find button based on selection
        const findButton = document.getElementById('find-connections-btn');
        if (findButton) {
            findButton.disabled = validNodes.length < 2;
            if (validNodes.length < 2) {
                findButton.title = 'Select at least 2 nodes to find connections';
            } else {
                findButton.title = '';
            }
        }
    }

    // Get all valid selected nodes
    getValidSelectedNodes() {
        const nodes = [];
        for (let i = 1; i <= 10; i++) {
            const input = document.getElementById(`node-${i}`);
            if (input) {
                const value = input.value.trim();
                if (value && this.isValidNode(value)) {
                    nodes.push(value);
                }
            }
        }
        return [...new Set(nodes)]; // Remove duplicates
    }

    // Initialize button handlers
    initializeButtons() {
        // Find Connections button
        const findButton = document.getElementById('find-connections-btn');
        if (findButton) {
            findButton.addEventListener('click', () => {
                this.findConnections();
            });
        }

        // Clear All button
        const clearButton = document.getElementById('clear-all-btn');
        if (clearButton) {
            clearButton.addEventListener('click', () => {
                this.clearAll();
            });
        }
    }

    // Find connections among selected nodes
    findConnections() {
        const selectedNodes = this.getValidSelectedNodes();

        if (selectedNodes.length < 2) {
            this.showMessage('Please select at least 2 nodes to find connections.', 'warning');
            return;
        }

        // Show loading state
        const findButton = document.getElementById('find-connections-btn');
        const originalText = findButton.textContent;
        findButton.textContent = 'Finding...';
        findButton.disabled = true;

        // Simulate processing (in real implementation, this would call the actual graph analysis)
        setTimeout(() => {
            // Call the parent visualization's multi-node connection finding method
            if (window.findMultiNodeConnections) {
                const results = window.findMultiNodeConnections(selectedNodes);
                this.displayResults(results, selectedNodes);
            } else {
                this.showMessage('Connection finding function not available.', 'error');
            }

            // Restore button state
            findButton.textContent = originalText;
            findButton.disabled = false;
            this.updateSelectedCount();
        }, 300);
    }

    // Display connection results
    displayResults(results, selectedNodes) {
        const summaryDiv = document.getElementById('results-summary');
        const contentDiv = document.getElementById('results-content');

        if (!summaryDiv || !contentDiv) return;

        // Format results
        let html = `
            <div style="margin-bottom: 10px;">
                <strong>Selected nodes:</strong> ${selectedNodes.length}
            </div>
        `;

        if (results.connections && results.connections.length > 0) {
            html += `
                <div style="margin-bottom: 10px;">
                    <strong>Direct connections found:</strong> ${results.connections.length}
                </div>
                <div style="margin-bottom: 10px;">
                    <strong>Total paths:</strong> ${results.totalPaths || 0}
                </div>
            `;

            if (results.commonNeighbors && results.commonNeighbors.length > 0) {
                html += `
                    <div>
                        <strong>Common connections:</strong> ${results.commonNeighbors.length}
                    </div>
                `;
            }
        } else {
            html = '<div style="color: #8b7355;">No direct connections found between selected nodes.</div>';
        }

        contentDiv.innerHTML = html;
        summaryDiv.style.display = 'block';
    }

    // Clear all inputs and selections
    clearAll() {
        for (let i = 1; i <= 10; i++) {
            const input = document.getElementById(`node-${i}`);
            const dropdown = document.getElementById(`autocomplete-${i}`);
            const inputGroup = input?.closest('.node-input-group');

            if (input) {
                input.value = '';
                input.classList.remove('error');
                delete input.dataset.previousValue;
            }

            if (dropdown) {
                dropdown.classList.remove('active');
                dropdown.innerHTML = '';
            }

            if (inputGroup) {
                inputGroup.classList.remove('has-value');
            }
        }

        this.selectedNodes.clear();
        this.updateSelectedCount();

        // Hide results
        const summaryDiv = document.getElementById('results-summary');
        if (summaryDiv) {
            summaryDiv.style.display = 'none';
        }

        // Clear visualization if function exists
        if (window.clearVisualization) {
            window.clearVisualization();
        }
    }

    // Show tooltip message
    showTooltip(element, message) {
        // Implementation for showing validation tooltips
        console.log(`Validation: ${message}`);
    }

    // Show system message
    showMessage(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
        // In production, this would show a toast notification or modal
    }
}

// Initialize when DOM is ready and data is loaded
document.addEventListener('DOMContentLoaded', () => {
    // This would be initialized with actual node data from the main visualization
    if (window.graphData && window.graphData.nodes) {
        const finder = new MultiNodeConnectionFinder(window.graphData.nodes);
        window.multiNodeFinder = finder; // Expose for integration
    }
});