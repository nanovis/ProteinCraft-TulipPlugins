from tulip import tlp
from tulipgui import tlpgui
import tulipplugins


###############################################################################
# Helper function: given an edge interaction string, decide if we keep it
###############################################################################
def is_interesting_interaction(int_type, include_vdw):
    """
    Return True if the interaction is accepted by user choice
    (include_vdw toggles VDW).
    """
    if not int_type:
        return False
    if int_type.startswith("VDW"):
        return include_vdw
    # Otherwise, accept (HBOND, IONIC, etc.)
    return True

def is_covalent(int_type):
    """
    We consider 'COV...' or '...PEPTIDE...' to be covalent (skip them).
    """
    if not int_type:
        return False
    return (int_type.startswith("COV") or "PEPTIDE" in int_type.upper())

###############################################################################
# Main plugin
###############################################################################
class BinderTargetConnectedInteraction(tlp.Algorithm):
    """
    Creates a new subgraph containing:
      1) All interesting inter-chain edges between chain A and chain B,
      2) Binder-binder edges that are NOT included in the 'BinderIntraInteraction'
         subgraphs (i.e. not part of contiguous H/E components that actually interact).
      3) Only nodes from chain A or B that have at least one such edge.
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Let user decide whether to include VDW or not
        self.addBooleanParameter("include_vdw",
                                 "Include VDW interactions in the subgraph?",
                                 "True")

    def check(self):
        # No specific checks
        return (True, "")

    def run(self):
        include_vdw = self.dataSet["include_vdw"]

        subgraphs = self.graph.getSubGraphs()
        binder_target_interaction_subgraph = None
        binder_target_connected_subgraph = None
        
        # Find the BinderTargetInteraction subgraph
        for subgraph in subgraphs:
            if subgraph.getName() == "BinderTargetInteraction":
                binder_target_interaction_subgraph = subgraph
                break
        
        # Create a new subgraph by copying BinderTargetInteraction
        if binder_target_interaction_subgraph:
            # Create a new subgraph
            binder_target_connected_subgraph = self.graph.addSubGraph("BinderTargetConnectedInteraction")
            
            # Copy all nodes and edges from BinderTargetInteraction
            for node in binder_target_interaction_subgraph.getNodes():
                binder_target_connected_subgraph.addNode(node)
                
            for edge in binder_target_interaction_subgraph.getEdges():
                binder_target_connected_subgraph.addEdge(edge)
            
            # Apply Stress Minimization layout to improve the visualization
            params = tlp.getDefaultPluginParameters('Stress Minimization (OGDF)', binder_target_connected_subgraph)
            # Configure parameters for better layout
            params['number of iterations'] = 5
            params['edge costs'] = 2
            # Apply the layout algorithm
            binder_target_connected_subgraph.applyLayoutAlgorithm('Stress Minimization (OGDF)', params)

            # Create and configure the view for this subgraph
            nlv_binder_target_connected_interaction_sub = tlpgui.createNodeLinkDiagramView(binder_target_connected_subgraph)
            # Set labels scaled to node sizes mode
            renderingParameters = nlv_binder_target_connected_interaction_sub.getRenderingParameters()
            renderingParameters.setLabelScaled(True)
            nlv_binder_target_connected_interaction_sub.setRenderingParameters(renderingParameters)
            # Center the layout
            nlv_binder_target_connected_interaction_sub.centerView()


            # done
            if self.pluginProgress:
                self.pluginProgress.setComment(
                    f"Created/updated 'BinderTargetConnectedInteraction' subgraph by copying BinderTargetInteraction."
                )
        else:
            if self.pluginProgress:
                self.pluginProgress.setComment(
                    f"Could not find the BinderTargetInteraction subgraph."
                )

        return True

# Register the plugin
doc = """
Creates a new subgraph 'BinderTargetConnectedInteraction' with:
1) All interesting (non-covalent, user-chosen) edges between chain A and chain B,
2) Binder–binder edges (A–A) that are NOT included in the 'BinderIntraInteraction' 
   subgraphs (i.e., not part of contiguous H/E interactions).
Nodes from chain A or B are added if they appear in at least one such edge; 
others are excluded. 
"""

tulipplugins.registerPluginOfGroup(
    "BinderTargetConnectedInteraction",
    "Binder Target Connected Interaction",
    "Roden Luo",
    "2025-03-21",
    doc,
    "1.0",
    "ProteinCraft"
)
