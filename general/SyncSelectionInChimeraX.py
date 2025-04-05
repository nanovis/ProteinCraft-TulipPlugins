from tulip import tlp
import tulipplugins
import requests
import json

class SyncSelectionInChimeraX(tlp.Algorithm):
    """
    This plugin syncs the selected nodes with ChimeraX by sending a proteincraft sync command
    for each selected node's structure file.
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Let the user specify the base URL for ChimeraX's REST interface
        self.addStringParameter(
            "baseUrl",
            "ChimeraX REST URL (default port 45145)",
            "http://127.0.0.1:45145/run"
        )
        # Let the user specify the base path for the structure files
        self.addStringParameter(
            "basePath",
            "Base path for structure files",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_AF2ig_reindex"
        )

    def check(self):
        """
        Precheck method called before run().
        Return (True, '') if good to proceed or (False, 'error message') if not.
        """
        return (True, '')

    def run(self):
        """
        The main method that gets executed when the user clicks "Run".
        For each selected node, send a proteincraft sync command to ChimeraX.
        """
        base_url = self.dataSet["baseUrl"]
        base_path = self.dataSet["basePath"]

        # Create a dictionary for all selected nodes
        sync_data = {}
        
        # Get the root graph named "AF2ig"
        AF2ig_graph = None
        Tetris_graph = None
        UMAP_graph = None
        for g in tlp.getRootGraphs():
            if g.getName() == "AF2ig":
                AF2ig_graph = g
            elif g.getName() == "Tetris":
                Tetris_graph = g
            elif g.getName() == "UMAP":
                UMAP_graph = g

        if AF2ig_graph:
            viewSelection = AF2ig_graph.getBooleanProperty("viewSelection")
            description = AF2ig_graph.getStringProperty("description")
            # Gather selected nodes from the root graph
            selected_nodes = [n for n in AF2ig_graph.getNodes() if viewSelection[n]]

            for n in selected_nodes:
                filename = description[n]
                full_path = f"{base_path}/{filename}.pdb"
                node_id = str(n.id)
                sync_data[full_path] = {
                    "id": node_id,
                    "name": filename,
                    "display": True
                }

        if Tetris_graph:
            viewSelection = Tetris_graph.getBooleanProperty("viewSelection")
            description = Tetris_graph.getStringProperty("description")
            # Gather selected nodes from the root graph
            selected_nodes = [n for n in Tetris_graph.getNodes() if viewSelection[n]]

            for n in selected_nodes:
                filename = description[n]
                full_path = f"{base_path}/{filename}.pdb"
                node_id = str(n.id)
                sync_data[full_path] = {
                    "id": node_id,
                    "name": filename,
                    "display": True
                }

        # Construct the ChimeraX command
        command = f"proteincraft sync jsonString '{json.dumps(sync_data)}'"
        # print(command)
        
        try:
            response = requests.get(base_url, params={"command": command})
        except Exception as e:
            if self.pluginProgress:
                self.pluginProgress.setError(f"Failed to connect to ChimeraX: {e}")
            return False

        return True

# Register the plugin so Tulip can discover and display it.
tulipplugins.registerPluginOfGroup(
    "SyncSelectionInChimeraX",       # internal identifier
    "SyncSelectionInChimeraX",       # displayed name
    "Roden Luo",                     # author
    "04/04/2025",                    # creation date
    "Sync selected nodes with ChimeraX via proteincraft sync",  # short description
    "1.0",
    "ProteinCraft"
) 