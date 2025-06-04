"""US Map with pie charts visualization specialized view using geopandas and scatter-based pie charts."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .chart_view import ChartView
import logging

logger = logging.getLogger(__name__)

class USMapPieChartView(ChartView):
    """Specialized view for displaying pie charts overlaid on a US map at specific locations."""
    
    # NASA Center locations (updated coordinates)
    NASA_CENTERS = {
        # Full names
        'Kennedy Space Center': {'lat': 28.5744, 'lon': -80.6520, 'state': 'FL'},
        'Johnson Space Center': {'lat': 29.5529, 'lon': -95.0934, 'state': 'TX'},
        'Marshall Space Flight Center': {'lat': 34.6459, 'lon': -86.6756, 'state': 'AL'},
        'Goddard Space Flight Center': {'lat': 38.9977, 'lon': -76.8525, 'state': 'MD'},
        'Jet Propulsion Laboratory': {'lat': 34.2013, 'lon': -118.1714, 'state': 'CA'},
        'Ames Research Center': {'lat': 37.419167, 'lon': -122.060556, 'state': 'CA'},
        'Glenn Research Center': {'lat': 41.4161, 'lon': -81.8583, 'state': 'OH'},
        'Langley Research Center': {'lat': 37.085639, 'lon': -76.380667, 'state': 'VA'},
        'Stennis Space Center': {'lat': 30.3620, 'lon': -89.5994, 'state': 'MS'},
        
        # Abbreviations (using same updated coordinates)
        'HQ': {'lat': 38.8833, 'lon': -77.0167, 'state': 'DC'},  # NASA Headquarters, Washington DC
        'ARC': {'lat': 37.419167, 'lon': -122.060556, 'state': 'CA'},  # Ames Research Center
        'AFRC': {'lat': 34.9593, 'lon': -117.8825, 'state': 'CA'},  # Armstrong Flight Research Center (Edwards AFB)
        'GRC': {'lat': 41.4161, 'lon': -81.8583, 'state': 'OH'},  # Glenn Research Center
        'GSFC': {'lat': 38.9977, 'lon': -76.8525, 'state': 'MD'},  # Goddard Space Flight Center
        'JSC': {'lat': 29.5529, 'lon': -95.0934, 'state': 'TX'},  # Johnson Space Center
        'KSC': {'lat': 28.5744, 'lon': -80.6520, 'state': 'FL'},  # Kennedy Space Center
        'LaRC': {'lat': 37.085639, 'lon': -76.380667, 'state': 'VA'},  # Langley Research Center
        'MSFC': {'lat': 34.6459, 'lon': -86.6756, 'state': 'AL'},  # Marshall Space Flight Center
        'SSC': {'lat': 30.3620, 'lon': -89.5994, 'state': 'MS'},  # Stennis Space Center
        
        # Alternative full names and common variations
        'NASA Headquarters': {'lat': 38.8833, 'lon': -77.0167, 'state': 'DC'},
        'Armstrong Flight Research Center': {'lat': 34.9593, 'lon': -117.8825, 'state': 'CA'},
        'Dryden Flight Research Center': {'lat': 34.9593, 'lon': -117.8825, 'state': 'CA'},  # Former name for AFRC
    }
    
    def us_map_pie_plot(self, metadata, stem, **kwargs):
        """
        Generate US map with pie charts at specified locations for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Required parameters:
            - pie_data: dict - Dictionary where keys are location names and values are 
                       dictionaries containing pie chart data
                       Example: {
                           'Kennedy Space Center': {
                               'values': [30, 50, 20],
                               'labels': ['Science', 'Exploration', 'Operations'],
                               'colors': ['#037CC2', '#643788', '#FF5D47']
                           }
                       }
            
            Optional parameters:
            - pie_size_column: str - Column name to use for sizing pies (makes them proportional)
            - base_pie_size: float - Base size for pie charts (default: 800)
            - max_pie_size: float - Maximum size for pie charts when using proportional sizing (default: 1500)
            - min_pie_size: float - Minimum size for pie charts when using proportional sizing (default: 400)
            - custom_locations: dict - Custom location coordinates to override defaults
            - show_state_boundaries: bool - Whether to show state boundaries (default: True)
            - show_pie_labels: bool - Whether to show labels on pie charts (default: False)
            - show_percentages: bool - Whether to show percentage values on pie segments (default: False)
            - legend_location: str - Location for legend (default: 'lower left')
            - pie_edge_color: str - Edge color for pie charts (default: 'white')
            - pie_edge_width: float - Edge width for pie charts (default: 2)
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)
    
    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a US map with pie charts using the scatter-based approach.
        
        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments for map creation
            
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract required parameters
        pie_data = kwargs.pop('pie_data', None)
        if pie_data is None:
            raise ValueError("pie_data is required for us_map_pie_plot")
        
        # Extract optional parameters
        pie_size_column = kwargs.pop('pie_size_column', None)
        base_pie_size = kwargs.pop('base_pie_size', 800)
        max_pie_size = kwargs.pop('max_pie_size', 1500)
        min_pie_size = kwargs.pop('min_pie_size', 400)
        custom_locations = kwargs.pop('custom_locations', {})
        show_state_boundaries = kwargs.pop('show_state_boundaries', True)
        show_pie_labels = kwargs.pop('show_pie_labels', False)
        show_percentages = kwargs.pop('show_percentages', False)
        legend_location = kwargs.pop('legend_location', 'lower left')
        pie_edge_color = kwargs.pop('pie_edge_color', 'white')
        pie_edge_width = kwargs.pop('pie_edge_width', 2)
        
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # Load and plot US states
        try:
            import geopandas as gpd
            
            # Try local file first, then fallback to remote
            try:
                from tpsplots import PACKAGE_ROOT
                states_file = PACKAGE_ROOT / "data_sources" / "us-states.geojson"
                states = gpd.read_file(states_file)
                # Filter out Alaska and Hawaii
                states = states[~states['id'].isin(['AK', 'HI'])]
            except Exception:
                # Fallback to remote Natural Earth data
                states = gpd.read_file(
                    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_1_states_provinces.geojson"
                ).query("iso_3166_2.str.startswith('US-') and iso_3166_2 != 'US-AK' and iso_3166_2 != 'US-HI'")
            
            # Plot the base map
            states.plot(
                ax=ax,
                facecolor='lightgray',
                edgecolor='white' if show_state_boundaries else 'lightgray',
                linewidth=0.5 if show_state_boundaries else 0.1,
                alpha=0.7
            )
            
        except Exception as e:
            logger.warning(f"Could not load US states data: {e}, using fallback map")
            self._create_fallback_map(ax)
        
        # Combine default locations with custom ones
        all_locations = {**self.NASA_CENTERS, **custom_locations}
        
        # Calculate pie sizes if using proportional sizing
        pie_sizes = self._calculate_pie_sizes(pie_data, pie_size_column, 
                                            base_pie_size, min_pie_size, max_pie_size)
        
        # Create pie charts at each location using scatter-based approach
        legend_elements = []
        legend_labels = set()
        
        for location_name, data in pie_data.items():
            if location_name not in all_locations:
                logger.warning(f"Location '{location_name}' not found in location database")
                continue
            
            location_info = all_locations[location_name]
            lat, lon = location_info['lat'], location_info['lon']
            
            # Get pie chart data
            values = data.get('values', [])
            labels = data.get('labels', [])
            colors = data.get('colors', self._get_default_pie_colors(len(values)))
            
            if not values:
                continue
            
            # Get pie size
            pie_size = pie_sizes.get(location_name, base_pie_size)
            
            # Draw pie chart using scatter-based method
            self._draw_pie(values, lon, lat, pie_size, colors, ax, show_percentages)
            
            # Collect legend information (avoid duplicates)
            for label, color in zip(labels, colors):
                if label not in legend_labels:
                    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, edgecolor='white'))
                    legend_labels.add(label)
        
        # Add legend
        if legend_elements:
            ax.legend(legend_elements, list(legend_labels), 
                     loc=legend_location, fontsize=style.get("legend_size", 12),
                     frameon=True, fancybox=True, shadow=True)
        
        # Set map bounds with proper geographic aspect ratio
        ax.set_xlim(-125, -66.5)
        ax.set_ylim(20, 50)
        
        # Use appropriate aspect ratio for continental US (not equal)
        # Continental US is roughly 2.5:1 width to height ratio
        ax.set_aspect(1.3)  # Adjust this value to get the right map proportions
        
        # Remove axes for cleaner look
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Apply layout adjustments
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _draw_pie(self, values, xpos, ypos, size, colors, ax, show_percentages=False):
        """
        Draw a pie chart using scatter plots with custom markers.
        Based on the scatter-pie approach from the baseline implementation.
        
        Args:
            values: List of values for pie segments
            xpos: X position (longitude)
            ypos: Y position (latitude)
            size: Size of the pie chart
            colors: List of colors for each segment
            ax: Matplotlib axes to draw on
            show_percentages: Whether to show percentage labels on segments
        """
        # Normalize values for pie slices
        total = sum(values)
        if total == 0:
            return ax
        
        # Calculate cumulative proportions
        cumsum = np.cumsum(values)
        cumsum = cumsum / cumsum[-1]
        pie = [0] + cumsum.tolist()
        
        # Start angle offset to align all pies the same way (90 degrees = 12 o'clock)
        start_angle_offset = np.pi / 2  # 90 degrees in radians
        
        # Draw each pie segment
        for i, (r1, r2) in enumerate(zip(pie[:-1], pie[1:])):
            # Create angles for this segment, starting from 12 o'clock
            angles = np.linspace(
                2 * np.pi * r1 + start_angle_offset, 
                2 * np.pi * r2 + start_angle_offset, 
                50
            )
            
            # Create pie wedge coordinates
            x = [0] + np.cos(angles).tolist()
            y = [0] + np.sin(angles).tolist()
            
            # Create marker from coordinates
            xy = np.column_stack([x, y])
            
            # Use color from provided list or default
            color = colors[i] if i < len(colors) else self._get_default_pie_colors(1)[0]
            
            # Draw the pie segment with exact positioning
            ax.scatter([xpos], [ypos], marker=xy, s=size, color=color, alpha=0.85, 
                      edgecolors='white', linewidths=0.5, zorder=10)
            
            # Add percentage label if requested
            if show_percentages:
                # Calculate percentage
                percentage = (values[i] / total) * 100
                
                # Only show percentages for segments > 5% to avoid clutter
                if percentage >= 5:
                    # Calculate the middle angle of this segment for label positioning
                    mid_angle = (2 * np.pi * r1 + 2 * np.pi * r2) / 2 + start_angle_offset
                    
                    # Calculate label position (slightly inside the pie chart)
                    label_radius = 0.4  # Position at 60% of the radius
                    label_x = xpos + label_radius * (size / 1000) * np.cos(mid_angle)
                    label_y = ypos + label_radius * (size / 1000) * np.sin(mid_angle)
                    
                    # Add percentage text
                    ax.text(
                        label_x, label_y,
                        f"{percentage:.0f}%",
                        ha='center',
                        va='center',
                        fontsize=10,
                        fontweight='bold',
                        color='white',
                        zorder=15
                    )
        
        return ax
    
    def _create_fallback_map(self, ax):
        """Create a simple fallback map when geopandas is not available."""
        # Simple rectangular map bounds (approximate continental US)
        ax.set_xlim(-125, -66.5)
        ax.set_ylim(20, 50)
        ax.set_aspect('equal')
        ax.set_facecolor('lightblue')
        
        # Add a simple background representing land
        ax.add_patch(plt.Rectangle((-125, 20), 58.5, 30, 
                                 facecolor='lightgray', alpha=0.7, zorder=0))
    
    def _calculate_pie_sizes(self, pie_data, size_column, base_size, min_size, max_size):
        """Calculate pie chart sizes based on data column if specified."""
        if not size_column:
            return {location: base_size for location in pie_data.keys()}
        
        # Extract size values
        size_values = {}
        for location, data in pie_data.items():
            if size_column in data:
                size_values[location] = data[size_column]
            else:
                size_values[location] = base_size
        
        if not size_values:
            return {location: base_size for location in pie_data.keys()}
        
        # Normalize sizes
        min_val = min(size_values.values())
        max_val = max(size_values.values())
        
        if max_val == min_val:
            return {location: base_size for location in pie_data.keys()}
        
        # Scale sizes proportionally
        sizes = {}
        for location, value in size_values.items():
            normalized = (value - min_val) / (max_val - min_val)
            sizes[location] = min_size + normalized * (max_size - min_size)
        
        return sizes
    
    def _get_default_pie_colors(self, num_segments):
        """Get default colors for pie chart segments."""
        colors = [
            self.TPS_COLORS["Neptune Blue"],
            self.TPS_COLORS["Plasma Purple"], 
            self.TPS_COLORS["Rocket Flame"],
            self.TPS_COLORS["Medium Neptune"],
            self.TPS_COLORS["Medium Plasma"],
            self.TPS_COLORS["Crater Shadow"]
        ]
        return [colors[i % len(colors)] for i in range(num_segments)] 