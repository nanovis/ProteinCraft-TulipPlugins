#!/usr/bin/env python3

import sys
import os
import csv
import importlib.util
from pathlib import Path

# ------------------------------
#  1) Load needed modules
# ------------------------------

# We load RINGImport from ../import/RINGImport.py
ring_import_path = Path("../import/RINGImport.py")
ring_spec = importlib.util.spec_from_file_location("RINGImport", ring_import_path)
RINGImport = importlib.util.module_from_spec(ring_spec)
sys.modules["RINGImport"] = RINGImport
ring_spec.loader.exec_module(RINGImport)
create_ring_graph = RINGImport.create_ring_graph

# We load BinderIntraInteraction
binder_intra_path = Path("../layout/BinderIntraInteraction.py")
binder_intra_spec = importlib.util.spec_from_file_location("BinderIntraInteraction", binder_intra_path)
BinderIntraInteraction = importlib.util.module_from_spec(binder_intra_spec)
sys.modules["BinderIntraInteraction"] = BinderIntraInteraction
binder_intra_spec.loader.exec_module(BinderIntraInteraction)
generate_subgraphs = BinderIntraInteraction.generate_subgraphs

# We load BinderTargetInteraction
binder_target_path = Path("../layout/BinderTargetInteraction.py")
binder_target_spec = importlib.util.spec_from_file_location("BinderTargetInteraction", binder_target_path)
BinderTargetInteraction = importlib.util.module_from_spec(binder_target_spec)
sys.modules["BinderTargetInteraction"] = BinderTargetInteraction
binder_target_spec.loader.exec_module(BinderTargetInteraction)
identify_interacting_nodes = BinderTargetInteraction.identify_interacting_nodes
create_interaction_subgraph = BinderTargetInteraction.create_interaction_subgraph

# Tulip
try:
    from tulip import tlp
except ImportError as e:
    print("ERROR: The Tulip Python bindings are required but not found.")
    sys.exit(1)

# ------------------------------
#  2) Define functions
# ------------------------------

def parse_score_file(input_path):
    """
    Reads a file of lines starting with 'SCORE:'
    and returns a tuple (header, rows).

    header: list of column names
    rows: list of lists, each row matching the header
    """
    header = []
    rows = []
    with open(input_path, 'r') as infile:
        for line in infile:
            if line.strip().startswith("SCORE:"):
                parts = line.replace("SCORE:", "").split()
                # If all parts are non-numeric => header
                # (Note: we consider float-like to be numeric too)
                if all(not p.replace('.', '', 1).isdigit() for p in parts):
                    header = parts
                else:
                    rows.append(parts)

    # If no header found, define a default
    if not header:
        header = [
            "binder_aligned_rmsd",
            "pae_binder",
            "pae_interaction",
            "pae_target",
            "plddt_binder",
            "plddt_target",
            "plddt_total",
            "target_aligned_rmsd",
            "time",
            "description"
        ]

    return header, rows


def count_interactions(graph):
    """
    Count various interaction metrics from the RING graph.
    """
    chainProp = graph.getStringProperty("chain")
    interactionProp = graph.getStringProperty("interaction")

    counts = {
        'inter_chain_total': 0,
        'inter_chain_vdw': 0,
        'inter_chain_hbond': 0,
        'inter_chain_other': 0,
        'binder_components_bonds': 0,
        'binder_components_bonds_without_vdw': 0
    }

    # 1) Count inter-chain interactions
    for edge in graph.getEdges():
        n1, n2 = graph.source(edge), graph.target(edge)
        chain1 = chainProp[n1]
        chain2 = chainProp[n2]
        if chain1 != chain2:
            counts['inter_chain_total'] += 1
            inter_type = interactionProp[edge]
            if inter_type.startswith("VDW"):
                counts['inter_chain_vdw'] += 1
            elif inter_type.startswith("HBOND"):
                counts['inter_chain_hbond'] += 1
            else:
                counts['inter_chain_other'] += 1

    counts['inter_chain_without_vdw'] = (
        counts['inter_chain_total'] - counts['inter_chain_vdw']
    )

    # 2) Count binder-components bonds
    subgraphs = generate_subgraphs(graph, include_vdw=True)
    for subg in subgraphs:
        for _ in subg.getEdges():
            counts['binder_components_bonds'] += 1
        for edge in subg.getEdges():
            if not interactionProp[edge].startswith("VDW"):
                counts['binder_components_bonds_without_vdw'] += 1

    # 3) Binder <-> Target (with VDW)
    binder_list, target_list = identify_interacting_nodes(graph, include_vdw=True)
    binder_target_sub = create_interaction_subgraph(graph, binder_list, target_list, include_vdw=True)
    counts['binder_target_bonds'] = binder_target_sub.numberOfEdges()

    connected_components = tlp.ConnectedTest.computeConnectedComponents(binder_target_sub)
    if connected_components:
        largest = max(connected_components, key=len)
        counts['binder_target_bonds_largest_component'] = len(largest)
    else:
        counts['binder_target_bonds_largest_component'] = 0

    # 4) Binder <-> Target (no VDW)
    binder_list, target_list = identify_interacting_nodes(graph, include_vdw=False)
    binder_target_sub = create_interaction_subgraph(graph, binder_list, target_list, include_vdw=False)
    counts['binder_target_bonds_no_vdw'] = binder_target_sub.numberOfEdges()

    connected_components = tlp.ConnectedTest.computeConnectedComponents(binder_target_sub)
    if connected_components:
        largest = max(connected_components, key=len)
        counts['binder_target_bonds_no_vdw_largest_component'] = len(largest)
    else:
        counts['binder_target_bonds_no_vdw_largest_component'] = 0

    return counts


def main():
    """
    Usage:
        python combined_af2ig_ring_metrics.py <score_file.txt> <output_file.csv> <ring_folder>

    Example:
        python combined_af2ig_ring_metrics.py input_score.txt output.csv /path/to/RING_folder
    """
    if len(sys.argv) < 4:
        print("Usage: python combined_af2ig_ring_metrics.py <score_file.txt> <output_file.csv> <ring_folder>")
        sys.exit(1)

    score_input = sys.argv[1]
    csv_output = sys.argv[2]
    ring_folder = sys.argv[3]

    # ------------------------------
    # Parse the AF2ig score file
    # ------------------------------
    header, rows = parse_score_file(score_input)

    # For convenience, let's map the columns into a dictionary
    # so we can easily handle them by name. We'll also keep track
    # of the final extended columns (ring metrics).
    ring_metric_names = [
        'inter_chain_total',
        'inter_chain_without_vdw',
        'inter_chain_hbond',
        'inter_chain_vdw',
        'inter_chain_other',
        'binder_components_bonds',
        'binder_components_bonds_without_vdw',
        'binder_target_bonds',
        'binder_target_bonds_largest_component',
        'binder_target_bonds_no_vdw',
        'binder_target_bonds_no_vdw_largest_component'
    ]

    # The final CSV columns will be the original plus ring metrics
    final_header = header + ring_metric_names

    # Convert each row to a dictionary keyed by column name,
    # then compute ring metrics if the <base_filename>_ringNodes
    # exist. Otherwise fill metrics with e.g. 0 or None.
    dict_rows = []
    idx = 0
    for row in rows:
        # row is list (like [0.688, 3.23, 22.099, ..., description])
        row_dict = {}
        for i, col in enumerate(header):
            row_dict[col] = row[i] if i < len(row) else ""

        # Attempt to find base_filename from the 'description' column
        description = row_dict.get("description", "")
        # If your descriptions have .pdb at the end, remove it
        base_filename = description.replace(".pdb", "")

        node_file = os.path.join(ring_folder, f"{base_filename}.pdb_ringNodes")
        edge_file = os.path.join(ring_folder, f"{base_filename}.pdb_ringEdges")

        # Default ring metrics
        ring_counts = dict.fromkeys(ring_metric_names, 0)

        # If the ring files exist, compute the metrics
        if os.path.exists(node_file) and os.path.exists(edge_file):
            try:
                graph = create_ring_graph(node_file, edge_file)
                ring_counts = count_interactions(graph)
            except Exception as e:
                # If there's an error, you could leave them at 0 or track "NA"
                print(f"Warning: could not process RING files for {description}: {e}")
        else:
            # You could also mark them as 'NA' if preferred
            pass

        # Merge ring_counts into row_dict
        for key in ring_metric_names:
            row_dict[key] = ring_counts[key]

        dict_rows.append(row_dict)

        if (idx % 100 == 0):
            print(f"Processing count: {idx}")
        idx += 1

    # ------------------------------
    #  Write the final CSV
    # ------------------------------
    with open(csv_output, 'w', newline='') as out_f:
        writer = csv.DictWriter(out_f, fieldnames=final_header)
        writer.writeheader()
        for drow in dict_rows:
            writer.writerow(drow)

    print(f"Combined CSV (scores + ring metrics) saved to: {csv_output}")


if __name__ == "__main__":
    main()

