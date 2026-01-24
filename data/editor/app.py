#!/usr/bin/env python3
"""
Flask server for the network data editor.
Serves both the editor UI and the visualization API.
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import database as db

app = Flask(__name__)
CORS(app)

# Serve visualization files
VISUALIZATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'visualization'))

# =============================================================================
# Frontend Routes
# =============================================================================

@app.route('/')
def editor():
    """Serve the data editor UI."""
    return render_template('editor.html')

@app.route('/visualization/')
def serve_visualization_index():
    """Serve visualization index."""
    return send_from_directory(VISUALIZATION_DIR, 'index.html')

@app.route('/visualization/<path:filename>')
def serve_visualization(filename):
    """Serve visualization files."""
    return send_from_directory(VISUALIZATION_DIR, filename)

# =============================================================================
# Graph JSON API (for visualization)
# =============================================================================

@app.route('/api/graph.json')
def graph_json():
    """Get graph data for visualization (same format as static graph.json)."""
    return jsonify(db.get_graph_json())

@app.route('/api/export-graph', methods=['POST'])
def export_graph():
    """Export graph.json to visualization directory from database."""
    import json
    data = db.get_graph_json()
    output_path = os.path.join(VISUALIZATION_DIR, 'graph.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({'success': True, 'nodes': len(data['nodes']), 'links': len(data['links'])})

# =============================================================================
# Node API
# =============================================================================

@app.route('/api/nodes', methods=['GET'])
def list_nodes():
    """List nodes with optional filtering, sorting, and pagination."""
    type_filter = request.args.get('type')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    sort_by = request.args.get('sort_by')
    sort_dir = request.args.get('sort_dir', 'desc')

    result = db.get_nodes(
        type_filter=type_filter,
        search=search,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_dir=sort_dir
    )
    return jsonify(result)

@app.route('/api/nodes/all', methods=['GET'])
def all_nodes_dropdown():
    """Get all nodes for dropdown/autocomplete (lightweight)."""
    return jsonify(db.get_all_nodes_for_dropdown())

@app.route('/api/nodes/<int:node_id>', methods=['GET'])
def get_node(node_id):
    """Get single node by ID."""
    node = db.get_node(node_id)
    if node:
        return jsonify(node)
    return jsonify({'error': 'Node not found'}), 404

@app.route('/api/nodes', methods=['POST'])
def create_node():
    """Create a new node."""
    data = request.json
    name = data.get('name', '').strip()
    node_type = data.get('type', 'unknown')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    if node_type not in ('person', 'institution', 'unknown'):
        return jsonify({'error': 'Invalid type'}), 400

    # Check if node already exists
    existing = db.get_node_by_name(name)
    if existing:
        return jsonify({'error': 'Node already exists', 'existing': existing}), 409

    try:
        node_id = db.create_node(name, node_type)
        return jsonify({'id': node_id, 'name': name, 'type': node_type}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    """Update a node."""
    data = request.json
    name = data.get('name')
    node_type = data.get('type')

    if node_type and node_type not in ('person', 'institution', 'unknown'):
        return jsonify({'error': 'Invalid type'}), 400

    try:
        db.update_node(node_id, name=name, node_type=node_type)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Delete a node."""
    try:
        db.delete_node(node_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes/<int:node_id>/connections', methods=['GET'])
def get_node_connections(node_id):
    """Get all nodes connected to a given node."""
    connections = db.get_node_connections(node_id)
    return jsonify(connections)

@app.route('/api/nodes/merge', methods=['POST'])
def merge_nodes():
    """Merge two nodes: transfer edges from secondary to primary, delete secondary."""
    data = request.json
    primary_id = data.get('primary_id')
    secondary_id = data.get('secondary_id')

    if not primary_id or not secondary_id:
        return jsonify({'error': 'primary_id and secondary_id are required'}), 400

    try:
        result = db.merge_nodes(primary_id, secondary_id)
        return jsonify({
            'success': True,
            'primary_name': result['primary_name'],
            'secondary_name': result['secondary_name'],
            'edges_transferred': result['edges_transferred']
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Edge API
# =============================================================================

@app.route('/api/edges', methods=['GET'])
def list_edges():
    """List edges with optional filtering, sorting, and pagination."""
    type_filter = request.args.get('type')
    needs_review = request.args.get('needs_review')
    source_type = request.args.get('source_type')
    target_type = request.args.get('target_type')
    min_shared = request.args.get('min_shared')
    max_shared = request.args.get('max_shared')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    sort_by = request.args.get('sort_by')
    sort_dir = request.args.get('sort_dir', 'desc')

    # Convert needs_review to boolean
    if needs_review is not None:
        needs_review = needs_review.lower() in ('true', '1', 'yes')

    result = db.get_edges(
        type_filter=type_filter,
        needs_review=needs_review,
        source_type=source_type,
        target_type=target_type,
        min_shared=min_shared,
        max_shared=max_shared,
        search=search,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_dir=sort_dir
    )
    return jsonify(result)

@app.route('/api/edges/<int:edge_id>', methods=['GET'])
def get_edge(edge_id):
    """Get single edge with shared institutions."""
    edge = db.get_edge(edge_id)
    if edge:
        return jsonify(edge)
    return jsonify({'error': 'Edge not found'}), 404

@app.route('/api/edges', methods=['POST'])
def create_edge():
    """Create a new edge."""
    data = request.json
    source_id = data.get('source_id')
    target_id = data.get('target_id')
    edge_type = data.get('type', 'affiliation')

    if not source_id or not target_id:
        return jsonify({'error': 'source_id and target_id are required'}), 400

    if edge_type not in ('personal', 'affiliation', 'unknown'):
        return jsonify({'error': 'Invalid type'}), 400

    try:
        edge_id = db.create_edge(source_id, target_id, edge_type)
        return jsonify({'id': edge_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/edges/<int:edge_id>', methods=['PUT'])
def update_edge(edge_id):
    """Update an edge."""
    data = request.json
    source_id = data.get('source_id')
    target_id = data.get('target_id')
    edge_type = data.get('type')
    needs_review = data.get('needs_review')

    if edge_type and edge_type not in ('personal', 'affiliation', 'unknown'):
        return jsonify({'error': 'Invalid type'}), 400

    try:
        db.update_edge(edge_id, source_id=source_id, target_id=target_id,
                       edge_type=edge_type, needs_review=needs_review)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/edges/<int:edge_id>', methods=['DELETE'])
def delete_edge(edge_id):
    """Delete an edge."""
    try:
        db.delete_edge(edge_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Batch Operations API
# =============================================================================

@app.route('/api/batch/edges/type', methods=['POST'])
def batch_update_type():
    """Set type for multiple edges."""
    data = request.json
    edge_ids = data.get('edge_ids', [])
    edge_type = data.get('type')

    if not edge_ids:
        return jsonify({'error': 'edge_ids is required'}), 400

    if edge_type not in ('personal', 'affiliation', 'unknown'):
        return jsonify({'error': 'Invalid type'}), 400

    try:
        count = db.batch_update_edge_type(edge_ids, edge_type)
        return jsonify({'updated': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch/edges/reviewed', methods=['POST'])
def batch_mark_reviewed():
    """Mark multiple edges as reviewed."""
    data = request.json
    edge_ids = data.get('edge_ids', [])
    reviewed = data.get('reviewed', True)

    if not edge_ids:
        return jsonify({'error': 'edge_ids is required'}), 400

    try:
        count = db.batch_mark_reviewed(edge_ids, reviewed)
        return jsonify({'updated': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch/edges/create', methods=['POST'])
def batch_create_edges():
    """Create edges from multiple source nodes to one target."""
    data = request.json
    source_ids = data.get('source_ids', [])
    target_id = data.get('target_id')
    edge_type = data.get('type', 'affiliation')

    if not source_ids or not target_id:
        return jsonify({'error': 'source_ids and target_id are required'}), 400

    if edge_type not in ('personal', 'affiliation', 'unknown'):
        return jsonify({'error': 'Invalid type'}), 400

    try:
        created = db.batch_create_edges(source_ids, target_id, edge_type)
        return jsonify({'created': len(created), 'edge_ids': created})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch/edges/delete', methods=['POST'])
def batch_delete_edges():
    """Delete multiple edges."""
    data = request.json
    edge_ids = data.get('edge_ids', [])

    if not edge_ids:
        return jsonify({'error': 'edge_ids is required'}), 400

    try:
        count = db.batch_delete_edges(edge_ids)
        return jsonify({'deleted': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Import/Export API
# =============================================================================

@app.route('/api/import/csv', methods=['POST'])
def import_csv():
    """Import data from CSV files (uploaded or from disk)."""
    import csv
    import io
    import re

    def normalize_name(name):
        name = name.strip()
        name = re.sub(r"\s+", " ", name)
        return name.lower()

    nodes_data = []
    edges_data = []

    # Check if files were uploaded
    if 'types_file' in request.files and 'edges_file' in request.files:
        types_file = request.files['types_file']
        edges_file = request.files['edges_file']

        # Parse types file
        types_content = types_file.read().decode('utf-8-sig')
        reader = csv.reader(io.StringIO(types_content))
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2:
                nodes_data.append({'name': row[0].strip(), 'type': row[1].strip().lower()})

        # Parse edges file
        edges_content = edges_file.read().decode('utf-8-sig')
        reader = csv.reader(io.StringIO(edges_content))
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2:
                edge_type = row[2].strip() if len(row) >= 3 else 'affiliation'
                edges_data.append({
                    'source': row[0].strip(),
                    'target': row[1].strip(),
                    'type': edge_type if edge_type in ('personal', 'affiliation') else 'affiliation'
                })
    else:
        # Import from disk (default paths)
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        types_path = os.path.join(data_dir, 'type1.csv')
        edges_path = os.path.join(data_dir, 'singlerows.csv')

        if not os.path.exists(types_path) or not os.path.exists(edges_path):
            return jsonify({'error': 'CSV files not found on disk. Please upload files.'}), 400

        # Read types file
        with open(types_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    nodes_data.append({'name': row[0].strip(), 'type': row[1].strip().lower()})

        # Read edges file
        with open(edges_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    edge_type = row[2].strip() if len(row) >= 3 else 'affiliation'
                    edges_data.append({
                        'source': row[0].strip(),
                        'target': row[1].strip(),
                        'type': edge_type if edge_type in ('personal', 'affiliation') else 'affiliation'
                    })

    # Import into database
    nodes_created = 0
    edges_created = 0
    name_to_id = {}

    # Create nodes
    for node in nodes_data:
        node_type = node['type'] if node['type'] in ('person', 'institution') else 'unknown'
        try:
            node_id = db.create_node(node['name'], node_type)
            name_to_id[normalize_name(node['name'])] = node_id
            nodes_created += 1
        except:
            # Node might already exist
            existing = db.get_node_by_name(node['name'])
            if existing:
                name_to_id[normalize_name(node['name'])] = existing['id']

    # Create edges
    for edge in edges_data:
        source_norm = normalize_name(edge['source'])
        target_norm = normalize_name(edge['target'])

        # Get or create source node
        if source_norm not in name_to_id:
            existing = db.get_node_by_name(edge['source'])
            if existing:
                name_to_id[source_norm] = existing['id']
            else:
                node_id = db.create_node(edge['source'], 'unknown')
                name_to_id[source_norm] = node_id
                nodes_created += 1

        # Get or create target node
        if target_norm not in name_to_id:
            existing = db.get_node_by_name(edge['target'])
            if existing:
                name_to_id[target_norm] = existing['id']
            else:
                node_id = db.create_node(edge['target'], 'unknown')
                name_to_id[target_norm] = node_id
                nodes_created += 1

        # Create edge
        try:
            db.create_edge(name_to_id[source_norm], name_to_id[target_norm], edge['type'])
            edges_created += 1
        except:
            pass  # Edge might already exist

    return jsonify({
        'success': True,
        'nodes_created': nodes_created,
        'edges_created': edges_created
    })

@app.route('/api/recalculate', methods=['POST'])
def recalculate_shared():
    """Recalculate all shared institutions and needs_review flags."""
    try:
        count = db.recalculate_all_shared_institutions()
        return jsonify({'success': True, 'edges_processed': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Statistics API
# =============================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get network statistics."""
    return jsonify(db.get_stats())

# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Network Data Editor")
    print("="*60)
    print("\nEditor:        http://localhost:5001")
    print("Visualization: http://localhost:5001/visualization/")
    print("API:           http://localhost:5001/api/graph.json")
    print("\n" + "="*60 + "\n")
    app.run(debug=False, port=5001, threaded=True)
