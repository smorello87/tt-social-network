/**
 * MultiNodeConnectionFinder - Direct Connections Only Version
 *
 * This modified version shows ONLY:
 * - The selected nodes (highlighted)
 * - Direct edges between selected nodes (no intermediate paths)
 * - All other nodes and edges are dimmed/hidden
 */
class MultiNodeConnectionFinder {
  constructor(nodes, links) {
    this.nodes = nodes;
    this.links = links;
    this.adjacencyList = this.buildAdjacencyList();
    this.nodeMap = new Map();
    this.nodes.forEach(node => {
      this.nodeMap.set(node.id.toLowerCase(), node);
    });
    // Store direct edges for quick lookup
    this.directEdges = new Map();
    this.buildDirectEdges();
  }

  buildAdjacencyList() {
    const adj = new Map();
    this.nodes.forEach(node => {
      adj.set(node.id.toLowerCase(), new Set());
    });
    this.links.forEach(link => {
      const source = (typeof link.source === 'object')
        ? link.source.id.toLowerCase()
        : String(link.source).toLowerCase();
      const target = (typeof link.target === 'object')
        ? link.target.id.toLowerCase()
        : String(link.target).toLowerCase();

      if (adj.has(source) && adj.has(target)) {
        adj.get(source).add(target);
        adj.get(target).add(source);
      }
    });
    return adj;
  }

  buildDirectEdges() {
    // Build a map of direct edges for quick lookup
    this.links.forEach(link => {
      const source = (typeof link.source === 'object')
        ? link.source.id.toLowerCase()
        : String(link.source).toLowerCase();
      const target = (typeof link.target === 'object')
        ? link.target.id.toLowerCase()
        : String(link.target).toLowerCase();

      // Store bidirectionally for easy lookup
      const key1 = `${source}-${target}`;
      const key2 = `${target}-${source}`;
      this.directEdges.set(key1, true);
      this.directEdges.set(key2, true);
    });
  }

  /**
   * Find direct connections between selected nodes only
   * @param {Array} selectedNodeIds - Array of node IDs (1-10 nodes)
   * @returns {Object} Result with nodes, links, and info
   */
  findMultiNodeConnections(selectedNodeIds) {
    // Validate and normalize input
    const validNodeIds = selectedNodeIds
      .filter(id => id && id.trim())
      .map(id => id.trim().toLowerCase())
      .filter((id, index, self) => self.indexOf(id) === index); // Remove duplicates

    // Validation checks
    if (validNodeIds.length === 0) {
      return {
        nodes: [],
        links: [],
        error: 'No valid nodes selected',
        info: { type: 'error', message: 'No valid nodes selected' }
      };
    }

    if (validNodeIds.length > 10) {
      return {
        nodes: [],
        links: [],
        error: 'Maximum 10 nodes allowed',
        info: { type: 'error', message: 'Maximum 10 nodes allowed' }
      };
    }

    // Check if all nodes exist in the graph
    const missingNodes = validNodeIds.filter(id => !this.adjacencyList.has(id));
    if (missingNodes.length > 0) {
      return {
        nodes: [],
        links: [],
        error: `Nodes not found: ${missingNodes.join(', ')}`,
        info: { type: 'error', message: `Nodes not found: ${missingNodes.join(', ')}` }
      };
    }

    // Find direct connections between selected nodes
    return this.findDirectConnections(validNodeIds);
  }

  /**
   * Find only direct edges between selected nodes
   */
  findDirectConnections(nodeIds) {
    const selectedSet = new Set(nodeIds);
    const directLinks = [];
    const connectedPairs = new Set();
    const isolatedNodes = new Set(nodeIds);

    // Find all direct edges between selected nodes
    for (let i = 0; i < nodeIds.length; i++) {
      for (let j = i + 1; j < nodeIds.length; j++) {
        const node1 = nodeIds[i];
        const node2 = nodeIds[j];

        // Check if there's a direct edge between these nodes
        if (this.adjacencyList.get(node1).has(node2)) {
          directLinks.push([node1, node2]);
          connectedPairs.add(`${node1}-${node2}`);
          // Remove from isolated nodes set
          isolatedNodes.delete(node1);
          isolatedNodes.delete(node2);
        }
      }
    }

    // Calculate statistics
    const nodeConnectionCounts = new Map();
    nodeIds.forEach(nodeId => {
      nodeConnectionCounts.set(nodeId, 0);
    });

    directLinks.forEach(([source, target]) => {
      nodeConnectionCounts.set(source, nodeConnectionCounts.get(source) + 1);
      nodeConnectionCounts.set(target, nodeConnectionCounts.get(target) + 1);
    });

    // Find nodes with no connections to other selected nodes
    const unconnectedNodes = nodeIds.filter(nodeId =>
      nodeConnectionCounts.get(nodeId) === 0
    );

    // Build connection matrix for detailed info
    const connectionMatrix = this.buildConnectionMatrix(nodeIds);

    // Prepare detailed info
    const info = {
      type: 'direct_connections',
      selectedCount: nodeIds.length,
      directConnectionCount: directLinks.length,
      possibleConnectionCount: (nodeIds.length * (nodeIds.length - 1)) / 2,
      connectionDensity: nodeIds.length > 1
        ? (directLinks.length / ((nodeIds.length * (nodeIds.length - 1)) / 2)).toFixed(2)
        : 0,
      isolatedNodes: Array.from(isolatedNodes),
      isolatedCount: isolatedNodes.size,
      nodeConnectionCounts: Object.fromEntries(nodeConnectionCounts),
      connectionMatrix: connectionMatrix
    };

    // Generate descriptive message
    let message = '';
    if (nodeIds.length === 1) {
      message = `Selected 1 node: ${nodeIds[0]}`;
    } else if (directLinks.length === 0) {
      message = `Selected ${nodeIds.length} nodes, but they have no direct connections to each other`;
    } else {
      const density = (info.connectionDensity * 100).toFixed(0);
      message = `Selected ${nodeIds.length} nodes with ${directLinks.length} direct connection${directLinks.length !== 1 ? 's' : ''} (${density}% density)`;

      if (isolatedNodes.size > 0) {
        const isolatedList = Array.from(isolatedNodes).slice(0, 3).join(', ');
        const moreText = isolatedNodes.size > 3 ? ` and ${isolatedNodes.size - 3} more` : '';
        message += `. Isolated nodes: ${isolatedList}${moreText}`;
      }
    }
    info.message = message;

    return {
      nodes: nodeIds,  // Only return the selected nodes
      links: directLinks,  // Only direct connections between selected nodes
      info: info,
      selectedNodes: nodeIds  // For visualization highlighting
    };
  }

  /**
   * Build a connection matrix showing which selected nodes connect to each other
   */
  buildConnectionMatrix(nodeIds) {
    const matrix = {};

    nodeIds.forEach(node1 => {
      matrix[node1] = {};
      nodeIds.forEach(node2 => {
        if (node1 !== node2) {
          matrix[node1][node2] = this.adjacencyList.get(node1).has(node2);
        }
      });
    });

    return matrix;
  }

  /**
   * Get detailed statistics about the selected nodes
   */
  getDetailedStats(nodeIds, directLinks) {
    // Count total edges each selected node has in the full graph
    const globalDegrees = {};
    nodeIds.forEach(nodeId => {
      globalDegrees[nodeId] = this.adjacencyList.get(nodeId).size;
    });

    // Find common neighbors (nodes connected to multiple selected nodes)
    const commonNeighbors = this.findCommonNeighbors(nodeIds);

    return {
      globalDegrees: globalDegrees,
      commonNeighbors: commonNeighbors,
      avgGlobalDegree: (Object.values(globalDegrees).reduce((a, b) => a + b, 0) / nodeIds.length).toFixed(1)
    };
  }

  /**
   * Find nodes that are connected to multiple selected nodes (but not selected themselves)
   */
  findCommonNeighbors(nodeIds) {
    const selectedSet = new Set(nodeIds);
    const neighborCounts = new Map();

    nodeIds.forEach(nodeId => {
      this.adjacencyList.get(nodeId).forEach(neighbor => {
        if (!selectedSet.has(neighbor)) {
          neighborCounts.set(neighbor, (neighborCounts.get(neighbor) || 0) + 1);
        }
      });
    });

    // Filter to only include nodes connected to 2+ selected nodes
    const commonNeighbors = [];
    neighborCounts.forEach((count, neighbor) => {
      if (count >= 2) {
        commonNeighbors.push({
          id: neighbor,
          connectedToCount: count,
          connectedTo: nodeIds.filter(nodeId =>
            this.adjacencyList.get(nodeId).has(neighbor)
          )
        });
      }
    });

    // Sort by number of connections
    commonNeighbors.sort((a, b) => b.connectedToCount - a.connectedToCount);

    return commonNeighbors.slice(0, 10); // Return top 10 common neighbors
  }

  /**
   * Helper method to check if nodes form a connected component
   */
  isConnectedComponent(nodeIds, directLinks) {
    if (nodeIds.length <= 1) return true;

    // Build adjacency for just the selected nodes
    const subgraph = new Map();
    nodeIds.forEach(id => subgraph.set(id, new Set()));

    directLinks.forEach(([source, target]) => {
      subgraph.get(source).add(target);
      subgraph.get(target).add(source);
    });

    // BFS to check connectivity
    const visited = new Set();
    const queue = [nodeIds[0]];
    visited.add(nodeIds[0]);

    while (queue.length > 0) {
      const current = queue.shift();
      subgraph.get(current).forEach(neighbor => {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      });
    }

    return visited.size === nodeIds.length;
  }

  /**
   * Find connected components among selected nodes
   */
  findComponents(nodeIds, directLinks) {
    const subgraph = new Map();
    nodeIds.forEach(id => subgraph.set(id, new Set()));

    directLinks.forEach(([source, target]) => {
      subgraph.get(source).add(target);
      subgraph.get(target).add(source);
    });

    const visited = new Set();
    const components = [];

    nodeIds.forEach(nodeId => {
      if (!visited.has(nodeId)) {
        const component = [];
        const queue = [nodeId];
        visited.add(nodeId);

        while (queue.length > 0) {
          const current = queue.shift();
          component.push(current);

          subgraph.get(current).forEach(neighbor => {
            if (!visited.has(neighbor)) {
              visited.add(neighbor);
              queue.push(neighbor);
            }
          });
        }

        components.push(component);
      }
    });

    return components;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MultiNodeConnectionFinder;
}