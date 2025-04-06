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

def create_ring_graph(nodeFile, edgeFile):
    """
    Create a Tulip graph from RING node and edge files.
    
    Args:
        nodeFile (str): Path to the node file (e.g. "xxx_ringNodes")
        edgeFile (str): Path to the edge file (e.g. "xxx_ringEdges")
        
    Returns:
        tlp.Graph: The created graph with all properties set
        
    Raises:
        Exception: If there are errors reading the files or parsing the data
    """
    if not nodeFile or not edgeFile:
        raise ValueError("Both node and edge files must be provided.")

    # Create a new graph
    new_graph = tlp.newGraph()
    nodeFileBaseName = os.path.basename(nodeFile)
    fileBase = nodeFileBaseName.replace(".pdb_ringNodes","")
    new_graph.setName(f"RING_{fileBase}")

    # -- Create node properties for the data columns in the node file --
    chainProp      = new_graph.getStringProperty("chain")
    positionProp   = new_graph.getIntegerProperty("position")
    residueProp    = new_graph.getStringProperty("residue")
    typeProp       = new_graph.getStringProperty("resType")
    dsspProp       = new_graph.getStringProperty("dssp")
    degreeProp     = new_graph.getIntegerProperty("degree")
    bfactorProp    = new_graph.getDoubleProperty("bfactor_CA")
    pdbFileProp    = new_graph.getStringProperty("pdbFileName")
    modelProp      = new_graph.getIntegerProperty("model")
    nodeIdProp     = new_graph.getStringProperty("nodeId") 
    xProp         = new_graph.getDoubleProperty("x")
    yProp         = new_graph.getDoubleProperty("y")
    zProp         = new_graph.getDoubleProperty("z")

    # We'll store node coordinates in the standard 'viewLayout' property
    viewLayout     = new_graph.getLayoutProperty("viewLayout")

    # Also store NodeId in the standard 'viewLabel' for convenience
    viewLabel      = new_graph.getStringProperty("viewLabel")

    # Add viewShape property for node shapes
    viewShape      = new_graph.getIntegerProperty("viewShape")

    # Add viewColor property for node colors
    viewColor      = new_graph.getColorProperty("viewColor")

    # We'll store the NodeId -> Tulip node mapping here to help edge creation
    nodeMap = {}

    # ------------------ Parse the Node file ------------------
    try:
        with open(nodeFile, 'r') as f:
            lines = f.read().strip().split('\n')
    except Exception as e:
        raise Exception(f"Error reading node file: {e}")

    # Assume the first line is a header
    headerLine = lines[0].split('\t')
    colIndex = {colName: i for i, colName in enumerate(headerLine)}

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
        raise Exception(f"Missing required column in node file: {e}")

    # Iterate over each subsequent line to create nodes
    for line in lines[1:]:
        if not line.strip():
            continue  # skip empty lines

        tokens = line.split('\t')
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
        n = new_graph.addNode()

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

        # Set viewLabel with position
        viewLabel[n] = f"{positionProp[n]}:{one_letter}"

        # Set coordinates in 'viewLayout'
        viewLayout[n] = tlp.Vec3f(xCoord, yCoord, zCoord)
        xProp[n] = xCoord
        yProp[n] = yCoord
        zProp[n] = zCoord

        # Set node shape based on DSSP
        viewShape[n] = 15  # default shape
        if dssp == "E":
            viewShape[n] = 18
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
    # Create edge properties
    interactionProp = new_graph.getStringProperty("interaction")
    distanceProp    = new_graph.getDoubleProperty("distance")
    angleProp       = new_graph.getDoubleProperty("angle")
    atom1Prop       = new_graph.getStringProperty("atom1")
    atom2Prop       = new_graph.getStringProperty("atom2")
    donorProp       = new_graph.getStringProperty("donor")
    positiveProp    = new_graph.getStringProperty("positive")
    cationProp      = new_graph.getStringProperty("cation")
    orientationProp = new_graph.getStringProperty("orientation")
    edgeModelProp   = new_graph.getIntegerProperty("edgeModel")

    # Create edges between consecutive residues on the same chain
    chain_nodes = {}
    for node_id, node in nodeMap.items():
        chain = chainProp[node]
        pos = positionProp[node]
        if chain not in chain_nodes:
            chain_nodes[chain] = {}
        chain_nodes[chain][pos] = node

    # Add edges between consecutive positions within each chain
    for chain, positions in chain_nodes.items():
        sorted_positions = sorted(positions.keys())
        for i in range(len(sorted_positions) - 1):
            pos1 = sorted_positions[i]
            pos2 = sorted_positions[i + 1]
            if pos2 == pos1 + 1:
                node1 = positions[pos1]
                node2 = positions[pos2]
                edge = new_graph.addEdge(node1, node2)
                interactionProp[edge] = "COV:PEP"
                viewColor[edge] = tlp.Color(20, 20, 20, 255)

    try:
        with open(edgeFile, 'r') as f:
            lines = f.read().strip().split('\n')
    except Exception as e:
        raise Exception(f"Error reading edge file: {e}")

    headerLine = lines[0].split('\t')
    colIndex = {colName: i for i, colName in enumerate(headerLine)}

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
        raise Exception(f"Missing required column in edge file: {e}")

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

        if node1Str not in nodeMap or node2Str not in nodeMap:
            continue

        n1 = nodeMap[node1Str]
        n2 = nodeMap[node2Str]
        e = new_graph.addEdge(n1, n2)
        
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

    return new_graph

class RINGImport(tlp.Algorithm):
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
        tlp.Algorithm.__init__(self, context)
        # Add two file parameters for the user to choose in the plugin UI
        self.addFileParameter(
            "Node File",
            True,
            "Tab-delimited file describing nodes",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_RING/try1_7_dldesign_0_cycle1_af2pred.pdb_ringNodes"
        )
        self.addFileParameter(
            "Edge File",
            True,
            "Tab-delimited file describing edges",
            "/home/luod/ProteinCraft/run/4_PD-L1/outs_RING/try1_7_dldesign_0_cycle1_af2pred.pdb_ringEdges"
        )

    def check(self):
        """
        Verify that the algorithm can be run
        """
        return (True, "")

    def run(self):
        """
        Main function that creates and populates the graph from the input files.
        """
        try:
            nodeFile = self.dataSet["Node File"]
            edgeFile = self.dataSet["Edge File"]
            self.new_graph = create_ring_graph(nodeFile, edgeFile)
            return True
        except Exception as e:
            if self.pluginProgress:
                self.pluginProgress.setError(str(e))
            return False


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
