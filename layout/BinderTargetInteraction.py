from tulip import tlp
from tulipgui import tlpgui
import tulipplugins

from BinderIntraInteraction import calculate_edge_lengths

def is_interesting_interaction(inter_type, include_vdw):
    """
    Include only non-VDW or VDW if user requested.
    """
    if not inter_type:
        return False
    if inter_type.startswith("VDW"):
        # only include if user wants VDW
        return include_vdw
    # otherwise accept e.g. HBOND, IONIC, etc.
    return True

def get_pos_int(node, prop_position):
    """
    Safe integer conversion for 'Position' property.
    """
    try:
        return int(prop_position[node])
    except:
        return -9999999

def identify_interacting_nodes(graph, prop_chain, prop_position, prop_interaction, include_vdw):
    """
    Identifies nodes from chain A and B that interact with each other.
    Returns sorted lists of interacting binder and target nodes.
    """
    # Separate chain A (binder) vs chain B (target)
    binder_nodes = []
    target_nodes = []

    for n in graph.getNodes():
        c = prop_chain[n]
        if c == "A":  # binder
            binder_nodes.append(n)
        elif c == "B":  # target
            target_nodes.append(n)
        else:
            # ignoring other chains
            pass

    # Sort them by residue number
    binder_nodes.sort(key=lambda n: get_pos_int(n, prop_position))
    target_nodes.sort(key=lambda n: get_pos_int(n, prop_position))

    # Identify chain B subset that interacts with chain A
    interacting_binder_set = set()
    interacting_target_set = set()

    for e in graph.getEdges():
        inter_type = prop_interaction[e]
        if not is_interesting_interaction(inter_type, include_vdw):
            continue

        n1 = graph.source(e)
        n2 = graph.target(e)
        c1 = prop_chain[n1]
        c2 = prop_chain[n2]

        if c1 == "A" and c2 == "B":
            interacting_binder_set.add(n1)
            interacting_target_set.add(n2)
        elif c1 == "B" and c2 == "A":
            interacting_binder_set.add(n2)
            interacting_target_set.add(n1)

    interacting_binder_list = sorted(list(interacting_binder_set), 
                                    key=lambda n: get_pos_int(n, prop_position))
    interacting_target_list = sorted(list(interacting_target_set), 
                                    key=lambda n: get_pos_int(n, prop_position))
    
    return interacting_binder_list, interacting_target_list

def create_interaction_subgraph(graph, interacting_binder_list, interacting_target_list, 
                              prop_interaction, include_vdw):
    """
    Creates or resets a subgraph containing the interacting nodes.
    Returns the subgraph.
    """
    binder_target_sub = graph.getSubGraph("BinderTargetInteraction")
    if binder_target_sub is None:
        binder_target_sub = graph.addSubGraph("BinderTargetInteraction")
    else:
        # clear existing content
        for n in list(binder_target_sub.getNodes()):
            binder_target_sub.delNode(n)
        for e in list(binder_target_sub.getEdges()):
            binder_target_sub.delEdge(e)

    # Add nodes
    binder_target_nodes = set(interacting_binder_list + interacting_target_list)
    for n in binder_target_nodes:
        binder_target_sub.addNode(n)

    # Add edges
    for e in graph.getEdges():
        s = graph.source(e)
        t = graph.target(e)
        if (s in binder_target_nodes) and (t in binder_target_nodes):
            inter_type = prop_interaction[e]
            if is_interesting_interaction(inter_type, include_vdw):
                binder_target_sub.addEdge(e)
                
    return binder_target_sub

def layout_bipartite_subgraph(graph, interacting_binder_list, interacting_target_list, sub_view_layout):
    """
    Creates a bipartite layout for the subgraph and selects the best orientation.
    """
    space_x = 1.5

    # First try with target nodes in original order
    for i, nodeB in enumerate(interacting_target_list):
        sub_view_layout[nodeB] = tlp.Vec3f(i * space_x, 0.0, 0.0)

    # Place binder nodes (chain A) horizontally at y=3
    for i, nodeA in enumerate(interacting_binder_list):
        sub_view_layout[nodeA] = tlp.Vec3f(i * space_x, 3.0, 0.0)

    # Calculate edge lengths for original orientation
    orig_length = calculate_edge_lengths(graph, interacting_binder_list + interacting_target_list, sub_view_layout)

    # Try reversed target nodes
    for i, nodeB in enumerate(reversed(interacting_target_list)):
        sub_view_layout[nodeB] = tlp.Vec3f(i * space_x, 0.0, 0.0)

    # Calculate edge lengths for reversed orientation
    reversed_length = calculate_edge_lengths(graph, interacting_binder_list + interacting_target_list, sub_view_layout)

    # Choose orientation with shorter total edge length
    if reversed_length < orig_length:
        # Keep the reversed orientation
        pass
    else:
        # Revert back to original orientation
        for i, nodeB in enumerate(interacting_target_list):
            sub_view_layout[nodeB] = tlp.Vec3f(i * space_x, 0.0, 0.0)

class BinderTargetInteraction(tlp.Algorithm):
    """
    Creates a subgraph named 'BinderTargetInteraction' containing 
    nodes of chain A and chain B that interact, and lays them 
    out in a bipartite manner (chain B at y=0, chain A at y=3).
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Let the user decide whether to include VDW interactions or not
        self.addBooleanParameter("include_vdw",
                                 "Include VDW interactions in the subgraph?",
                                 "True")

    def check(self):
        # Pre-check before run()
        return (True, "")

    def run(self):
        # Retrieve user parameter
        include_vdw = self.dataSet["include_vdw"]

        # Retrieve relevant properties
        prop_chain = self.graph["chain"]          # e.g. "A" or "B"
        prop_position = self.graph["position"]    # residue numbering
        prop_interaction = self.graph["interaction"]  # e.g. "HBOND:MC_MC", "VDW:SC_SC"

        # Identify interacting nodes
        interacting_binder_list, interacting_target_list = identify_interacting_nodes(
            self.graph, prop_chain, prop_position, prop_interaction, include_vdw)
            
        # Create or reset subgraph
        binder_target_sub = create_interaction_subgraph(
            self.graph, interacting_binder_list, interacting_target_list, 
            prop_interaction, include_vdw)
            
        # Layout the subgraph
        sub_view_layout = binder_target_sub.getLocalLayoutProperty("viewLayout")
        layout_bipartite_subgraph(
            self.graph, interacting_binder_list, interacting_target_list, sub_view_layout)

        if self.pluginProgress:
            self.pluginProgress.setComment(
                "Created subgraph 'BinderTargetInteraction' with bipartite layout for chain A/B interactions."
            )

        nlv_binder_target_sub = tlpgui.createNodeLinkDiagramView(binder_target_sub)

        # set labels scaled to node sizes mode
        renderingParameters = nlv_binder_target_sub.getRenderingParameters()
        renderingParameters.setLabelScaled(True)
        nlv_binder_target_sub.setRenderingParameters(renderingParameters)
        
        # center the layout
        nlv_binder_target_sub.centerView()

        return True

# Register plugin
tulipplugins.registerPluginOfGroup(
    "BinderTargetInteraction",
    "Binder Target Interaction",
    "Roden Luo",
    "2025-03-21",
    "Creates a subgraph for chain A-B interactions and sets bipartite layout",
    "1.0",
    "ProteinCraft"
)
