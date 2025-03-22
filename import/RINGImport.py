from tulip import tlp
import tulipplugins
import os

# Map 3-letter to 1-letter codes
AA_3TO1 = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D',
    'CYS': 'C', 'GLN': 'Q', 'GLU': 'E', 'GLY': 'G',
    'HIS': 'H', 'ILE': 'I', 'LEU': 'L', 'LYS': 'K',
    'MET': 'M', 'PHE': 'F', 'PRO': 'P', 'SER': 'S',
    'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
}

def parse_ring_nodes(ring_nodes_file):
    """
    Parse the *_ringNodes file to find the maximum 'Position' for chain A.
    Returns an integer, e.g. 63 if the highest residue on chain A is 63.
    If no chain A found, returns 0 (no offset).
    """
    max_position_a = 0
    with open(ring_nodes_file, 'r') as f:
        # Skip header
        next(f)
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) < 3:
                continue
            chain = fields[1]  # e.g. 'A' or 'B'
            try:
                position = int(fields[2])
            except ValueError:
                continue
            if chain == 'A' and position > max_position_a:
                max_position_a = position
    return max_position_a

class RINGImport(tlp.ImportModule):
    """
    This plugin imports a graph from two TSV (tab-delimited) files:
      1) A node file, e.g. "xxx_ringNodes",
      2) An edge file, e.g. "xxx_ringEdges".

    Example columns (node file):
      NodeId  Chain Position Residue Type Dssp Degree Bfactor_CA x y z pdbFileName Model
      A:1:_:GLU A 1 GLU RES ... 25.364 -9.145 -9.022 ...
    
    Example columns (edge file):
      NodeId1 Interaction NodeId2 Distance Angle Atom1 Atom2 Donor Positive Cation Orientation Model
      A:1:_:GLU VDW:MC_SC A:4:_:LYS 2.707 ...
    """

    def __init__(self, context):
        tlp.ImportModule.__init__(self, context)
        # Add two file parameters for the user to choose in the plugin UI
        self.addFileParameter('nodeFile', True, 'Tab-delimited file describing nodes')
        self.addFileParameter('edgeFile', True, 'Tab-delimited file describing edges')

    def fileExtensions(self):
        """
        You can optionally declare recognized file extensions. 
        Here we leave it broad, returning an empty list so that 
        this plugin appears for all file types.
        """
        return []

    def importGraph(self):
        """
        Main function that Tulip calls to import the graph.
        """

        # -- Retrieve plugin parameters (the files chosen by user) --
        nodeFile = self.dataSet['nodeFile']
        edgeFile = self.dataSet['edgeFile']

        # Find the highest residue number on chain A (offset)
        offset_a = parse_ring_nodes(nodeFile)

        # -- Create node properties for the data columns in the node file --
        # You can create or reuse property names as you see fit.
        chainProp      = self.graph.getStringProperty("chain")
        positionProp   = self.graph.getIntegerProperty("position")
        residueProp    = self.graph.getStringProperty("residue")
        typeProp       = self.graph.getStringProperty("resType")
        dsspProp       = self.graph.getStringProperty("dssp")
        degreeProp     = self.graph.getIntegerProperty("degree")
        bfactorProp    = self.graph.getDoubleProperty("bfactor_CA")
        pdbFileProp    = self.graph.getStringProperty("pdbFileName")
        modelProp      = self.graph.getIntegerProperty("model")
        nodeIdProp     = self.graph.getStringProperty("nodeId") 
        xProp         = self.graph.getDoubleProperty("x")
        yProp         = self.graph.getDoubleProperty("y")
        zProp         = self.graph.getDoubleProperty("z")

        # We'll store node coordinates in the standard 'viewLayout' property
        viewLayout     = self.graph.getLayoutProperty("viewLayout")

        # Also store NodeId in the standard 'viewLabel' for convenience
        viewLabel      = self.graph.getStringProperty("viewLabel")

        # Add viewShape property for node shapes
        viewShape      = self.graph.getIntegerProperty("viewShape")

        # Add viewColor property for node colors
        viewColor      = self.graph.getColorProperty("viewColor")

        # We'll store the NodeId -> Tulip node mapping here to help edge creation
        nodeMap = {}

        # ------------------ Parse the Node file ------------------
        try:
            with open(nodeFile, 'r') as f:
                lines = f.read().strip().split('\n')
        except Exception as e:
            if self.pluginProgress:
                self.pluginProgress.setError(f"Error reading node file: {e}")
            return False

        # Assume the first line is a header
        # Example header: NodeId  Chain  Position  Residue  Type ...
        headerLine = lines[0].split('\t')
        # Let's define an index lookup so we can parse columns more robustly:
        colIndex = {colName: i for i, colName in enumerate(headerLine)}

        # If you prefer, you can require specific column names. 
        # For example, if "NodeId" is guaranteed, do:
        try:
            nodeIdIdx = colIndex["NodeId"]
            chainIdx = colIndex["Chain"]
            positionIdx = colIndex["Position"]
            residueIdx = colIndex["Residue"]
            typeIdx = colIndex["Type"]
            dsspIdx = colIndex["Dssp"]
            degreeIdx = colIndex["Degree"]
            bfactorIdx = colIndex["Bfactor_CA"]
            xIdx = colIndex["x"]
            yIdx = colIndex["y"]
            zIdx = colIndex["z"]
            pdbFileIdx = colIndex["pdbFileName"]
            modelIdx = colIndex["Model"]
        except KeyError as e:
            if self.pluginProgress:
                self.pluginProgress.setError(f"Missing required column in node file: {e}")
            return False

        # Iterate over each subsequent line to create nodes
        for line in lines[1:]:
            if not line.strip():
                continue  # skip empty lines

            tokens = line.split('\t')
            # Make sure we have enough columns:
            if len(tokens) <= max(nodeIdIdx, modelIdx):
                continue  # skip malformed line

            nodeIdStr    = tokens[nodeIdIdx]
            chain        = tokens[chainIdx]
            positionStr  = tokens[positionIdx]
            residue      = tokens[residueIdx]
            resType      = tokens[typeIdx]
            dssp         = tokens[dsspIdx]
            degreeStr    = tokens[degreeIdx]
            bfactorStr   = tokens[bfactorIdx]
            xStr         = tokens[xIdx]
            yStr         = tokens[yIdx]
            zStr         = tokens[zIdx]
            pdbFileName  = tokens[pdbFileIdx]
            modelStr     = tokens[modelIdx]

            # Create a new Tulip node
            n = self.graph.addNode()

            # Fill in the properties
            nodeIdProp[n]     = nodeIdStr
            chainProp[n]      = chain
            residueProp[n]    = residue
            typeProp[n]       = resType
            dsspProp[n]       = dssp
            pdbFileProp[n]    = pdbFileName

            # Convert numeric fields from string
            try:
                positionProp[n]   = int(positionStr) if positionStr else 0
                degreeProp[n]     = int(degreeStr) if degreeStr else 0
                bfactorProp[n]    = float(bfactorStr) if bfactorStr else 0.0
                xCoord            = float(xStr) if xStr else 0.0
                yCoord            = float(yStr) if yStr else 0.0
                zCoord            = float(zStr) if zStr else 0.0
                modelProp[n]      = int(modelStr) if modelStr else 0
            except ValueError:
                # fallback to defaults
                positionProp[n]   = 0
                degreeProp[n]     = 0
                bfactorProp[n]    = 0.0
                xCoord            = 0.0
                yCoord            = 0.0
                zCoord            = 0.0
                modelProp[n]      = 0

            # Convert 3-letter code to 1-letter code
            one_letter = AA_3TO1.get(residue, 'X')  # Use 'X' if residue not found in mapping

            # Set viewLabel with position offset for chain B
            if chain == 'B':
                display_position = positionProp[n] + offset_a
            else:
                display_position = positionProp[n]
            
            viewLabel[n] = f"{display_position}:{one_letter}"

            # Set coordinates in 'viewLayout'
            viewLayout[n] = tlp.Vec3f(xCoord, yCoord, zCoord)
            xProp[n] = xCoord
            yProp[n] = yCoord
            zProp[n] = zCoord

            # Set node shape based on DSSP
            viewShape[n] = 15  # default shape
            if dssp == "E":
                viewShape[n] = 7
            if dssp == "H":
                viewShape[n] = 14

            # Set node color based on chain
            if chain == "A":
                viewColor[n] = tlp.Color(129, 109, 249, 255)
            elif chain == "B":
                viewColor[n] = tlp.Color(251, 134, 134, 255)

            # Keep track of NodeId->node mapping for edge creation
            nodeMap[nodeIdStr] = n

        # ------------------ Parse the Edge file ------------------
        # We will create edges for each line that references existing NodeId1 and NodeId2
        # Then store other columns in edge properties.

        # Create edge properties
        interactionProp = self.graph.getStringProperty("interaction")
        distanceProp    = self.graph.getDoubleProperty("distance")
        angleProp       = self.graph.getDoubleProperty("angle")
        atom1Prop       = self.graph.getStringProperty("atom1")
        atom2Prop       = self.graph.getStringProperty("atom2")
        donorProp       = self.graph.getStringProperty("donor")
        positiveProp    = self.graph.getStringProperty("positive")
        cationProp      = self.graph.getStringProperty("cation")
        orientationProp = self.graph.getStringProperty("orientation")
        edgeModelProp   = self.graph.getIntegerProperty("edgeModel")

        # Create edges between consecutive residues on the same chain
        # First, organize nodes by chain and position
        chain_nodes = {}
        for node_id, node in nodeMap.items():
            chain = chainProp[node]
            pos = positionProp[node]
            if chain not in chain_nodes:
                chain_nodes[chain] = {}
            chain_nodes[chain][pos] = node

        # Add edges between consecutive positions within each chain
        for chain, positions in chain_nodes.items():
            sorted_positions = sorted(positions.keys())  # Sort positions numerically
            for i in range(len(sorted_positions) - 1):
                pos1 = sorted_positions[i]
                pos2 = sorted_positions[i + 1]
                # Only connect if positions are consecutive
                if pos2 == pos1 + 1:
                    node1 = positions[pos1]
                    node2 = positions[pos2]
                    edge = self.graph.addEdge(node1, node2)
                    interactionProp[edge] = "COV:PEP"
                    # Set edge color for COV:PEP (backbone)
                    viewColor[edge] = tlp.Color(20, 20, 20, 255)

        try:
            with open(edgeFile, 'r') as f:
                lines = f.read().strip().split('\n')
        except Exception as e:
            if self.pluginProgress:
                self.pluginProgress.setError(f"Error reading edge file: {e}")
            return False

        headerLine = lines[0].split('\t')
        colIndex = {colName: i for i, colName in enumerate(headerLine)}

        # Attempt to find needed columns:
        try:
            nodeId1Idx = colIndex["NodeId1"]
            interactionIdx = colIndex["Interaction"]
            nodeId2Idx = colIndex["NodeId2"]
            distanceIdx = colIndex["Distance"]
            angleIdx = colIndex["Angle"]
            atom1Idx = colIndex["Atom1"]
            atom2Idx = colIndex["Atom2"]
            donorIdx = colIndex["Donor"]
            positiveIdx = colIndex["Positive"]
            cationIdx = colIndex["Cation"]
            orientationIdx = colIndex["Orientation"]
            eModelIdx = colIndex["Model"]
        except KeyError as e:
            if self.pluginProgress:
                self.pluginProgress.setError(f"Missing required column in edge file: {e}")
            return False

        for line in lines[1:]:
            if not line.strip():
                continue
            tokens = line.split('\t')
            if len(tokens) <= max(nodeId2Idx, eModelIdx):
                continue

            node1Str     = tokens[nodeId1Idx]
            interaction  = tokens[interactionIdx]
            node2Str     = tokens[nodeId2Idx]
            distanceStr  = tokens[distanceIdx]
            angleStr     = tokens[angleIdx]
            atom1        = tokens[atom1Idx]
            atom2        = tokens[atom2Idx]
            donor        = tokens[donorIdx]
            positive     = tokens[positiveIdx]
            cation       = tokens[cationIdx]
            orientation  = tokens[orientationIdx]
            emodelStr    = tokens[eModelIdx]

            # Check if these NodeIds exist in nodeMap
            if node1Str not in nodeMap or node2Str not in nodeMap:
                # Possibly the edge references nodes we didn't parse or don't exist
                continue

            # Create the edge
            n1 = nodeMap[node1Str]
            n2 = nodeMap[node2Str]
            e = self.graph.addEdge(n1, n2)
            
            # Fill edge properties
            interactionProp[e] = interaction
            atom1Prop[e]       = atom1
            atom2Prop[e]       = atom2
            donorProp[e]       = donor
            positiveProp[e]    = positive
            cationProp[e]      = cation
            orientationProp[e] = orientation

            # Set edge color based on interaction type
            if interaction.startswith("COV"):
                viewColor[e] = tlp.Color(20, 20, 20, 255)  # Black
            elif interaction.startswith("VDW"):
                viewColor[e] = tlp.Color(180, 180, 180, 255)  # Light gray
            elif interaction.startswith("HBOND"):
                viewColor[e] = tlp.Color(61, 119, 176, 255)  # Blue
            else:
                viewColor[e] = tlp.Color(255, 28, 77, 255)  # Red

            # Convert numeric fields
            try:
                distanceProp[e] = float(distanceStr) if distanceStr else 0.0
            except ValueError:
                distanceProp[e] = 0.0

            try:
                angleProp[e] = float(angleStr) if angleStr else 0.0
            except ValueError:
                angleProp[e] = 0.0

            try:
                edgeModelProp[e] = int(emodelStr) if emodelStr else 0
            except ValueError:
                edgeModelProp[e] = 0

        nodeFileBaseName = os.path.basename(nodeFile)
        fileBase = nodeFileBaseName.replace(".pdb_ringNodes","")
        self.graph.setName(f"RING_{fileBase}")

        # If we reach here, we successfully parsed both files and created a graph
        return True


pluginDoc = """
<p>This plugin imports a graph from two TSV (tab-delimited) files:</p>
<ol>
<li>A node file, e.g. <code>xxx_ringNodes</code>,</li>
<li>An edge file, e.g. <code>xxx_ringEdges</code>.</li>
</ol>

<p><strong>Example columns (node file):</strong></p>
<pre>
NodeId      Chain  Position  Residue  Type  Dssp  Degree  Bfactor_CA    x       y       z     pdbFileName  Model
A:1:_:GLU   A      1         GLU      RES   ...   25.364  -9.145        -9.022  ...</pre>

<p><strong>Example columns (edge file):</strong></p>
<pre>
NodeId1      Interaction  NodeId2      Distance  Angle  Atom1  Atom2  Donor  Positive  Cation  Orientation  Model
A:1:_:GLU    VDW:MC_SC    A:4:_:LYS    2.707     ...
</pre>

<p>It stores node attributes (e.g. chain, residue, coordinates, etc.) and edge attributes (e.g. interaction type, distance, angle, etc.) in Tulip properties.</p>
"""

# Register the plugin so Tulip can discover it. Adapt the name as you like.
tulipplugins.registerPluginOfGroup(
    "RINGImport",           # internal plugin name
    "ProteinCraft RING Import",  # displayed plugin name
    "Roden Luo",                    # author
    "2025-03-21",                  # creation date
    pluginDoc,
    "1.0",                         # version
    "ProteinCraft"                         # plugin group
)
