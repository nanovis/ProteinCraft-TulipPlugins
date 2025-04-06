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
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_AF2ig_score.csv"
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

        # Dictionary to hold dynamic properties
        numericProps = {}
        stringProps = {}

        # Now parse the CSV file, skipping header if present
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            # Create properties for all columns
            for col in fieldnames:
                if col == "description":
                    stringProps[col] = self.new_graph.getStringProperty(col)
                else:
                    numericProps[col] = self.new_graph.getDoubleProperty(col)

            # For each row in the CSV, create a node and set property values
            for row in reader:
                n = self.new_graph.addNode()

                # Set string property
                stringProps["description"][n] = row["description"]

                # Set numeric properties
                for col in numericProps:
                    try:
                        numericProps[col][n] = float(row[col])
                    except:
                        numericProps[col][n] = 0.0

        # Create a parallel coordinate view for the new graph
        pcv = tlpgui.createView("Parallel Coordinates view", self.new_graph)
        pcv.setOverviewVisible(False)
        
        # Activate specific properties in the parallel coordinates view
        # We need to set selectedProperties as a dictionary with numeric keys
        selected_props = {}
        selected_props["0"] = "binder_aligned_rmsd"
        selected_props["1"] = "pae_interaction" 
        selected_props["2"] = "plddt_total"
        selected_props["3"] = "inter_chain_total"
        selected_props["4"] = "inter_chain_without_vdw"
        selected_props["5"] = "inter_chain_hbond"
        selected_props["6"] = "inter_chain_vdw"
        selected_props["7"] = "inter_chain_other"
        selected_props["8"] = "binder_components_bonds"
        selected_props["9"] = "binder_components_bonds_without_vdw"
        selected_props["10"] = "binder_target_bonds"
        selected_props["11"] = "binder_target_bonds_largest_component"
        selected_props["12"] = "binder_target_bonds_no_vdw"
        selected_props["13"] = "binder_target_bonds_no_vdw_largest_component"

        selected_props_order = {}
        selected_props_order["0"] = False
        selected_props_order["1"] = False
        selected_props_order["2"] = True
        selected_props_order["3"] = True
        selected_props_order["4"] = True
        selected_props_order["5"] = True
        selected_props_order["6"] = True
        selected_props_order["7"] = True
        selected_props_order["8"] = True
        selected_props_order["9"] = True
        selected_props_order["10"] = True
        selected_props_order["11"] = True
        selected_props_order["12"] = True
        selected_props_order["13"] = True
        
        # Update the state
        state = pcv.state()
        state["selectedProperties"] = selected_props
        state["selectedPropertiesOrder"] = selected_props_order
        pcv.setState(state)

        # If we get here, the import has succeeded
        return True

# Register the plugin with Tulip
tulipplugins.registerPluginOfGroup(
    "AF2igImport",                      # The class name (must match above)
    "AF2ig Import Algorithm",           # A short description for the plugin
    "Roden Luo",                         # Author
    "2025",                             # Date or year
    "",                                 # Citation or reference
    "1.0",                               # Version
    "ProteinCraft"
)
