from tulip import tlp
from tulipgui import tlpgui
import tulipplugins

def calculate_edge_lengths(graph, nodes, view_layout):
    """
    Calculate total edge length for a set of nodes.
    
    Args:
        graph: The Tulip graph
        nodes: List of nodes
        view_layout: The layout property of the graph
        
    Returns:
        Total edge length
    """
    total_length = 0.0
    node_set = set(nodes)
    
    for n in nodes:
        for e in graph.getInOutEdges(n):
            if graph.source(e) in node_set and graph.target(e) in node_set:
                src = view_layout[graph.source(e)]
                tgt = view_layout[graph.target(e)]
                total_length += (src - tgt).norm()
    
    return total_length

class BinderIntraInteraction(tlp.Algorithm):
    """
    This plugin finds contiguous H/E components on chain A
    and creates subgraphs for each interacting pair of these components
    in a bipartite layout (vertical or horizontal).

    Requirements:
    - The graph has node properties "chain", "position", "dssp"
      and edge property "interaction" (matching those from RINGImport).
    - The user can specify whether to include VDW edges or not
      (include_vdw).
    - The user can specify layout orientation ("vertical" or "horizontal").
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Boolean parameter for including or excluding VDW interactions
        self.addBooleanParameter("include_vdw",
                                 "Include VDW interactions in the subgraphs?",
                                 "True")
        # String parameter for orientation: vertical or horizontal
        self.addStringCollectionParameter("layout_orientation",
                                        "Bipartite layout orientation",
                                        "vertical;horizontal",
                                        True,
                                        True,
                                        False,
                                        "Layout orientation can be either 'vertical' (two columns) or 'horizontal' (two rows)")

    def check(self):
        # Optionally check if needed properties exist
        g = self.graph
        # No strict checks here, but you could do:
        # if "chain" not in g.getPropertyNames():
        #     return (False, "Property 'chain' not found. Please import with RINGImport first.")
        return (True, "")

    def run(self):
        # Retrieve the user parameters
        include_vdw = self.dataSet["include_vdw"]
        layout_orientation = self.dataSet["layout_orientation"]

        # Retrieve the relevant properties set by the RINGImport plugin
        prop_chain       = self.graph["chain"]        # e.g., "A", "B", etc.
        prop_position    = self.graph["position"]     # numeric or convertible to int
        prop_dssp        = self.graph["dssp"]         # e.g., "H", "E", etc.
        prop_interaction = self.graph["interaction"]  # e.g., "HBOND:MC_MC", "VDW:SC_SC"

        # Helper: convert 'position' to a usable int
        def get_position_int(n):
            try:
                return int(prop_position[n])
            except:
                return -999999

        # Decide which edges are "interesting"
        def is_interesting_interaction(int_type):
            if not int_type:
                return False
            if int_type.startswith("VDW"):
                return include_vdw  # only keep VDW if user wants it
            # accept everything else (HBOND, IONIC, etc.)
            return True

        # Decide if an interaction is covalent (we skip these)
        def is_covalent(int_type):
            if not int_type:
                return False
            # e.g. "COV:PEP", "COV", "PEPTIDE BOND", etc.
            return (int_type.startswith("COV") or "PEPTIDE" in int_type.upper())

        # ------------------------------------------------------------------
        # 1) Identify chain A's contiguous H/E components
        # ------------------------------------------------------------------
        chain_a_nodes = [n for n in self.graph.getNodes() if prop_chain[n] == "A"]
        chain_a_nodes.sort(key=get_position_int)

        components = []  # will store dicts: { "nodes", "dssp", "startPos", "endPos" }

        def flush_component(node_list, dssp_code, start_p, end_p):
            if node_list and dssp_code in ("H","E"):
                components.append({
                    "nodes":    list(node_list),
                    "dssp":     dssp_code,
                    "startPos": start_p,
                    "endPos":   end_p
                })

        curr_nodes = []
        curr_dssp  = None
        curr_start = None
        curr_end   = None
        prev_pos   = None

        for i, nd in enumerate(chain_a_nodes):
            d = prop_dssp[nd] or ""  # handle None => ""
            p = get_position_int(nd)
            
            if i == 0:
                # first residue in chain A
                if d in ("H","E"):
                    curr_nodes = [nd]
                    curr_dssp  = d
                    curr_start = p
                    curr_end   = p
            else:
                if curr_nodes:  # we're building a run
                    if (d == curr_dssp) and (p == prev_pos + 1) and (d in ("H","E")):
                        # continue the same run
                        curr_nodes.append(nd)
                        curr_end = p
                    else:
                        # flush old run
                        flush_component(curr_nodes, curr_dssp, curr_start, curr_end)
                        # start new if this residue is H/E
                        if d in ("H","E"):
                            curr_nodes = [nd]
                            curr_dssp  = d
                            curr_start = p
                            curr_end   = p
                        else:
                            # reset
                            curr_nodes = []
                            curr_dssp  = None
                            curr_start = None
                            curr_end   = None
                else:
                    # not building a run
                    if d in ("H","E"):
                        curr_nodes = [nd]
                        curr_dssp  = d
                        curr_start = p
                        curr_end   = p
            prev_pos = p

        # final flush at end
        if curr_nodes:
            flush_component(curr_nodes, curr_dssp, curr_start, curr_end)

        # sort components by start position
        components.sort(key=lambda c: c["startPos"])

        # ------------------------------------------------------------------
        # 2) For each pair of these components, check if they interact
        #    and if so, create a subgraph with bipartite layout
        # ------------------------------------------------------------------
        def do_components_interact(compA, compB):
            nodeSetA = set(compA["nodes"])
            nodeSetB = set(compB["nodes"])
            for nA in nodeSetA:
                for e in self.graph.getInOutEdges(nA):
                    itype = prop_interaction[e]
                    if not is_interesting_interaction(itype):
                        continue
                    if is_covalent(itype):
                        continue
                    nOther = self.graph.target(e) if self.graph.source(e) == nA else self.graph.source(e)
                    if nOther in nodeSetB:
                        return True
            return False

        def layout_bipartite(compA_nodes, compB_nodes, sub_layout):
            """
            Places compA_nodes & compB_nodes in a bipartite arrangement:
              - 'vertical': two columns
              - 'horizontal': two rows
            """
            # sort each group by ascending position
            compA_nodes = sorted(compA_nodes, key=get_position_int)
            compB_nodes = sorted(compB_nodes, key=get_position_int)

            if layout_orientation == "vertical":
                left_x  = 0.0
                right_x = 3.0
                top_y   = 0.0
                step_y  = -1.5

                # First try with compB in original order
                yA = top_y
                for ndA in compA_nodes:
                    sub_layout[ndA] = tlp.Vec3f(left_x, yA, 0)
                    yA += step_y

                yB = top_y
                for ndB in compB_nodes:
                    sub_layout[ndB] = tlp.Vec3f(right_x, yB, 0)
                    yB += step_y

                # Calculate edge lengths for original orientation
                orig_length = calculate_edge_lengths(self.graph, compA_nodes + compB_nodes, sub_layout)

                # Try reversed compB
                yB = top_y
                for ndB in reversed(compB_nodes):
                    sub_layout[ndB] = tlp.Vec3f(right_x, yB, 0)
                    yB += step_y

                # Calculate edge lengths for reversed orientation
                reversed_length = calculate_edge_lengths(self.graph, compA_nodes + compB_nodes, sub_layout)

                # Choose orientation with shorter total edge length
                if reversed_length < orig_length:
                    # Keep the reversed orientation
                    pass
                else:
                    # Revert back to original orientation
                    yB = top_y
                    for ndB in compB_nodes:
                        sub_layout[ndB] = tlp.Vec3f(right_x, yB, 0)
                        yB += step_y

            elif layout_orientation == "horizontal":
                top_y     = 0.0
                bottom_y  = -1.5
                left_x    = 0.0
                step_x    = 3.0

                # First try with compB in original order
                xA = left_x
                for ndA in compA_nodes:
                    sub_layout[ndA] = tlp.Vec3f(xA, top_y, 0)
                    xA += step_x

                xB = left_x
                for ndB in compB_nodes:
                    sub_layout[ndB] = tlp.Vec3f(xB, bottom_y, 0)
                    xB += step_x

                # Calculate edge lengths for original orientation
                orig_length = calculate_edge_lengths(self.graph, compA_nodes + compB_nodes, sub_layout)

                # Try reversed compB
                xB = left_x
                for ndB in reversed(compB_nodes):
                    sub_layout[ndB] = tlp.Vec3f(xB, bottom_y, 0)
                    xB += step_x

                # Calculate edge lengths for reversed orientation
                reversed_length = calculate_edge_lengths(self.graph, compA_nodes + compB_nodes, sub_layout)

                # Choose orientation with shorter total edge length
                if reversed_length < orig_length:
                    # Keep the reversed orientation
                    pass
                else:
                    # Revert back to original orientation
                    xB = left_x
                    for ndB in compB_nodes:
                        sub_layout[ndB] = tlp.Vec3f(xB, bottom_y, 0)
                        xB += step_x

            else:
                # fallback => vertical
                print(f"[WARNING] Unrecognized layout_orientation={layout_orientation}, using vertical fallback.")
                left_x  = 0.0
                right_x = 3.0
                top_y   = 0.0
                step_y  = -1.5

                yA = top_y
                for ndA in compA_nodes:
                    sub_layout[ndA] = tlp.Vec3f(left_x, yA, 0)
                    yA += step_y

                yB = top_y
                for ndB in compB_nodes:
                    sub_layout[ndB] = tlp.Vec3f(right_x, yB, 0)
                    yB += step_y

        # Create subgraphs for interacting pairs
        for i in range(len(components)):
            for j in range(i+1, len(components)):
                compA = components[i]
                compB = components[j]

                if do_components_interact(compA, compB):
                    sub_name = f"CompA_{compA['startPos']}_{compA['endPos']}__CompB_{compB['startPos']}_{compB['endPos']}"
                    subg = self.graph.getSubGraph(sub_name)
                    if subg:
                        # clear old content
                        for nd in list(subg.getNodes()):
                            subg.delNode(nd)
                        for e in list(subg.getEdges()):
                            subg.delEdge(e)
                    else:
                        subg = self.graph.addSubGraph(sub_name)

                    sub_layout = subg.getLocalLayoutProperty("viewLayout")

                    # gather all nodes
                    all_nodes = set(compA["nodes"] + compB["nodes"])
                    for nd in all_nodes:
                        subg.addNode(nd)

                    # Track nodes that have interactions
                    nodes_with_interactions = set()

                    # gather edges (non-covalent, interesting)
                    for nd in all_nodes:
                        for e in self.graph.getInOutEdges(nd):
                            itype = prop_interaction[e]
                            if not is_interesting_interaction(itype):
                                continue
                            if is_covalent(itype):
                                continue
                            nOther = self.graph.target(e) if self.graph.source(e) == nd else self.graph.source(e)
                            # Only keep edges that connect between different components
                            if nOther in all_nodes:
                                # Check if the edge connects between different components
                                if ((nd in compA["nodes"] and nOther in compB["nodes"]) or 
                                    (nd in compB["nodes"] and nOther in compA["nodes"])):
                                    subg.addEdge(e)
                                    nodes_with_interactions.add(nd)
                                    nodes_with_interactions.add(nOther)

                    # Set opacity for nodes without interactions using viewColor
                    prop_viewParentColor = subg.getColorProperty("viewColor")
                    prop_viewColor = subg.getLocalColorProperty("viewColor")
                    
                    # Copy parent colors to local property for edges
                    for e in subg.getEdges():
                        prop_viewColor[e] = prop_viewParentColor[e]
                    
                    # Set opacity for nodes without interactions
                    for nd in all_nodes:
                        if nd not in nodes_with_interactions:
                            # Get current color and set alpha to 64 (1/4 opacity)
                            current_color = prop_viewParentColor[nd]
                            prop_viewColor[nd] = (current_color[0], current_color[1], current_color[2], 64)
                        else:
                            prop_viewColor[nd] = (current_color[0], current_color[1], current_color[2], 255)

                    # bipartite layout
                    layout_bipartite(compA["nodes"], compB["nodes"], sub_layout)
                    if self.pluginProgress:
                        self.pluginProgress.setComment(
                            f"Created subgraph '{sub_name}' in {layout_orientation} bipartite layout."
                        )

                    # Create and configure the view for this subgraph
                    nlv_binder_intra_sub = tlpgui.createNodeLinkDiagramView(subg)
                    # Set labels scaled to node sizes mode
                    renderingParameters = nlv_binder_intra_sub.getRenderingParameters()
                    renderingParameters.setLabelScaled(True)
                    nlv_binder_intra_sub.setRenderingParameters(renderingParameters)
                    # Center the layout
                    nlv_binder_intra_sub.centerView()            

        if self.pluginProgress:
            self.pluginProgress.setComment(
                "Done. Created subgraphs for each pair of chain A H/E components with non-covalent interactions."
            )

        return True

# Register the plugin
doc = """
For chain A only, find contiguous runs of H or E (based on dssp property), 
then for each pair that interacts non-covalently, create a subgraph with a bipartite layout.
User parameters:
 - include_vdw: boolean to include or exclude VDW edges,
 - layout_orientation: "vertical" (two columns) or "horizontal" (two rows).
"""

tulipplugins.registerPluginOfGroup(
    "BinderIntraInteraction",          # internal plugin name
    "Binder Intra Interaction",       # displayed name
    "Roden Luo",                         # author
    "2025-03-21",                        # creation date
    doc,                                 # documentation
    "1.0",                               # version
    "ProteinCraft"                       # plugin group
)
