from tulip import tlp
import tulipplugins
from tulipgui import tlpgui
import csv

class UMAPImport(tlp.Algorithm):
    """
    A plugin that reads a CSV file containing UMAP coordinates for PDB files and creates:
    - Nodes for each PDB file
    - Positions nodes according to their UMAP coordinates
    - Stores coordinates as properties
    - Labels nodes with PDB filenames
    """

    def __init__(self, context):
        """
        Constructor initializes the algorithm and defines parameters
        """
        tlp.Algorithm.__init__(self, context)
        
        # Define the parameter for the input file path
        self.addFileParameter(
            "Input File",
            True,
            "Path to the CSV file containing UMAP coordinates",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_RF_umap.csv"
        )
        
        # Add scaling parameter for better visualization
        self.addFloatParameter(
            "Scale Factor", 
            "Scaling factor for the UMAP coordinates", 
            "1.0", 
            False,  # not mandatory
            True,   # input parameter
            False   # not output parameter
        )
        
        # Add color parameter for node coloring
        self.addColorParameter(
            "Node Color",
            "Color for the nodes in the visualization",
            "(0, 255, 95, 255)",  # Vivid red as default
            False,  # not mandatory
            True,   # input parameter
            False   # not output parameter
        )

    def check(self):
        """
        Verify that the algorithm can be run
        """
        return (True, "")

    def run(self):
        """
        Implementation of the algorithm:
        1) Read the CSV file
        2) Create nodes for each PDB file
        3) Position nodes according to UMAP coordinates
        4) Store coordinates as properties
        5) Create a graph visualization
        """
        # Get parameters
        input_file = self.dataSet["Input File"]
        if not input_file:
            self.pluginProgress.setError("No input file path was provided.")
            return False
            
        scale_factor = self.dataSet["Scale Factor"]
        node_color = self.dataSet["Node Color"]
        
        # Create a new graph
        self.new_graph = tlp.newGraph()
        self.new_graph.setName("UMAP Visualization")
        
        # Get standard Tulip properties
        viewLayout = self.new_graph.getLayoutProperty('viewLayout')
        viewColor = self.new_graph.getColorProperty('viewColor')
        viewLabel = self.new_graph.getStringProperty('viewLabel')
        
        # Create properties for UMAP coordinates
        x_coord = self.new_graph.getDoubleProperty('X')
        y_coord = self.new_graph.getDoubleProperty('Y')
        
        try:
            # Open and read the CSV file
            with open(input_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                # Check if required columns exist
                fieldnames = reader.fieldnames
                required_cols = ['filename', 'X', 'Y']
                for col in required_cols:
                    if col not in fieldnames:
                        self.pluginProgress.setError(f"Required column '{col}' not found in file.")
                        return False
                
                # Process each row
                row_counter = 0
                for row in reader:
                    # Create node
                    node = self.new_graph.addNode()
                    
                    # Set label to filename
                    viewLabel[node] = row['filename']
                    
                    # Store coordinates as properties
                    x_coord[node] = float(row['X'])
                    y_coord[node] = float(row['Y'])
                    
                    # Position node using scaled coordinates
                    # Note: We use Y as Z coordinate to create a 2D visualization
                    coord = tlp.Vec3f(
                        float(row['X']) * scale_factor,
                        float(row['Y']) * scale_factor,
                        0.0,  # Z coordinate set to 0 for 2D view
                    )
                    viewLayout[node] = coord
                    
                    # Set node color using the user-defined color
                    viewColor[node] = node_color
                    
                    row_counter += 1
                
                # Create a suitable view for the graph
                if row_counter > 0:
                    # Create a node link view
                    nlv = tlpgui.createView("Node Link Diagram view", self.new_graph)
                    if nlv:
                        # Set up initial view
                        nlv.setOverviewVisible(False)
                        # Set labels scaled to node sizes mode
                        renderingParameters = nlv.getRenderingParameters()
                        renderingParameters.setLabelScaled(True)
                        nlv.setRenderingParameters(renderingParameters)
                        # Center the layout
                        nlv.centerView()
                        
                self.pluginProgress.setComment(f"Imported {row_counter} PDB files from {input_file}.")
                return True
                
        except Exception as e:
            self.pluginProgress.setError(f"Error processing file: {str(e)}")
            return False


# Plugin documentation
pluginDoc = """
<p>A plugin for importing UMAP coordinate data from CSV files.
Creates a graph with nodes for each PDB file, positioned according to their UMAP coordinates.
Stores the original coordinates as properties and provides a 2D visualization of the UMAP space.
The scale factor parameter allows adjusting the visualization size for better viewing.</p>
"""

# Register the plugin with Tulip
tulipplugins.registerPluginOfGroup(
    "UMAPImport",                       # Class name
    "UMAP Coordinate Import",           # Plugin description
    "Roden Luo",                        # Author
    "2025",                             # Date/year
    pluginDoc,                          # Documentation
    "1.0",                              # Version
    "ProteinCraft"                      # Group
) 