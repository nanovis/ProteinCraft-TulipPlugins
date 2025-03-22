from tulip import tlp
import tulipplugins

def get_selected_nodes(graph, view_selection):
    """
    Get a list of selected nodes from the graph.
    
    Args:
        graph: The Tulip graph
        view_selection: The selection property of the graph
        
    Returns:
        List of selected nodes
    """
    return [n for n in graph.getNodes() if view_selection[n]]

def get_node_coordinates(graph, nodes, view_layout):
    """
    Extract coordinates for a list of nodes.
    
    Args:
        graph: The Tulip graph
        nodes: List of nodes to get coordinates for
        view_layout: The layout property of the graph
        
    Returns:
        List of tuples (node, x, y)
    """
    return [(n, view_layout[n][0], view_layout[n][1]) for n in nodes]

def determine_orientation(coords):
    """
    Determine if the nodes form a horizontal or vertical line.
    
    Args:
        coords: List of (node, x, y) tuples
        
    Returns:
        Tuple of (is_horizontal, range_x, range_y)
    """
    xs = [c[1] for c in coords]
    ys = [c[2] for c in coords]
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    range_x = max_x - min_x
    range_y = max_y - min_y
    
    is_horizontal = (range_x >= range_y)
    return is_horizontal, range_x, range_y

def sort_coordinates(coords, is_horizontal):
    """
    Sort coordinates based on orientation.
    
    Args:
        coords: List of (node, x, y) tuples
        is_horizontal: Boolean indicating if line is horizontal
        
    Returns:
        Sorted list of coordinates
    """
    if is_horizontal:
        return sorted(coords, key=lambda c: c[1])
    return sorted(coords, key=lambda c: c[2])

def reverse_node_positions(graph, coords, view_layout, is_horizontal):
    """
    Reverse the positions of nodes while maintaining their relative positions.
    
    Args:
        graph: The Tulip graph
        coords: List of (node, x, y) tuples
        view_layout: The layout property of the graph
        is_horizontal: Boolean indicating if line is horizontal
    """
    # Extract the sorted positions
    if is_horizontal:
        sorted_positions = [c[1] for c in coords]
    else:
        sorted_positions = [c[2] for c in coords]
    
    # Reverse the positions
    reversed_positions = list(reversed(sorted_positions))
    
    # Assign reversed positions back in the same sorted order
    for i, (node, old_x, old_y) in enumerate(coords):
        if is_horizontal:
            view_layout[node] = tlp.Vec3f(reversed_positions[i], old_y, 0)
        else:
            view_layout[node] = tlp.Vec3f(old_x, reversed_positions[i], 0)

class ReverseLine(tlp.Algorithm):
    """
    Detects whether the selected nodes form a mostly horizontal or mostly vertical line,
    and reverses their left-to-right or top-to-bottom order in place.
    """

    def __init__(self, context):
        tlp.Algorithm.__init__(self, context)

    def check(self):
        # Always return True, but we could add conditions (e.g., at least 2 selected nodes).
        return (True, "")

    def run(self):
        # Standard Tulip layout property
        view_layout = self.graph.getLayoutProperty("viewLayout")
        view_selection = self.graph.getBooleanProperty("viewSelection")

        # Get selected nodes
        selected_nodes = get_selected_nodes(self.graph, view_selection)

        if len(selected_nodes) < 2:
            # Nothing to reverse if fewer than 2 selected
            if self.pluginProgress:
                self.pluginProgress.setWarning("Fewer than 2 nodes selected. Nothing to do.")
            return True

        # Get coordinates and determine orientation
        coords = get_node_coordinates(self.graph, selected_nodes, view_layout)
        is_horizontal, range_x, range_y = determine_orientation(coords)
        
        # Sort and reverse positions
        sorted_coords = sort_coordinates(coords, is_horizontal)
        reverse_node_positions(self.graph, sorted_coords, view_layout, is_horizontal)

        if self.pluginProgress:
            orientation = "horizontal" if is_horizontal else "vertical"
            self.pluginProgress.setComment(
                f"Reversed order of {len(selected_nodes)} nodes along a {orientation} line."
            )

        return True


# Register the plugin so Tulip can discover it in the "ProteinCraft" group.
tulipplugins.registerPluginOfGroup(
    "ReverseLine",
    "Reverse Layout",
    "Roden Luo",
    "2025-03-21",
    "Reverses the order of selected nodes along a horizontal or vertical line",
    "1.0",
    "ProteinCraft"
)
