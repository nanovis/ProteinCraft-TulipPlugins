# AF2igImport.py

from tulip import tlp
import tulipplugins
import csv
from tulipgui import tlpgui

class AF2igImport(tlp.Algorithm):
    """
    An example plugin that reads a CSV file and creates a node for each row,
    storing the row's values into Tulip properties.
    """

    def __init__(self, context):
        """
        The constructor calls the base class constructor.
        """
        tlp.Algorithm.__init__(self, context)
        
        # Define the parameter for the CSV file path
        self.addFileParameter(
            "CSV File",
            True,
            "Path to the CSV file to import",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_AF2ig.csv"
        )

    def check(self):
        """
        This method is called by Tulip to check if the algorithm can be run.
        """
        # Return (True, "") to signal that everything is OK.
        return (True, "")

    def run(self):
        """
        Implementation of the plugin. We:
          1) Retrieve the CSV file path from the parameters.
          2) Open and parse the CSV.
          3) For each row, create a node in a new graph.
          4) Store each CSV column in its own property.
        """
        csv_file = self.dataSet["CSV File"]
        if not csv_file:
            # If no file was provided, we cannot proceed.
            self.pluginProgress.setError("No CSV file path was provided.")
            return False

        # Create a new graph
        self.new_graph = tlp.newGraph()
        self.new_graph.setName("AF2ig")

        # We prepare Tulip properties to hold each column.
        # Note: The .csv example includes the header:
        #   binder_aligned_rmsd,pae_binder,pae_interaction,pae_target,
        #   plddt_binder,plddt_target,plddt_total,target_aligned_rmsd,
        #   time,description
        #
        # Adjust or add properties as needed for your columns.

        binder_aligned_rmsdP = self.new_graph.getDoubleProperty("binder_aligned_rmsd")
        pae_binderP          = self.new_graph.getDoubleProperty("pae_binder")
        pae_interactionP     = self.new_graph.getDoubleProperty("pae_interaction")
        pae_targetP          = self.new_graph.getDoubleProperty("pae_target")
        plddt_binderP        = self.new_graph.getDoubleProperty("plddt_binder")
        plddt_targetP        = self.new_graph.getDoubleProperty("plddt_target")
        plddt_totalP         = self.new_graph.getDoubleProperty("plddt_total")
        target_aligned_rmsdP = self.new_graph.getDoubleProperty("target_aligned_rmsd")
        timeP                = self.new_graph.getDoubleProperty("time")
        descriptionP         = self.new_graph.getStringProperty("description")

        # Now parse the CSV file, skipping header if present
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)

            # For each row in the CSV, create a node and set property values
            for row in reader:
                n = self.new_graph.addNode()

                # Safely convert numeric fields. If a field is empty or invalid,
                # you may want to handle it (here we do a straightforward float cast).
                try:
                    binder_aligned_rmsdP[n] = float(row["binder_aligned_rmsd"])
                except:
                    binder_aligned_rmsdP[n] = 0.0

                try:
                    pae_binderP[n] = float(row["pae_binder"])
                except:
                    pae_binderP[n] = 0.0

                try:
                    pae_interactionP[n] = float(row["pae_interaction"])
                except:
                    pae_interactionP[n] = 0.0

                try:
                    pae_targetP[n] = float(row["pae_target"])
                except:
                    pae_targetP[n] = 0.0

                try:
                    plddt_binderP[n] = float(row["plddt_binder"])
                except:
                    plddt_binderP[n] = 0.0

                try:
                    plddt_targetP[n] = float(row["plddt_target"])
                except:
                    plddt_targetP[n] = 0.0

                try:
                    plddt_totalP[n] = float(row["plddt_total"])
                except:
                    plddt_totalP[n] = 0.0

                try:
                    target_aligned_rmsdP[n] = float(row["target_aligned_rmsd"])
                except:
                    target_aligned_rmsdP[n] = 0.0

                try:
                    timeP[n] = float(row["time"])
                except:
                    timeP[n] = 0.0

                # 'description' is a string
                descriptionP[n] = row["description"]

        # Create a parallel coordinate view for the new graph
        pcv = tlpgui.createView("Parallel Coordinates view", self.new_graph)
        pcv.setOverviewVisible(False)
        
        # Activate specific properties in the parallel coordinates view
        # We need to set selectedProperties as a dictionary with numeric keys
        selected_props = {}
        selected_props["0"] = "binder_aligned_rmsd"
        selected_props["1"] = "pae_interaction" 
        selected_props["2"] = "plddt_total"
        
        # Update the state
        state = pcv.state()
        state["selectedProperties"] = selected_props
        pcv.setState(state)

        # If we get here, the import has succeeded
        return True

# Register the plugin with Tulip
tulipplugins.registerPlugin(
    "AF2igImport",                      # The class name (must match above)
    "AF2ig Import Algorithm",           # A short description for the plugin
    "YourName",                         # Author
    "2025",                             # Date or year
    "",                                 # Citation or reference
    "1.0"                               # Version
)
