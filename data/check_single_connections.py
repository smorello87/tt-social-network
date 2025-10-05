#!/usr/bin/env python3
"""
Find entries that are connected to exactly one other entry in the network.
"""

import csv
from collections import defaultdict
import sys

def find_single_connections(edges_file='singlerows.csv'):
    """
    Identify nodes that have exactly one connection in the network.
    """
    # Track connections for each node
    connections = defaultdict(set)

    # Read edges file with encoding detection
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1', 'mac_roman']

    for encoding in encodings:
        try:
            with open(edges_file, 'r', encoding=encoding) as f:
                reader = csv.reader(f)

                # Skip header if present
                first_row = next(reader, None)
                if first_row and first_row[0].lower() == 'entry':
                    pass  # Header row, already skipped
                else:
                    # Not a header, process it
                    if first_row and len(first_row) >= 2:
                        source = first_row[0].strip()
                        target = first_row[1].strip()
                        if source and target:
                            connections[source].add(target)
                            connections[target].add(source)

                # Process remaining rows
                for row in reader:
                    if len(row) >= 2:
                        source = row[0].strip()
                        target = row[1].strip()
                        if source and target:
                            connections[source].add(target)
                            connections[target].add(source)
                break  # Success, exit encoding loop

        except UnicodeDecodeError:
            if encoding == encodings[-1]:
                print(f"Error: Could not decode {edges_file} with any known encoding")
                sys.exit(1)
            continue
        except FileNotFoundError:
            print(f"Error: Could not find {edges_file}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

    # Find nodes with exactly one connection
    single_connection_nodes = []
    for node, connected_to in connections.items():
        if len(connected_to) == 1:
            single_connection_nodes.append((node, list(connected_to)[0]))

    # Sort alphabetically
    single_connection_nodes.sort(key=lambda x: x[0].lower())

    # Display results
    print(f"\n{'='*70}")
    print(f"NODES WITH EXACTLY ONE CONNECTION")
    print(f"{'='*70}\n")

    if single_connection_nodes:
        print(f"Found {len(single_connection_nodes)} entries with only one connection:\n")

        # Group by their single connection for easier review
        by_connection = defaultdict(list)
        for node, connected_to in single_connection_nodes:
            by_connection[connected_to].append(node)

        # Display grouped results
        print("Grouped by their connection:\n")
        for hub, leaves in sorted(by_connection.items(), key=lambda x: (-len(x[1]), x[0].lower())):
            if len(leaves) > 1:
                print(f"\n'{hub}' is the only connection for {len(leaves)} nodes:")
                for leaf in sorted(leaves, key=str.lower):
                    print(f"  - {leaf}")

        print("\n" + "-"*70 + "\n")
        print("Individual list:\n")
        for node, connected_to in single_connection_nodes:
            print(f"  '{node}' → '{connected_to}'")
    else:
        print("No entries found with exactly one connection.")

    print(f"\n{'='*70}")
    print(f"Total nodes in network: {len(connections)}")
    print(f"Nodes with 1 connection: {len(single_connection_nodes)}")
    print(f"Percentage: {len(single_connection_nodes)/len(connections)*100:.1f}%")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        find_single_connections(sys.argv[1])
    else:
        find_single_connections()