from tulip import tlp
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
# Helper function: parse chain A H/E runs and find edges used in 
# BinderIntraInteraction subgraphs
###############################################################################
def find_binder_intra_component_edges(graph, include_vdw):
    """
    1) Identify chain A contiguous H/E components.
    2) For each pair that interacts (non-covalent, interesting edges),
       gather all edges among the union of those two components.
    3) Return a set of "component edges" that appear in such subgraphs.
    """
    prop_chain       = graph["chain"]
    prop_position    = graph["position"]
    prop_dssp        = graph["dssp"]
    prop_interaction = graph["interaction"]

    # safe position int
    def get_position_int(n):
        try:
            return int(prop_position[n])
        except:
            return -999999

    # define "interesting" for BinderIntra
    def binder_intra_interesting(int_type):
        if not int_type:
            return False
        if int_type.startswith("VDW"):
            return include_vdw
        return True

    def do_components_interact(compA, compB):
        nodeSetA = set(compA["nodes"])
        nodeSetB = set(compB["nodes"])
        for nA in nodeSetA:
            for e in graph.getInOutEdges(nA):
                itype = prop_interaction[e]
                if not binder_intra_interesting(itype):
                    continue
                if is_covalent(itype):
                    continue
                nOther = graph.target(e) if graph.source(e) == nA else graph.source(e)
                if nOther in nodeSetB:
                    return True
        return False

    # 1) gather chain A, sort by position
    chain_a_nodes = [n for n in graph.getNodes() if prop_chain[n] == "A"]
    chain_a_nodes.sort(key=get_position_int)

    # find contiguous H/E runs
    components = []
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
        d = prop_dssp[nd] or ""
        p = get_position_int(nd)
        if i == 0:
            if d in ("H","E"):
                curr_nodes = [nd]
                curr_dssp  = d
                curr_start = p
                curr_end   = p
        else:
            if curr_nodes:
                # continuing a run
                if (d == curr_dssp) and (p == prev_pos + 1) and (d in ("H","E")):
                    curr_nodes.append(nd)
                    curr_end = p
                else:
                    flush_component(curr_nodes, curr_dssp, curr_start, curr_end)
                    if d in ("H","E"):
                        curr_nodes = [nd]
                        curr_dssp  = d
                        curr_start = p
                        curr_end   = p
                    else:
                        curr_nodes = []
                        curr_dssp  = None
                        curr_start = None
                        curr_end   = None
            else:
                if d in ("H","E"):
                    curr_nodes = [nd]
                    curr_dssp  = d
                    curr_start = p
                    curr_end   = p
        prev_pos = p

    if curr_nodes:
        flush_component(curr_nodes, curr_dssp, curr_start, curr_end)

    components.sort(key=lambda c: c["startPos"])

    # 2) For each pair that does interact, gather all edges among compA+compB
    component_edges = set()
    for i in range(len(components)):
        for j in range(i+1, len(components)):
            compA = components[i]
            compB = components[j]
            if do_components_interact(compA, compB):
                # gather edges among compA+compB (non-covalent + interesting)
                all_nodes = set(compA["nodes"] + compB["nodes"])
                for nd in all_nodes:
                    for e in graph.getInOutEdges(nd):
                        itype = prop_interaction[e]
                        if not binder_intra_interesting(itype):
                            continue
                        if is_covalent(itype):
                            continue
                        other = graph.target(e) if graph.source(e) == nd else graph.source(e)
                        if other in all_nodes:
                            component_edges.add(e)

    return component_edges

###############################################################################
# Main plugin
###############################################################################
class BinderTargetAndSingletonInteraction(tlp.Algorithm):
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

        g = self.graph
        prop_chain       = g["chain"]         # e.g. "A","B"
        prop_interaction = g["interaction"]   # e.g. "HBOND:MC_MC","VDW:SC_SC"

        # 1) Identify binder-intra "component edges"
        #    (the edges used by BinderIntraInteraction subgraphs).
        binder_intra_edges = find_binder_intra_component_edges(g, include_vdw)

        # 2) Create or reuse subgraph "BinderTargetAndSingletonInteraction"
        sub_name = "BinderTargetAndSingletonInteraction"
        new_sub = g.getSubGraph(sub_name)
        if new_sub:
            # Clear it
            for n in list(new_sub.getNodes()):
                new_sub.delNode(n)
            for e in list(new_sub.getEdges()):
                new_sub.delEdge(e)
        else:
            new_sub = g.addSubGraph(sub_name)

        sub_layout = new_sub.getLocalLayoutProperty("viewLayout")

        # We will add chain A and chain B nodes only
        # but we do it in two steps:
        # (a) gather edges that pass the filter
        # (b) add the nodes that appear in those edges
        def is_inter_chain(n1, n2):
            return prop_chain[n1] != prop_chain[n2]

        def passes_filter(e):
            # skip if covalent
            if is_covalent(prop_interaction[e]):
                return False
            if not is_interesting_interaction(prop_interaction[e], include_vdw):
                return False
            s = g.source(e)
            t = g.target(e)
            chain_s = prop_chain[s]
            chain_t = prop_chain[t]
            # we only consider edges that connect chain A or B
            if chain_s not in ("A","B") or chain_t not in ("A","B"):
                return False

            # If both nodes are in chain B, exclude this edge
            if chain_s == "B" and chain_t == "B":
                return False

            # check if it is inter-chain => always keep if it passes filter
            if chain_s != chain_t:
                return True

            # else chain_s == chain_t == "A" => binder-binder edge
            # keep if it's NOT in binder_intra_edges
            if e not in binder_intra_edges:
                return True

            # skip otherwise
            return False

        edges_to_add = []
        for e in g.getEdges():
            if passes_filter(e):
                edges_to_add.append(e)

        # 3) Add edges to subgraph, and also ensure nodes are present
        # Get the original viewLayout property
        original_layout = g.getLayoutProperty("viewLayout")
        
        for e in edges_to_add:
            s = g.source(e)
            t = g.target(e)
            # add nodes if not present and copy their layout
            if not new_sub.isElement(s):
                new_sub.addNode(s)
                sub_layout[s] = original_layout[s]
            if not new_sub.isElement(t):
                new_sub.addNode(t)
                sub_layout[t] = original_layout[t]
            new_sub.addEdge(e)

        # 4) Remove nodes that have no edges
        #    (in practice, they shouldn't exist if we only add them from edges, 
        #     but let's be safe in case chain A or B had preexisting nodes.)
        for n in list(new_sub.getNodes()):
            if len(list(new_sub.getInOutEdges(n))) == 0:
                new_sub.delNode(n)

        # done
        if self.pluginProgress:
            self.pluginProgress.setComment(
                f"Created/updated '{sub_name}' subgraph with inter-chain edges + leftover binder-binder edges."
            )

        return True

# Register the plugin
doc = """
Creates a new subgraph 'BinderTargetAndSingletonInteraction' with:
1) All interesting (non-covalent, user-chosen) edges between chain A and chain B,
2) Binder–binder edges (A–A) that are NOT included in the 'BinderIntraInteraction' 
   subgraphs (i.e., not part of contiguous H/E interactions).
Nodes from chain A or B are added if they appear in at least one such edge; 
others are excluded. 
"""

tulipplugins.registerPluginOfGroup(
    "BinderTargetAndSingletonInteraction",
    "Binder Target and Singleton Interaction",
    "Roden Luo",
    "2025-03-21",
    doc,
    "1.0",
    "ProteinCraft"
)
