from tulip import tlp
import tulipplugins

# We will need the 'requests' library to send the REST commands to ChimeraX.
# Make sure the 'requests' package is installed in your Python environment.
import requests

class ShowSelectionInChimeraX(tlp.Algorithm):
    """
    This plugin shows the ChimeraX structures that correspond
    to the Tulip node IDs currently selected in the graph.
    It sends a REST call like "show #<nodeID> cartoon" for each selected node.
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        # Let the user specify the base URL for ChimeraX's REST interface
        self.addStringParameter(
            "baseUrl",
            "ChimeraX REST URL (default port 45145)",
            "http://127.0.0.1:45145/run"
        )
        # Optionally let the user pick what representation to show,
        # e.g. "car" (cartoon) or "stick" or "ribbon".
        self.addStringParameter(
            "representation",
            "Representation to show in ChimeraX (e.g. car, cartoon, stick, etc.)",
            "car"
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
        Iterate over selected nodes, for each, send a 'show #<id> <rep>' command to ChimeraX.
        """
        base_url = self.dataSet["baseUrl"]
        rep = self.dataSet["representation"]
        viewSelection = self.graph.getBooleanProperty("viewSelection")

        # Gather selected nodes:
        selected_nodes = [n for n in self.graph.getNodes() if viewSelection[n]]

        if not selected_nodes:
            # No nodes selected, nothing to do
            if self.pluginProgress:
                self.pluginProgress.setWarning("No nodes selected.")
            return True

        for n in selected_nodes:
            node_id = n.id  # This is the internal integer ID of the node in Tulip
            # Construct a ChimeraX command; for example:
            # "show #<node_id> car"
            command = f"show #{node_id} {rep}"
            if self.pluginProgress:
                self.pluginProgress.setComment(f"Sending to ChimeraX: {command}")

            try:
                response = requests.get(base_url, params={"command": command})
                # Optionally print or log the response
                if self.pluginProgress:
                    self.pluginProgress.setComment(f"Response: {response.text}")
            except Exception as e:
                if self.pluginProgress:
                    self.pluginProgress.setError(f"Failed to connect to ChimeraX: {e}")
                return False

        return True

# Register the plugin so Tulip can discover and display it.
tulipplugins.registerPluginOfGroup(
    "ShowSelectionInChimeraX",       # internal identifier
    "ShowSelectionInChimeraX",       # displayed name
    "Roden Luo",                      # author
    "21/03/2025",                    # creation date
    "Show node-based structures in ChimeraX via REST",  # short description
    "1.0",
    "ProteinCraft"
)

