from tulip import tlp
import tulipplugins
from tulipgui import tlpgui
import csv

class TetrisImport(tlp.Algorithm):
    """
    A plugin that reads a tab-delimited file with residue interaction data and creates:
    - Main nodes for each residue row
    - Sub-nodes for detailed interactions
    - Stores all numeric data in Tulip properties
    - Colors nodes by residue type
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
            "Path to the tab-delimited file containing interaction data",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_tetris.csv"
        )
        
        # Add spacing parameters
        self.addFloatParameter(
            "Horizontal Spacing", 
            "Spacing between main nodes horizontally", 
            "1.0", 
            False,  # not mandatory
            True,   # input parameter
            False   # not output parameter
        )
        
        self.addFloatParameter(
            "Vertical Spacing", 
            "Spacing between sub-nodes vertically", 
            "1.0", 
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
        1) Read the tab-delimited file
        2) Create main nodes for each row with all numeric properties
        3) Parse detail strings to create sub-nodes
        4) Apply colors based on residue types
        5) Create a graph visualization
        """
        # Get parameters
        input_file = self.dataSet["Input File"]
        if not input_file:
            self.pluginProgress.setError("No input file path was provided.")
            return False
            
        # Hard coded column names
        main_label_col = "B_residue"
        details_col = "Details"
        
        x_spacing = self.dataSet["Horizontal Spacing"]
        y_sub_spacing = self.dataSet["Vertical Spacing"]
        
        # Create a new graph
        self.new_graph = tlp.newGraph()
        self.new_graph.setName("Residue Interaction Tetris")
        
        # Get standard Tulip properties
        viewLayout = self.new_graph.getLayoutProperty('viewLayout')
        viewColor = self.new_graph.getColorProperty('viewColor')
        viewLabel = self.new_graph.getStringProperty('viewLabel')
        viewShape = self.new_graph.getIntegerProperty('viewShape')
        
        # Dictionary to hold dynamic properties
        numericProps = {}
        
        # Predefine residue color map
        residueColorMap = {
            'A': tlp.Color(255, 192, 192),
            'R': tlp.Color(192, 255, 192),
            'N': tlp.Color(192, 192, 255),
            'D': tlp.Color(255, 128, 128),
            'C': tlp.Color(128, 255, 128),
            'Q': tlp.Color(128, 128, 255),
            'E': tlp.Color(255, 128, 255),
            'G': tlp.Color(128, 255, 255),
            'H': tlp.Color(200, 200, 100),
            'I': tlp.Color(200, 100, 200),
            'L': tlp.Color(180, 180, 180),
            'K': tlp.Color(100, 200, 100),
            'M': tlp.Color(200, 100, 100),
            'F': tlp.Color(120, 120, 255),
            'P': tlp.Color(130, 200, 200),
            'S': tlp.Color(255, 255, 128),
            'T': tlp.Color(255, 210, 150),
            'W': tlp.Color(150, 150, 220),
            'Y': tlp.Color(180, 180, 120),
            'V': tlp.Color(220, 220, 220)
        }
        
        # Define layout parameters
        y_main = 0.0
        y_sub_offset = 0.5
        
        try:
            # Open and read the file with csv module for better handling
            with open(input_file, 'r', newline='') as f:
                # Use tab delimiter explicitly for TSV files
                reader = csv.DictReader(f, delimiter='\t')
                
                # Check if required columns exist
                fieldnames = reader.fieldnames
                if main_label_col not in fieldnames:
                    self.pluginProgress.setError(f"Required column '{main_label_col}' not found in file.")
                    return False
                    
                if details_col not in fieldnames:
                    self.pluginProgress.setError(f"Required column '{details_col}' not found in file.")
                    return False
                
                # Create properties for all numeric columns
                for col in fieldnames:
                    if col != main_label_col and col != details_col:
                        numericProps[col] = self.new_graph.getDoubleProperty(col)
                
                # Process each row
                row_counter = 0
                for row in reader:
                    # Create main node
                    main_node = self.new_graph.addNode()
                    
                    # Parse B_residue to get components
                    b_residue_parts = row[main_label_col].split(':')
                    if len(b_residue_parts) >= 4:
                        b_chain, b_res_num, b_res_1letter, b_dssp = b_residue_parts
                        viewLabel[main_node] = row[main_label_col]
                        
                        # Set node shape based on DSSP
                        viewShape[main_node] = 15  # default shape
                        if b_dssp == "E":
                            viewShape[main_node] = 18
                        if b_dssp == "H":
                            viewShape[main_node] = 14
                    else:
                        viewLabel[main_node] = row[main_label_col]
                    
                    # Position the main node
                    main_coord = tlp.Vec3f(row_counter * x_spacing, y_main, 0.0)
                    viewLayout[main_node] = main_coord
                    
                    # Store numeric values
                    for col, prop in numericProps.items():
                        try:
                            prop[main_node] = float(row[col])
                        except (ValueError, TypeError):
                            prop[main_node] = 0.0
                    
                    # Process detailed data to create sub-nodes
                    details_str = row[details_col].strip()
                    if details_str:
                        detail_entries = details_str.split('|')
                        for j, entry in enumerate(detail_entries):
                            fields = entry.split(':')
                            if len(fields) < 5:
                                continue
                                
                            # Parse fields
                            chain = fields[1]
                            res_num = fields[2]
                            res_type = fields[3]
                            dssp = fields[4]
                            
                            # Create sub-node
                            sub_node = self.new_graph.addNode()
                            sub_label = f"{chain}:{res_num}:{res_type}:{dssp}"
                            viewLabel[sub_node] = sub_label
                            
                            # Color by residue type
                            color = residueColorMap.get(res_type, tlp.Color(200, 200, 200))
                            viewColor[sub_node] = color
                            
                            # Set node shape based on DSSP
                            viewShape[sub_node] = 15  # default shape
                            if dssp == "E":
                                viewShape[sub_node] = 7
                            if dssp == "H":
                                viewShape[sub_node] = 14
                            
                            # Position above the main node
                            sub_coord = tlp.Vec3f(
                                main_coord.getX(),
                                main_coord.getY() + y_sub_offset + (j+1)*y_sub_spacing,
                                0.0
                            )
                            viewLayout[sub_node] = sub_coord
                    
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
                        
                self.pluginProgress.setComment(f"Imported {row_counter} rows from {input_file}.")
                return True
                
        except Exception as e:
            self.pluginProgress.setError(f"Error processing file: {str(e)}")
            return False


# Plugin documentation
pluginDoc = """
<p>A general-purpose plugin for importing tab-delimited files with residue interaction data.
Creates a graph with main nodes for each residue row and sub-nodes for detailed interactions.
Automatically stores all numeric data as properties and applies residue-based coloring.
Customizable parameters allow for flexible use with different data formats.</p>
"""

# Register the plugin with Tulip
tulipplugins.registerPluginOfGroup(
    "TetrisImport",                       # Class name
    "Tetris Import",          # Plugin description
    "Roden Luo",                        # Author
    "2025",                             # Date/year
    pluginDoc,                          # Documentation
    "1.0",                              # Version
    "ProteinCraft"                      # Group
)
