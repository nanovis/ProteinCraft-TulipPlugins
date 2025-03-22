"""
Import plugin example to read a tab-delimited file that has:
 - a first column called "B_residue" (the main node label),
 - multiple columns,
 - a last column "Details" containing "|"-separated records.

One main node is created per row, laid out horizontally.
For each row's Details, we create sub-nodes, placed above the main node.

Residue type is used to color these sub-nodes. The residue type is the 4th
field in the detail string ("filename:chain:res_num:res_type").
"""

from tulip import tlp
import tulipplugins


class InteractionLogoImport(tlp.ImportModule):
    def __init__(self, context):
        """
        In the constructor, we declare the parameters needed by this import plugin.

        We require one file parameter: 'filename'.
        """
        tlp.ImportModule.__init__(self, context)
        self.addFileParameter('filename', True, 
                              'Tab-delimited input file containing B_residue and Details columns')

    def importGraph(self):
        """
        Main function called by Tulip to perform the import.
        """
        filename = self.dataSet['filename']

        # Get the standard Tulip properties for node positioning, color, etc.
        viewLayout = self.graph.getLayoutProperty('viewLayout')
        viewColor  = self.graph.getColorProperty('viewColor')
        viewLabel  = self.graph.getStringProperty('viewLabel')

        # Residue-type color map: adjust as you see fit
        # Feel free to add more residue types or modify the colors.
        residueColorMap = {
            'A': tlp.Color(255, 192, 192),  # e.g. light red
            'R': tlp.Color(192, 255, 192),  # e.g. light green
            'N': tlp.Color(192, 192, 255),  # e.g. light blue
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

        # We'll keep a simple horizontal spacing for main nodes
        x_spacing = 1.0
        y_main = 0.0  # all main nodes on y=0
        # Vertical offset and spacing for sub-nodes above each main node
        y_sub_offset = 0.5
        y_sub_spacing = 1.0

        # Read the file
        try:
            with open(filename, 'r') as f:
                lines = f.read().strip().split('\n')
        except Exception as e:
            if self.pluginProgress:
                self.pluginProgress.setError("Error reading file: " + str(e))
            return False

        # The first line is assumed to be header
        header = lines[0].split()
        # We'll find the indices of columns of interest
        try:
            bResidueIndex = header.index("B_residue")      # the main label
            detailsIndex = header.index("Details")       # the sub-nodes
        except ValueError as e:
            if self.pluginProgress:
                self.pluginProgress.setError("Could not find required columns: " + str(e))
            return False

        # Iterate on each row (skip header line)
        row_counter = 0
        for i, line in enumerate(lines[1:]):
            # Avoid empty lines if any
            if not line.strip():
                continue

            tokens = line.split('\t')
            if len(tokens) <= max(bResidueIndex, detailsIndex):
                continue  # skip malformed lines

            bResidue = tokens[bResidueIndex]
            details_str = tokens[detailsIndex]

            # Create the main node for this row
            main_node = self.graph.addNode()
            viewLabel[main_node] = bResidue

            # Layout the main node horizontally spaced
            main_coord = tlp.Vec3f(i * x_spacing, y_main, 0.0)
            viewLayout[main_node] = main_coord

            # Parse the details column, splitting by '|'
            if details_str.strip():
                detail_entries = details_str.split('|')
                # We place them each at some offset above main_node
                for j, entry in enumerate(detail_entries):
                    # Each entry is "filename:chain:resnum:restype"
                    fields = entry.split(':')
                    # Safely handle if they are not well-formed
                    if len(fields) < 4:
                        continue

                    file_name = fields[0]
                    chain = fields[1]
                    res_num = fields[2]
                    res_type = fields[3]

                    # Create a sub-node
                    sub_node = self.graph.addNode()
                    # Label it with chain and residue info, or anything you prefer
                    label_str = f"{chain}:{res_num}:{res_type}"
                    viewLabel[sub_node] = label_str

                    # Color it by residue type if we have one in the map, else grey
                    color = residueColorMap.get(res_type, tlp.Color(200, 200, 200))
                    viewColor[sub_node] = color

                    # Layout: place above the main node
                    # for j-th sub-node, we move a bit more up
                    sub_coord = tlp.Vec3f(
                        main_coord.getX(), 
                        main_coord.getY() + (j+1) * y_sub_spacing + y_sub_offset,
                        0.0
                    )
                    viewLayout[sub_node] = sub_coord

            row_counter += 1

        if self.pluginProgress:
            self.pluginProgress.setComment(f"Created {row_counter} main row nodes.")

        # Returning True indicates that the import succeeded
        return True


# Documentation about this plugin
pluginDoc = """
<p>Imports a tab-delimited file that has one row per design residue (B_residue),
plus a final column Details (pipe-separated). Creates a main node for each row,
and sub-nodes from Details above the main node. Sub-nodes are colored by their
residue type (fourth field in 'filename:chain:res_num:res_type').</p>
"""

# Register the plugin
tulipplugins.registerPluginOfGroup(
    'InteractionLogoImport',        # internal plugin name
    'ProteinCraft Interaction Logo',       # displayed name in Tulip
    'Roden Luo',                        # author
    '2025-03-20',                       # creation date
    pluginDoc,
    '1.0',                              # version
    'ProteinCraft'                              # plugin group
)

