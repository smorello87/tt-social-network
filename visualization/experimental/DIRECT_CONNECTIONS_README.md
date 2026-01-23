# Multi-Node Direct Connections Finder

## Overview

This is a modified version of the Multi-Node Connection Finder algorithm that shows **only direct connections** between selected nodes, rather than finding the full connecting subgraph (Steiner tree).

## Key Differences from Original

### Original Algorithm (Steiner Tree Approach)
- Shows minimal connecting subgraph linking all selected nodes
- **Includes intermediate nodes** on paths between selected nodes
- Displays **all edges** in the connecting tree
- Creates a fully connected network view
- Best for: Understanding how nodes are indirectly related

### New Algorithm (Direct Connections Only)
- Shows **only the selected nodes** themselves
- Displays **only direct edges** between selected nodes (where both source and target are selected)
- **Hides intermediate nodes** entirely
- Clearly identifies isolated nodes (selected nodes with no direct connections to other selected nodes)
- Best for: Understanding which nodes are directly connected to each other

## Visual Example

### Scenario: Select nodes A, B, C, D

**Original Algorithm (Steiner Tree):**
```
Shows: A --X-- B
       |       |
       Y       Z
       |       |
       C --W-- D

Highlights: A, B, C, D (selected) + X, Y, Z, W (intermediate)
Edges: A-X, X-B, A-Y, Y-C, B-Z, Z-D, C-W, W-D
```

**New Algorithm (Direct Only):**
```
Shows: A       B
       |
       C       D

Highlights: A, B, C, D (selected only)
Edges: A-C (only direct connection shown)
Isolated: B, D (marked with dashed outline)
```

## Features

### 1. Direct Edge Detection
- Identifies only edges where **both endpoints are in the selected set**
- No path-finding or intermediate node discovery
- O(n²) complexity for n selected nodes (very fast)

### 2. Isolated Node Detection
- Automatically identifies selected nodes with **zero direct connections** to other selected nodes
- Visual indicators: dashed red outline
- Listed separately in results

### 3. Connection Statistics
- **Selected nodes count**: How many nodes you selected
- **Direct connections count**: Number of edges between selected nodes
- **Connection density**: Percentage of possible connections that exist
  - Formula: `actual_edges / ((n * (n-1)) / 2)`
  - Example: 3 edges among 4 nodes = 3/6 = 50% density
- **Per-node connection count**: How many other selected nodes each connects to

### 4. Connection Matrix
- For small selections (≤5 nodes), displays a visual matrix
- Shows which nodes connect to which
- Green checkmark (✓) = direct connection exists
- Red X (✗) = no direct connection

### 5. Component Analysis
- Detects disconnected components in the selected subgraph
- Identifies which groups of selected nodes form connected clusters
- Useful for understanding selection structure

## Files Included

### 1. `multi_node_direct_connections.js`
**Main implementation file** - Drop-in replacement for the original MultiNodeConnectionFinder class.

**Key Methods:**
```javascript
// Constructor - same as original
constructor(nodes, links)

// Main method - same signature, different behavior
findMultiNodeConnections(selectedNodeIds)
  Returns: {
    nodes: [...],           // Only selected nodes
    links: [...],           // Only direct edges
    info: {
      type: 'direct_connections',
      selectedCount: number,
      directConnectionCount: number,
      connectionDensity: number,
      isolatedNodes: [...],
      nodeConnectionCounts: {...},
      connectionMatrix: {...}
    },
    selectedNodes: [...],   // For visualization
    error: string?          // If validation fails
  }

// Helper methods
findDirectConnections(nodeIds)
buildConnectionMatrix(nodeIds)
findComponents(nodeIds, directLinks)
```

### 2. `test_direct_connections.html`
**Standalone demo page** - Full visualization showing the new algorithm in action.

Features:
- 10 input fields for node selection
- Side-by-side comparison with original algorithm explanation
- Connection matrix display
- Isolated nodes highlighting
- Statistics dashboard
- Interactive D3.js visualization

### 3. `integration_example.js`
**Integration guide** - Shows how to integrate into your existing visualization.

Includes:
- Step-by-step replacement instructions
- Updated event handler code
- Enhanced styling classes
- Clear function updates
- Optional mode toggle implementation

## Integration Steps

### Quick Integration (Replace Existing)

1. **Include the new script:**
```html
<script src="multi_node_direct_connections.js"></script>
```

2. **Initialize (no changes needed):**
```javascript
// Works with same initialization
window.multiNodeFinder = new MultiNodeConnectionFinder(
  data.nodes,
  data.links
);
```

3. **Call the method (same name):**
```javascript
// Same method call, different results
const result = window.multiNodeFinder.findMultiNodeConnections(selectedNodes);
```

4. **Update visualization to handle isolated nodes:**
```javascript
const isolatedSet = new Set(result.info.isolatedNodes?.map(n => n.toLowerCase()) || []);

nodeGroups.select("circle")
  .style("stroke-dasharray", d =>
    isolatedSet.has(d.id.toLowerCase()) ? "5,5" : "none"
  )
  .style("stroke", d =>
    isolatedSet.has(d.id.toLowerCase()) ? "#e74c3c" : "#2ecc71"
  );
```

### Advanced Integration (Dual Mode)

Keep both algorithms and let users toggle:

```javascript
// Initialize both
window.directFinder = new DirectConnectionFinder(nodes, links);
window.fullFinder = new SteinerTreeFinder(nodes, links);

// Toggle
const mode = document.querySelector('input[name="mode"]:checked').value;
window.multiNodeFinder = (mode === 'direct') ? directFinder : fullFinder;
```

## CSS Styling

### Recommended Styles

```css
/* Selected nodes with connections */
.node.selected-node {
  stroke: #2ecc71;
  stroke-width: 3px;
}

/* Isolated selected nodes (no connections to other selected) */
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

/* Direct connection edges */
.link.highlighted {
  stroke: #2ecc71;
  stroke-width: 2px;
  stroke-opacity: 1;
}

/* Dimmed non-selected elements */
.node.dimmed { opacity: 0.1; }
.link.dimmed { stroke-opacity: 0.05; }
```

## Use Cases

### When to Use Direct Connections Only

1. **Cluster Analysis**: Find which nodes in a set are directly connected
2. **Collaboration Networks**: See who directly collaborated with whom
3. **Citation Analysis**: Identify direct citations between selected papers
4. **Social Networks**: Find direct friendships in a group
5. **Sparse Networks**: Better visualization when most nodes aren't connected

### When to Use Full Path Connections (Original)

1. **Relationship Discovery**: Understand how nodes are indirectly related
2. **Network Distance**: Visualize shortest paths between nodes
3. **Bridging Nodes**: Identify important intermediate connectors
4. **Dense Networks**: Better for highly connected graphs
5. **Complete Picture**: Need to see the full relationship structure

## Performance

### Complexity Analysis

**Direct Connections Algorithm:**
- Time: O(n² + m) where n = selected nodes, m = total edges
  - O(n²) to check all pairs of selected nodes
  - O(m) to build adjacency list once
- Space: O(n + m) for data structures
- Very fast even for large graphs (only depends on selection size)

**Original Steiner Tree Algorithm:**
- Time: O(n² × V) where V = total vertices in graph
  - Requires BFS/shortest path between all pairs
  - Tree optimization passes
- Space: O(V + E) for graph traversal
- Slower for large graphs, especially sparse ones

### Optimization Tips

1. **Adjacency list is pre-built** in constructor (one-time cost)
2. **Direct edge map** provides O(1) lookup
3. **Set operations** for fast membership checking
4. **No recursive algorithms** - all iterative
5. **Minimal graph traversal** - only touches selected nodes

## API Reference

### Input Format

```javascript
// Selected node IDs (case-insensitive)
const selectedNodeIds = [
  'Node A',
  'Node B',
  'Node C'
];
```

### Return Format

```javascript
{
  // Array of selected node IDs (normalized to lowercase)
  nodes: ['node a', 'node b', 'node c'],

  // Array of [source, target] pairs for direct edges
  links: [
    ['node a', 'node b'],
    ['node b', 'node c']
  ],

  // Detailed information object
  info: {
    type: 'direct_connections',
    selectedCount: 3,
    directConnectionCount: 2,
    possibleConnectionCount: 3,  // n*(n-1)/2
    connectionDensity: 0.67,      // 2/3 = 67%
    isolatedNodes: [],
    isolatedCount: 0,

    // Per-node connection counts
    nodeConnectionCounts: {
      'node a': 1,  // connects to 1 other selected node
      'node b': 2,  // connects to 2 other selected nodes
      'node c': 1
    },

    // Connection matrix
    connectionMatrix: {
      'node a': {
        'node b': true,
        'node c': false
      },
      'node b': {
        'node a': true,
        'node c': true
      },
      'node c': {
        'node a': false,
        'node b': true
      }
    },

    // Human-readable message
    message: 'Selected 3 nodes with 2 direct connections (67% density)'
  },

  // For visualization highlighting
  selectedNodes: ['node a', 'node b', 'node c'],

  // Error message if validation fails
  error: null
}
```

### Error Cases

```javascript
// No nodes selected
{ nodes: [], links: [], error: 'No valid nodes selected' }

// Too many nodes (max 10)
{ nodes: [], links: [], error: 'Maximum 10 nodes allowed' }

// Nodes not found in graph
{ nodes: [], links: [], error: 'Nodes not found: invalid1, invalid2' }
```

## Testing

### Test with Demo Page

1. Start local server:
```bash
cd visualization
python3 -m http.server 8080
```

2. Open in browser:
```
http://localhost:8080/test_direct_connections.html
```

3. Try different selections:
   - **Single node**: Shows just that node (no edges)
   - **Two connected nodes**: Shows both nodes and the edge
   - **Two disconnected nodes**: Shows both as isolated
   - **Triangle (3 nodes all connected)**: Shows 100% density
   - **Star pattern (1 hub + others)**: Shows hub with high count, others with 1

### Example Test Cases

```javascript
// Test 1: Fully connected triangle
selectedNodes = ['A', 'B', 'C']
// Expected: 3 edges, 100% density

// Test 2: Star pattern
selectedNodes = ['Hub', 'Spoke1', 'Spoke2', 'Spoke3']
// Expected: 3 edges (hub to each spoke), 50% density
// Hub: 3 connections, Spokes: 1 connection each

// Test 3: Disconnected nodes
selectedNodes = ['Island1', 'Island2', 'Island3']
// Expected: 0 edges, 0% density, all isolated

// Test 4: Two components
selectedNodes = ['A', 'B', 'C', 'D']  // where A-B connected, C-D connected
// Expected: 2 edges, 33% density, 2 components
```

## Troubleshooting

### Issue: No edges showing
- **Check:** Are the nodes actually directly connected?
- **Solution:** Use `console.log(result.info.connectionMatrix)` to see the matrix

### Issue: Nodes marked as isolated incorrectly
- **Check:** Case sensitivity - all IDs normalized to lowercase
- **Solution:** Verify node IDs match graph data exactly

### Issue: Performance slow
- **Check:** Graph initialization only happens once
- **Solution:** Don't re-create MultiNodeConnectionFinder on every call

### Issue: Visualization not updating
- **Check:** Are you using the result.nodes and result.links correctly?
- **Solution:** Ensure edgeSet includes both directions for undirected graphs

## Future Enhancements

Possible additions to the algorithm:

1. **Path hints**: Show indirect connection count (e.g., "A→B via 3 nodes")
2. **Common neighbors**: List nodes connected to multiple selected nodes
3. **Degree statistics**: Show how connected each node is in full graph
4. **Export to CSV/JSON**: Save the connection matrix
5. **Weighted edges**: Support edge weights if available
6. **Directed graphs**: Handle asymmetric connections
7. **Temporal filtering**: Filter by date range if time data available
8. **Subgraph export**: Extract just the selected nodes as a new graph

## Questions?

For integration help or issues:
1. Check `integration_example.js` for detailed code samples
2. Run `test_direct_connections.html` to see it working
3. Compare your code with the example implementations
4. Verify data format matches expected input structure

## Summary

This direct connections finder provides a cleaner, simpler view of multi-node relationships by showing only what's directly connected. It's ideal for:
- Understanding direct relationships in a selection
- Identifying isolated nodes quickly
- Analyzing connection density in subgroups
- Fast visualization of sparse networks

Use the original Steiner tree algorithm when you need to see the full connecting structure including intermediate nodes.