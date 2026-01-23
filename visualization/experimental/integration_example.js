/**
 * Integration Example - How to Replace the Multi-Node Connection Finder
 *
 * This file shows how to integrate the direct connections version
 * into your existing visualization (diva_optimized.html or diva_multinode.html)
 */

// STEP 1: Replace the existing MultiNodeConnectionFinder class with the new one
// You can either:
// A) Include the new JS file: <script src="multi_node_direct_connections.js"></script>
// B) Or copy the class directly into your HTML

// STEP 2: Update the initialization (keep the same)
// The initialization remains the same since the constructor signature is identical:
/*
window.multiNodeFinder = new MultiNodeConnectionFinder(
  data.nodes,
  data.links
);
*/

// STEP 3: Update the visualization handler
// Replace your existing findMultiNodeConnections handler with this:

function handleFindMultiNodeConnections() {
  // Get selected node IDs from input fields
  const selectedNodes = [];
  for (let i = 1; i <= 10; i++) {
    const input = document.getElementById(`node-input-${i}`) ||
                  document.getElementById(`node-${i}`);
    if (input && input.value.trim()) {
      selectedNodes.push(input.value.trim());
    }
  }

  if (selectedNodes.length === 0) {
    alert('Please select at least one node');
    return;
  }

  // Call the new finder - same method name, different behavior
  const result = window.multiNodeFinder.findMultiNodeConnections(selectedNodes);

  if (result.error) {
    alert(result.error);
    return;
  }

  // Create sets for efficient lookup
  const highlightNodeSet = new Set(result.nodes.map(n => n.toLowerCase()));
  const selectedSet = new Set(result.selectedNodes.map(n => n.toLowerCase()));
  const isolatedSet = new Set(result.info.isolatedNodes?.map(n => n.toLowerCase()) || []);

  // Update node visibility and styling
  // IMPORTANT: This is the key difference - we only show selected nodes
  nodeGroups.style("opacity", d =>
    highlightNodeSet.has(d.id.toLowerCase()) ? 1 : 0.1
  );

  // Apply different styles for different node states
  nodeGroups.select("circle")
    .classed("highlight-node", false)
    .classed("selected-node", false)
    .classed("intermediate-node", false)
    .classed("selected-node", d => selectedSet.has(d.id.toLowerCase()))
    // Add special styling for isolated nodes (nodes with no connections to other selected)
    .style("stroke-dasharray", d =>
      isolatedSet.has(d.id.toLowerCase()) ? "5,5" : "none"
    )
    .style("stroke", d => {
      const id = d.id.toLowerCase();
      if (isolatedSet.has(id)) return "#e74c3c"; // Red for isolated
      if (selectedSet.has(id)) return "#2ecc71"; // Green for connected selected
      return d.type === 'institution' ? "#6d5a44" : "#546f7d"; // Default
    })
    .style("stroke-width", d =>
      selectedSet.has(d.id.toLowerCase()) ? 3 : 1
    );

  // Create edge set for direct connections only
  const edgeSet = new Set();
  result.links.forEach(([source, target]) => {
    // Store both directions for undirected graph
    edgeSet.add(`${source.toLowerCase()}-${target.toLowerCase()}`);
    edgeSet.add(`${target.toLowerCase()}-${source.toLowerCase()}`);
  });

  // Update edge visibility - only show direct connections
  d3.selectAll("line").each(function(l) {
    const source = (typeof l.source === "object")
      ? l.source.id.toLowerCase()
      : String(l.source).toLowerCase();
    const target = (typeof l.target === "object")
      ? l.target.id.toLowerCase()
      : String(l.target).toLowerCase();

    const isHighlighted = edgeSet.has(`${source}-${target}`);

    d3.select(this)
      .classed("highlight-path", isHighlighted)
      .style("opacity", isHighlighted ? 1 : 0.05) // Very dim for non-selected
      .style("stroke-width", isHighlighted ? 2 : 1);
  });

  // Display enhanced connection info
  displayDirectConnectionInfo(result.info, selectedNodes);

  // Center the view on selected nodes only
  const nodesToCenter = allNodes.filter(n =>
    highlightNodeSet.has(n.id.toLowerCase())
  );

  if (nodesToCenter.length > 0) {
    centerNodes(nodesToCenter);
  }
}

// STEP 4: Update the info display function
function displayDirectConnectionInfo(info, selectedNodes) {
  let message = '';

  // Build the main message
  if (info.message) {
    message = info.message;
  } else {
    // Fallback message construction
    switch (info.type) {
      case 'direct_connections':
        if (info.directConnectionCount === 0) {
          message = `Selected ${info.selectedCount} nodes - No direct connections between them`;
        } else {
          const density = (parseFloat(info.connectionDensity) * 100).toFixed(0);
          message = `Selected ${info.selectedCount} nodes with ${info.directConnectionCount} direct connection(s) (${density}% density)`;
        }
        break;
      case 'error':
        message = info.message;
        break;
      default:
        message = 'Connection analysis complete';
    }
  }

  // Add information about isolated nodes
  if (info.isolatedCount > 0) {
    const isolatedList = info.isolatedNodes.slice(0, 3).join(', ');
    const more = info.isolatedCount > 3 ? ` and ${info.isolatedCount - 3} more` : '';
    message += `\nIsolated nodes: ${isolatedList}${more}`;
  }

  // Add statistics about connections
  if (info.nodeConnectionCounts) {
    const counts = Object.entries(info.nodeConnectionCounts)
      .filter(([_, count]) => count > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);

    if (counts.length > 0) {
      const topConnected = counts.map(([node, count]) =>
        `${node} (${count})`
      ).join(', ');
      message += `\nMost connected: ${topConnected}`;
    }
  }

  // Display the message
  const infoDiv = document.getElementById('connection-info') ||
                  document.getElementById('multi-node-info');
  if (infoDiv) {
    infoDiv.innerHTML = message.replace(/\n/g, '<br>');
    infoDiv.classList.add('show');
    infoDiv.style.display = 'block';
  }

  // Log detailed stats for debugging
  console.log('Direct Connection Analysis:', {
    selectedNodes: info.selectedCount,
    directConnections: info.directConnectionCount,
    possibleConnections: info.possibleConnectionCount,
    density: info.connectionDensity,
    isolated: info.isolatedNodes,
    connectionMatrix: info.connectionMatrix
  });
}

// STEP 5: Update the clear function (stays mostly the same)
function clearMultiNodeHighlights() {
  // Reset all node styles
  nodeGroups.style("opacity", 1);
  nodeGroups.select("circle")
    .classed("highlight-node", false)
    .classed("selected-node", false)
    .classed("intermediate-node", false)
    .style("stroke-dasharray", "none")
    .style("stroke", d => d.type === 'institution' ? "#6d5a44" : "#546f7d")
    .style("stroke-width", 1);

  // Reset all edge styles
  d3.selectAll("line")
    .classed("highlight-path", false)
    .style("opacity", 0.3)
    .style("stroke-width", 1);

  // Hide info display
  const infoDiv = document.getElementById('connection-info') ||
                  document.getElementById('multi-node-info');
  if (infoDiv) {
    infoDiv.classList.remove('show');
    infoDiv.style.display = 'none';
  }

  // Clear input fields
  for (let i = 1; i <= 10; i++) {
    const input = document.getElementById(`node-input-${i}`) ||
                  document.getElementById(`node-${i}`);
    if (input) {
      input.value = '';
      input.classList.remove('has-value');
      const wrapper = input.closest('.node-input-wrapper');
      if (wrapper) wrapper.classList.remove('has-value');
    }
  }

  // Update any node counter if exists
  if (typeof updateNodeCounter === 'function') {
    updateNodeCounter();
  }
}

// STEP 6: Optional - Add CSS for isolated nodes
// Add this to your <style> section:
/*
.node.selected-node {
  stroke: #2ecc71;
  stroke-width: 3px;
}

.node.selected-node.isolated {
  stroke: #e74c3c;
  stroke-dasharray: 5,5;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { stroke-opacity: 1; }
  50% { stroke-opacity: 0.5; }
  100% { stroke-opacity: 1; }
}

.highlight-path {
  stroke: #2ecc71;
  stroke-width: 2px;
  stroke-opacity: 1;
}
*/

// STEP 7: Example of adding a toggle to switch between modes
function addModeToggle() {
  // Add this HTML to your controls:
  /*
  <div class="connection-mode-toggle">
    <label>
      <input type="radio" name="connection-mode" value="direct" checked>
      Direct Connections Only
    </label>
    <label>
      <input type="radio" name="connection-mode" value="full">
      Full Path Connections
    </label>
  </div>
  */

  // Store both finders
  window.directConnectionFinder = new MultiNodeConnectionFinder(data.nodes, data.links);
  window.fullConnectionFinder = createOriginalFinder(data.nodes, data.links); // Your original

  // Switch based on mode
  document.querySelectorAll('input[name="connection-mode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.value === 'direct') {
        window.multiNodeFinder = window.directConnectionFinder;
      } else {
        window.multiNodeFinder = window.fullConnectionFinder;
      }
      // Re-run the search if nodes are selected
      const hasSelection = Array.from({length: 10}, (_, i) => i + 1)
        .some(i => {
          const input = document.getElementById(`node-input-${i}`);
          return input && input.value.trim();
        });

      if (hasSelection) {
        handleFindMultiNodeConnections();
      }
    });
  });
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    handleFindMultiNodeConnections,
    displayDirectConnectionInfo,
    clearMultiNodeHighlights,
    addModeToggle
  };
}