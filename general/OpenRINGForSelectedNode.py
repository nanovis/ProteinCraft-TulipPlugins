from tulip import tlp
import tulipplugins
from tulipgui import tlpgui

class OpenRINGForSelectedNode(tlp.Algorithm):
    """
    This plugin opens a RING graph for the currently selected node.
    It requires exactly one node to be selected, and uses the node's
    description property as the base filename to construct the paths
    for the RING node and edge files.
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Let the user specify the base path for the RING files
        self.addStringParameter(
            "base path",
            "Base path for RING files",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_RING"
        )

    def check(self):
        """
        Verify that exactly one node is selected and has a description property.
        """
        viewSelection = self.graph.getBooleanProperty("viewSelection")
        description = self.graph.getStringProperty("description")
        
        # Count selected nodes
        selected_nodes = [n for n in self.graph.getNodes() if viewSelection[n]]
        
        if len(selected_nodes) != 1:
            return (False, "Please select exactly one node.")
            
        # Check if the selected node has a description
        if not description[selected_nodes[0]]:
            return (False, "Selected node must have a description property.")
            
        return (True, "")

    def run(self):
        """
        Main function that:
        1. Gets the selected node's description
        2. Constructs paths for ringNodes and ringEdges files
        3. Calls RINGImport plugin with these files
        """
        base_path = self.dataSet["base path"]
        viewSelection = self.graph.getBooleanProperty("viewSelection")
        description = self.graph.getStringProperty("description")
        
        # Get the selected node
        selected_node = [n for n in self.graph.getNodes() if viewSelection[n]][0]
        filename = description[selected_node]
        
        # Construct paths for RING files
        node_file = f"{base_path}/{filename}.pdb_ringNodes"
        edge_file = f"{base_path}/{filename}.pdb_ringEdges"

        # Call RINGImport plugin
        params = tlp.getDefaultPluginParameters("ProteinCraft RING Import", self.graph)

        params["node file"] = node_file
        params["edge file"] = edge_file

        success = self.graph.applyAlgorithm("ProteinCraft RING Import", params)
        
        if not success:
            if self.pluginProgress:
                self.pluginProgress.setError("Failed to import RING graph.")
            return False
            
        return True

# Register the plugin so Tulip can discover and display it.
tulipplugins.registerPluginOfGroup(
    "OpenRINGForSelectedNode",       # internal identifier
    "Open RING For Selected Node",   # displayed name
    "Roden Luo",                     # author
    "04/04/2025",                    # creation date
    "Opens a RING graph for the selected node",  # short description
    "1.0",
    "ProteinCraft"
) 