#!/usr/bin/env python3
import sys
import os
import importlib.util
from pathlib import Path
from tulip import tlp
# Define the full path to the module
module_path = Path("../import/RINGImport.py")

# Create module spec
spec = importlib.util.spec_from_file_location("RINGImport", module_path)

# Load the module
RINGImport = importlib.util.module_from_spec(spec)
sys.modules["RINGImport"] = RINGImport
spec.loader.exec_module(RINGImport)

# Now you can access its contents
create_ring_graph = RINGImport.create_ring_graph

# Import binder intra interaction functions
binder_module_path = Path("../layout/BinderIntraInteraction.py")
binder_spec = importlib.util.spec_from_file_location("BinderIntraInteraction", binder_module_path)
BinderIntraInteraction = importlib.util.module_from_spec(binder_spec)
sys.modules["BinderIntraInteraction"] = BinderIntraInteraction
binder_spec.loader.exec_module(BinderIntraInteraction)

binderTarget_module_path = Path("../layout/BinderTargetInteraction.py")
binderTarget_spec = importlib.util.spec_from_file_location("BinderTargetInteraction", binderTarget_module_path)
BinderTargetInteraction = importlib.util.module_from_spec(binderTarget_spec)
sys.modules["BinderTargetInteraction"] = BinderTargetInteraction
binderTarget_spec.loader.exec_module(BinderTargetInteraction)

from BinderIntraInteraction import generate_subgraphs
from BinderTargetInteraction import identify_interacting_nodes, create_interaction_subgraph


def count_interactions(graph):
    """
    Count inter-chain interactions in the graph.
    
    Args:
        graph: A Tulip graph created by create_ring_graph
        
    Returns:
        dict: Dictionary containing interaction counts
    """
    # Get the properties we need
    chainProp = graph.getStringProperty("chain")
    interactionProp = graph.getStringProperty("interaction")
    
    # Initialize counters
    counts = {
        'inter_chain_total': 0,
        'inter_chain_vdw': 0,
        'inter_chain_hbond': 0,
        'inter_chain_other': 0,
        'binder_components_bonds': 0,
        'binder_components_bonds_without_vdw': 0
    }
    
    # Count inter-chain interactions
    for edge in graph.getEdges():
        # Get the nodes connected by this edge
        n1, n2 = graph.source(edge), graph.target(edge)
        
        # Get their chains
        chain1 = chainProp[n1]
        chain2 = chainProp[n2]
        
        # If chains are different, count as inter-chain
        if chain1 != chain2:
            counts['inter_chain_total'] += 1
            inter_type = interactionProp[edge]
            
            if inter_type.startswith("VDW"):
                counts['inter_chain_vdw'] += 1
            elif inter_type.startswith("HBOND"):
                counts['inter_chain_hbond'] += 1
            else:
                counts['inter_chain_other'] += 1
    
    # Calculate 'without VDW'
    counts['inter_chain_without_vdw'] = counts['inter_chain_total'] - counts['inter_chain_vdw']

    subgraphs = generate_subgraphs(graph, include_vdw=True)
    for subg in subgraphs:
        for edge in subg.getEdges():
            counts['binder_components_bonds'] += 1
            if not interactionProp[edge].startswith("VDW"):
                counts['binder_components_bonds_without_vdw'] += 1

    interacting_binder_list, interacting_target_list = identify_interacting_nodes(graph, include_vdw=True)
    binder_target_sub = create_interaction_subgraph(graph, interacting_binder_list, interacting_target_list, include_vdw=True)
    counts['binder_target_bonds'] = binder_target_sub.numberOfEdges()

    # Get the largest connected component
    connected_components = tlp.ConnectedTest.computeConnectedComponents(binder_target_sub)
    if connected_components:
        largest_component = max(connected_components, key=len)
        counts['binder_target_bonds_largest_component'] = len(largest_component)
    else:
        counts['binder_target_bonds_largest_component'] = 0

    interacting_binder_list, interacting_target_list = identify_interacting_nodes(graph, include_vdw=False)
    binder_target_sub = create_interaction_subgraph(graph, interacting_binder_list, interacting_target_list, include_vdw=False)
    counts['binder_target_bonds_no_vdw'] = binder_target_sub.numberOfEdges()

    # Get the largest connected component
    connected_components = tlp.ConnectedTest.computeConnectedComponents(binder_target_sub)
    if connected_components:
        largest_component = max(connected_components, key=len)
        counts['binder_target_bonds_no_vdw_largest_component'] = len(largest_component)
    else:
        counts['binder_target_bonds_no_vdw_largest_component'] = 0
     
    return counts

def main():
    if len(sys.argv) != 2:
        print("Usage: python ring_interactions.py <base_filename>")
        print("Example: python ring_interactions.py try1_9_dldesign_0_cycle1_af2pred")
        sys.exit(1)
    
    base_filename = sys.argv[1]
    node_file = f"{base_filename}_ringNodes"
    edge_file = f"{base_filename}_ringEdges"
    
    # Check if files exist
    if not os.path.exists(node_file):
        print(f"Error: Node file {node_file} does not exist")
        sys.exit(1)
    if not os.path.exists(edge_file):
        print(f"Error: Edge file {edge_file} does not exist")
        sys.exit(1)
    
    try:
        # Create the graph
        graph = create_ring_graph(node_file, edge_file)
        
        # Count interactions
        counts = count_interactions(graph)
        
        # Print results
        print("\n===== Interaction Counts =====")
        print("\nInter-Chain Interactions:")
        print(f"Total Inter-chain bonds: {counts['inter_chain_total']}")
        print(f"Inter-chain bonds WITHOUT VDW: {counts['inter_chain_without_vdw']}")
        print(f"All inter-chain HBonds: {counts['inter_chain_hbond']}")
        print(f"All inter-chain VDW bonds: {counts['inter_chain_vdw']}")
        print(f"All inter-chain OTHER bonds: {counts['inter_chain_other']}")
        
        print("\nBinder Components:")
        print(f"Number of binder component bonds: {counts['binder_components_bonds']}")
        print(f"Number of binder component bonds WITHOUT VDW: {counts['binder_components_bonds_without_vdw']}")

        print("\nBinder Target:")
        print(f"Number of binder target bonds: {counts['binder_target_bonds']}")
        print(f"Number of binder target bonds in largest component: {counts['binder_target_bonds_largest_component']}")

        print("\nBinder Target (no VDW):")
        print(f"Number of binder target bonds: {counts['binder_target_bonds_no_vdw']}")
        print(f"Number of binder target bonds in largest component: {counts['binder_target_bonds_no_vdw_largest_component']}")
    except Exception as e:
        print(f"Error processing files: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 