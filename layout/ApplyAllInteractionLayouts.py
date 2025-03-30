from tulip import tlp
from tulipgui import tlpgui
import tulipplugins

class ApplyAllInteractionLayouts(tlp.Algorithm):
    """
    This plugin applies all three interaction layout algorithms in sequence:
    1. Binder Target Interaction - Creates a bipartite layout for chain A-B interactions
    2. Binder Target and Singleton Interaction - Shows remaining chain A-B and singleton interactions
    3. Binder Intra Interaction - Shows interactions between contiguous H/E components in chain A

    Requirements:
    - The graph must have node properties "chain", "position", "dssp"
      and edge property "interaction" (matching those from RINGImport).
    - The user can specify whether to include VDW edges or not
      (include_vdw).
    - The user can specify layout orientation for Binder Intra Interaction
      ("vertical" or "horizontal").
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Boolean parameter for including or excluding VDW interactions
        self.addBooleanParameter("include_vdw",
                               "Include VDW interactions in the subgraphs?",
                               "True")
        # String parameter for orientation: vertical or horizontal
        self.addStringCollectionParameter("layout_orientation",
                                        "Bipartite layout orientation for Binder Intra Interaction",
                                        "vertical;horizontal",
                                        True,
                                        True,
                                        False,
                                        "Layout orientation can be either 'vertical' (two columns) or 'horizontal' (two rows)")
        
    def check(self):
        # Check if required properties exist
        g = self.graph
        required_props = ["chain", "position", "dssp", "interaction"]
        existing_prop_names = [p for p in g.getProperties()]

        for prop in required_props:
            if prop not in existing_prop_names:
                return (False, f"Property '{prop}' not found. Please import with RINGImport first.")

        return (True, "")

    def run(self):
        # Retrieve the user parameters
        include_vdw = self.dataSet["include_vdw"]
        layout_orientation = self.dataSet["layout_orientation"]

        # 1. Apply Binder Target Interaction
        binder_target_params = tlp.getDefaultPluginParameters("Binder Target Interaction", self.graph)
        binder_target_params["include_vdw"] = include_vdw
        success = self.graph.applyAlgorithm("Binder Target Interaction", binder_target_params)
        if not success:
            return False

        # 2. Apply Binder Intra Interaction
        binder_intra_params = tlp.getDefaultPluginParameters("Binder Intra Interaction", self.graph)
        binder_intra_params["include_vdw"] = include_vdw
        binder_intra_params["layout_orientation"] = layout_orientation
        success = self.graph.applyAlgorithm("Binder Intra Interaction", binder_intra_params)
        if not success:
            return False

        # 3. Apply Binder Target Connected Interaction
        binder_target_connected_params = tlp.getDefaultPluginParameters("Binder Target Connected Interaction", self.graph)
        binder_target_connected_params["include_vdw"] = include_vdw
        success = self.graph.applyAlgorithm("Binder Target Connected Interaction", binder_target_connected_params)
        if not success:
            return False
        
        if self.pluginProgress:
            self.pluginProgress.setComment(
                "Successfully applied all three interaction layout algorithms."
            )

        # last action: close all views on the parent graph
        tlpgui.closeViewsRelatedToGraph(self.graph)

        return True

# Register plugin
tulipplugins.registerPluginOfGroup(
    "ApplyAllInteractionLayouts",
    "Apply All Interaction Layouts",
    "Roden Luo",
    "2025-03-21",
    "Applies all three interaction layout algorithms in sequence",
    "1.0",
    "ProteinCraft"
) 