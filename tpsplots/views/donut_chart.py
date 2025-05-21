"""Donut chart visualization specialized view."""
import matplotlib.pyplot as plt
import numpy as np
import textwrap
from pathlib import Path
from .chart_view import ChartView
import matplotlib.patches as mpatches

class DonutChartView(ChartView):
    """Specialized view for donut charts with a focus on exposing matplotlib's API."""
    
    def donut_plot(self, metadata, stem, **kwargs):
        """
        Generate donut charts for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments passed directly to matplotlib's plotting functions.
            Required parameters:
            - values: list/array - Values for each donut segment
            
            Common parameters:
            - labels: list - Labels for each segment
            - colors: list - Colors for each segment
            - center_text: str - Text to display in the center of the donut
            - center_color: str - Color of the center circle area
            - hole_size: float - Size of the donut hole (0.0-1.0, default: 0.7)
            - wedgeprops: dict - Properties for the wedges, defaults to 
                         {'linewidth': 7, 'edgecolor': 'white'}
            - show_percentages: bool - Whether to show percentage values in the chart
            - label_wrap_length: int - Max characters per line for labels (default: 15)
            - label_distance: float - Distance of labels from center (default: 1.2)
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)
    
    def _wrap_labels(self, labels, max_length=15):
        """
        Wrap long labels to multiple lines.
        
        Args:
            labels: List of label strings
            max_length: Maximum characters per line
            
        Returns:
            List of wrapped label strings
        """
        
        wrapped_labels = []
        for label in labels:
            if len(label) > max_length:
                # Use textwrap to break on word boundaries where possible
                wrapped = '\n'.join(textwrap.wrap(label, width=max_length,break_long_words=False))
                wrapped_labels.append(wrapped)
            else:
                wrapped_labels.append(label)
        return wrapped_labels
    
    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a donut chart with appropriate styling.
        
        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments passed directly to matplotlib
            
        Returns:
            matplotlib.figure.Figure: The created figure
            
        Raises:
            ValueError: If required parameters are missing
        """
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # Intercept title and subtitle parameters
        for text in ["title", "subtitle"]:
            if kwargs.get(text):
                metadata[text] = kwargs.pop(text)
        
        # Get required parameters
        values = kwargs.pop('values', None)
        
        if values is None or len(values) == 0:
            raise ValueError("The 'values' parameter is required for donut_plot")
        
        # Extract styling parameters
        labels = kwargs.pop('labels', None)
        colors = kwargs.pop('colors', None)
        label_wrap_length = kwargs.pop('label_wrap_length', style.get("label_wrap_length"))
        label_distance = kwargs.pop('label_distance', 1.4)  # Increased for less overlap
 
        # Wrap long labels
        if labels:
            # Convert to list if it's a tuple (which doesn't have copy method)
            original_labels = list(labels) if isinstance(labels, tuple) else labels.copy()
            labels = self._wrap_labels(original_labels, label_wrap_length)
        
        # Handle default wedge properties or use provided ones
        default_wedgeprops = {'linewidth': 7, 'edgecolor': 'white'}
        wedgeprops = kwargs.pop('wedgeprops', default_wedgeprops)
        
        # Extract other parameters
        hole_size = kwargs.pop('hole_size', 0.7)
        center_text = kwargs.pop('center_text', None)
        center_color = kwargs.pop('center_color', self.COLORS["light_gray"])
        show_percentages = kwargs.pop('show_percentages', True)
        
        # Calculate percentages for labels
        total = sum(values)
        percentages = [val / total * 100 for val in values]
        
        # Create formatted percentage strings
        pct_strings = [f"{p:.1f}%" for p in percentages]
        
        # Create the pie chart (which will become our donut)
        # No labels at this point, we'll add them manually
        wedges, _ = ax.pie(
            values,
            labels=None,  
            colors=colors,
            autopct=None,
            wedgeprops=wedgeprops,
            startangle=90,
            radius=1,  # The radius of the pie
            counterclock=False,  # Make it go clockwise for consistent positioning
            **kwargs
        )
        
        # Add custom positioned and formatted labels
        if labels:
            # Calculate wedge angles
            wedge_angles = []
            cumulative = 0
            for val in values:
                # The start and end angle of each wedge
                wedge_angle = val / total * 360
                midpoint = 90 - (cumulative + wedge_angle/2)  # 90 is the start angle (top of circle)
                wedge_angles.append(midpoint)
                cumulative += wedge_angle
            
            # Place labels with optimized positions and prevent overlap
            label_positions = []
            
            # Precalculate positions
            for i, (wedge, angle, label, pct) in enumerate(zip(wedges, wedge_angles, labels, pct_strings)):
                # Convert angle to radians for calculation
                rad_angle = np.radians(angle)
                
                # Calculate the position
                x = label_distance * np.cos(rad_angle)
                y = label_distance * np.sin(rad_angle)
                
                label_positions.append((x, y, rad_angle, label, pct))
            
            # Sort labels into quadrants
            top_right = []
            top_left = []
            bottom_left = []
            bottom_right = []
            
            for pos in label_positions:
                x, y = pos[0], pos[1]
                if x >= 0 and y >= 0:
                    top_right.append(pos)
                elif x < 0 and y >= 0:
                    top_left.append(pos)
                elif x < 0 and y < 0:
                    bottom_left.append(pos)
                else:
                    bottom_right.append(pos)
            
            # Sort each quadrant to avoid overlap (sort by y for left/right, by x for top/bottom)
            top_right.sort(key=lambda p: -p[1])  # Sort from top to bottom
            top_left.sort(key=lambda p: -p[1])   # Sort from top to bottom
            bottom_left.sort(key=lambda p: p[1]) # Sort from bottom to top
            bottom_right.sort(key=lambda p: p[1])  # Sort from bottom to top
            
            # Function to add vertical separation between labels
            def adjust_positions(positions, vertical_spacing=0.3):
                adjusted = []
                if not positions:
                    return adjusted
                
                adjusted.append(positions[0])
                for i in range(1, len(positions)):
                    prev = adjusted[i-1]
                    curr = positions[i]
                    
                    # Calculate adjusted y-position with minimum spacing
                    if prev[1] - curr[1] < vertical_spacing:
                        # Adjust y-coordinate
                        new_y = prev[1] - vertical_spacing
                        # Keep x-coordinate proportional to the adjusted position
                        new_x = curr[0]
                        adjusted.append((new_x, new_y, curr[2], curr[3], curr[4]))
                    else:
                        adjusted.append(curr)
                
                return adjusted
            
            # Apply vertical spacing adjustment to each quadrant
            top_right = adjust_positions(top_right, 0.1)
            top_left = adjust_positions(top_left,0.22)
            bottom_left = adjust_positions(bottom_left, -0.3)  # Negative for bottom sections
            bottom_right = adjust_positions(bottom_right, -0.4)  # Negative for bottom sections
            
            # Combine all adjusted positions
            adjusted_positions = top_right + top_left + bottom_left + bottom_right
            
            # Now draw the labels
            for i, (x, y, angle, label, pct) in enumerate(adjusted_positions):
                # Determine text alignment based on position
                ha = 'left' if x >= 0 else 'right'
                va = 'center'
                
                # For labels near the top or bottom, adjust vertical alignment
                if abs(y) > 0.8:
                    va = 'top' if y < 0 else 'bottom'
                
                # Add the label with percentage
                label_text = f"{label}\n({pct})" if show_percentages else label
                
                ax.text(
                    x, y, 
                    label_text,
                    ha=ha, 
                    va=va,
                    fontsize=style.get("legend_size", 14),
                    fontweight='normal',
                    bbox=dict(boxstyle="round,pad=0.3", fc='white', ec="none", alpha=0.7)
                )
        
        # Add the center circle to create the donut effect
        center_circle = plt.Circle(
            (0, 0), 
            hole_size, 
            fc=center_color
        )
        ax.add_artist(center_circle)
        
        # Add center text if provided
        if center_text:
            ax.text(
                0, 0,
                center_text,
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=style.get("title_size", 20),
                fontweight='bold'
            )
        
        # Equal aspect ratio ensures the pie is circular
        ax.set_aspect('equal')
        
        # Remove axes and grid
        ax.axis('off')
        
        # Expand the plot area to accommodate labels
        plt.tight_layout(pad=3.0)
        
        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig