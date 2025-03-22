from tulip import tlp
import tulipplugins

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

        # Gather selected nodes
        selected_nodes = [n for n in self.graph.getNodes() if view_selection[n]]

        if len(selected_nodes) < 2:
            # Nothing to reverse if fewer than 2 selected
            if self.pluginProgress:
                self.pluginProgress.setWarning("Fewer than 2 nodes selected. Nothing to do.")
            return True

        # Extract the x and y coordinates
        coords = [(n, view_layout[n][0], view_layout[n][1]) for n in selected_nodes]

        xs = [c[1] for c in coords]
        ys = [c[2] for c in coords]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        range_x = max_x - min_x
        range_y = max_y - min_y

        # Decide if it's horizontal or vertical
        # If range in x is larger, we call it horizontal
        # Otherwise, we call it vertical
        is_horizontal = (range_x >= range_y)

        # Sort coords by x if horizontal, otherwise by y
        if is_horizontal:
            coords.sort(key=lambda c: c[1])  # sort by x
        else:
            coords.sort(key=lambda c: c[2])  # sort by y

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
                # Keep old_y, just flip x
                view_layout[node] = tlp.Vec3f(reversed_positions[i], old_y, 0)
            else:
                # Keep old_x, just flip y
                view_layout[node] = tlp.Vec3f(old_x, reversed_positions[i], 0)

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
