from tulip import tlp
import tulipplugins
import requests
import json

class SyncBondInChimeraX(tlp.Algorithm):
    """
    This plugin syncs the selected edges with ChimeraX by sending a proteincraft sync_bonds command
    for each selected edge's atom pair.
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)
        self.addStringParameter(
            "base url",
            "ChimeraX REST URL (default port 45145)",
            "http://127.0.0.1:45145/run"
        )

    def check(self):
        return (True, '')

    def run(self):
        base_url = self.dataSet["base url"]

        # Create a dictionary for all selected edges
        bond_data = []

        # Get the root graph
        viewSelection = self.graph.getBooleanProperty("viewSelection")
        chainProp = self.graph.getStringProperty("chain")
        positionProp = self.graph.getIntegerProperty("position")
        atom1Prop = self.graph.getStringProperty("atom1")
        atom2Prop = self.graph.getStringProperty("atom2")

        # Gather selected edges
        selected_edges = [e for e in self.graph.getEdges() if viewSelection[e]]

        for e in selected_edges:
            # get the nodes of the edge
            n1 = self.graph.source(e)
            n2 = self.graph.target(e)
            chain1 = chainProp[n1]
            chain2 = chainProp[n2]
            pos1 = positionProp[n1]
            pos2 = positionProp[n2]

            # While reading, atom1 is set to source node, atom2 is set to target node
            atom1 = atom1Prop[e]
            atom2 = atom2Prop[e]

            bond_data.append({"chain1": chain1, "pos1": pos1, "atom1": atom1, "chain2": chain2, "pos2": pos2, "atom2": atom2})

        # Construct the ChimeraX command
        command = f"proteincraft sync_bonds jsonString '{json.dumps(bond_data)}'"
        print(f"Command sent to ChimeraX: {command}")

        try:
            response = requests.get(base_url, params={"command": command})
            print(f"Response from ChimeraX: {response.text}")
        except Exception as e:
            if self.pluginProgress:
                self.pluginProgress.setError(f"Failed to connect to ChimeraX: {e}")
            return False

        return True

# Register the plugin so Tulip can discover and display it.
tulipplugins.registerPluginOfGroup(
    "SyncBondInChimeraX",       # internal identifier
    "SyncBondInChimeraX",       # displayed name
    "Roden Luo",                # author
    "04/04/2025",               # creation date
    "Sync selected edges with ChimeraX via proteincraft sync_bonds",  # short description
    "1.0",
    "ProteinCraft"
)
