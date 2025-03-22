from tulip import tlp
import tulipplugins

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
                                 "False")

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

        # --- Helper Functions ---

        def is_interesting_interaction(inter_type):
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

        def get_pos_int(node):
            """
            Safe integer conversion for 'Position' property.
            """
            try:
                return int(prop_position[node])
            except:
                return -9999999

        # --- 1) Separate chain A (binder) vs chain B (target) ---

        binder_nodes = []
        target_nodes = []

        for n in self.graph.getNodes():
            c = prop_chain[n]
            if c == "A":  # binder
                binder_nodes.append(n)
            elif c == "B":  # target
                target_nodes.append(n)
            else:
                # ignoring other chains
                pass

        # Sort them by residue number
        binder_nodes.sort(key=get_pos_int)
        target_nodes.sort(key=get_pos_int)

        # --- 2) Identify chain B subset that interacts with chain A ---

        interacting_binder_set = set()
        interacting_target_set = set()

        for e in self.graph.getEdges():
            inter_type = prop_interaction[e]
            if not is_interesting_interaction(inter_type):
                continue

            n1 = self.graph.source(e)
            n2 = self.graph.target(e)
            c1 = prop_chain[n1]
            c2 = prop_chain[n2]

            if c1 == "A" and c2 == "B":
                interacting_binder_set.add(n1)
                interacting_target_set.add(n2)
            elif c1 == "B" and c2 == "A":
                interacting_binder_set.add(n2)
                interacting_target_set.add(n1)

        interacting_binder_list = sorted(list(interacting_binder_set), key=get_pos_int)
        interacting_target_list = sorted(list(interacting_target_set), key=get_pos_int)

        # --- 3) Build or reset subgraph "InteractingFrontline" ---

        binder_target_sub = self.graph.getSubGraph("BinderTargetInteraction")
        if binder_target_sub is None:
            binder_target_sub = self.graph.addSubGraph("BinderTargetInteraction")
        else:
            # clear existing content
            for n in list(binder_target_sub.getNodes()):
                binder_target_sub.delNode(n)
            for e in list(binder_target_sub.getEdges()):
                binder_target_sub.delEdge(e)

        sub_view_layout = binder_target_sub.getLocalLayoutProperty("viewLayout")

        # Add nodes
        binder_target_nodes = set(interacting_binder_list + interacting_target_list)
        for n in binder_target_nodes:
            binder_target_sub.addNode(n)

        # Add edges
        for e in self.graph.getEdges():
            s = self.graph.source(e)
            t = self.graph.target(e)
            if (s in binder_target_nodes) and (t in binder_target_nodes):
                inter_type = prop_interaction[e]
                if is_interesting_interaction(inter_type):
                    binder_target_sub.addEdge(e)

        # --- 4) Bipartite layout inside the subgraph ---

        space_x = 1.5

        # Place target nodes (chain B) horizontally at y=0
        for i, nodeB in enumerate(interacting_target_list):
            sub_view_layout[nodeB] = tlp.Vec3f(i * space_x, 0.0, 0.0)

        # Place binder nodes (chain A) horizontally at y=3
        for i, nodeA in enumerate(interacting_binder_list):
            sub_view_layout[nodeA] = tlp.Vec3f(i * space_x, 3.0, 0.0)

        if self.pluginProgress:
            self.pluginProgress.setComment(
                "Created subgraph 'BinderTargetInteraction' with bipartite layout for chain A/B interactions."
            )

        return True

# Register plugin
tulipplugins.registerPluginOfGroup(
    "BinderTargetInteraction",
    "ProteinCraft Binder Target Interaction",
    "Roden Luo",
    "2025-03-21",
    "Creates a subgraph for chain A-B interactions and sets bipartite layout",
    "1.0",
    "ProteinCraft"
)
