"""Improved US Map with pie charts visualization with expanded offset functionality."""
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
    
    # Centers that should be offset to avoid overlap - UPDATED to include JSC, ARC, and SSC
    OFFSET_CENTERS = {'GSFC', 'LaRC', 'HQ', 'Goddard Space Flight Center', 
                      'Langley Research Center', 'NASA Headquarters', 
                      'JSC', 'Johnson Space Center', 'ARC', 'Ames Research Center',
                      'SSC', 'Stennis Space Center'}
    
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
            - show_pie_labels: bool - Whether to show labels on pie charts (default: True)
            - show_percentages: bool or list(bool) - Whether to show percentage values on pie segments, or which ones to display
            - legend_location: str - Location for legend (default: 'lower left')
            - pie_edge_color: str - Edge color for pie charts (default: 'white')
            - pie_edge_width: float - Edge width for pie charts (default: 2)
            - offset_line_color: str - Color for connecting lines (default: 'gray')
            - offset_line_style: str - Style for connecting lines (default: '--')
            - offset_line_width: float - Width for connecting lines (default: 1.5)
            - auto_expand_bounds: bool - Automatically expand figure bounds to fit all pies (default: True)
            - padding_factor: float - Extra padding around pies as fraction of pie radius 
                                (default: 0.15 for desktop, 0.3 for mobile)
            
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
        show_pie_labels = kwargs.pop('show_pie_labels', True)
        show_percentages = kwargs.pop('show_percentages', False)
        legend_location = kwargs.pop('legend_location', 'lower left')
        pie_edge_color = kwargs.pop('pie_edge_color', 'white')
        pie_edge_width = kwargs.pop('pie_edge_width', 2)
        offset_line_color = kwargs.pop('offset_line_color', 'gray')
        offset_line_style = kwargs.pop('offset_line_style', '--')
        offset_line_width = kwargs.pop('offset_line_width', 1.5)
        auto_expand_bounds = kwargs.pop('auto_expand_bounds', True)
        padding_factor = kwargs.pop('padding_factor', 0  if style.get("type") == "desktop" else 0.15)
        
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
        
        # Apply desktop scaling factor to pie sizes
        if style.get("type") == "desktop":
            desktop_scale_factor = 2.0
            scaled_base_pie_size = base_pie_size * desktop_scale_factor
            scaled_min_pie_size = min_pie_size * desktop_scale_factor
            scaled_max_pie_size = max_pie_size * desktop_scale_factor
        else:
            scaled_base_pie_size = base_pie_size
            scaled_min_pie_size = min_pie_size
            scaled_max_pie_size = max_pie_size
        
        # Calculate pie sizes if using proportional sizing
        pie_sizes = self._calculate_pie_sizes(pie_data, pie_size_column, 
                                            scaled_base_pie_size, scaled_min_pie_size, scaled_max_pie_size)
        
        # Set initial map bounds
        base_xlim = (-122, -65)
        base_ylim = (22, 48)
        ax.set_xlim(base_xlim)
        ax.set_ylim(base_ylim)
        
        # Calculate offset positions for the centers that need to be displaced
        offset_positions = self._calculate_offset_positions(pie_data, all_locations, ax, pie_sizes, scaled_base_pie_size)
        
        # Calculate actual pie positions and sizes for bounds checking
        pie_positions_and_sizes = []
        for location_name, data in pie_data.items():
            if location_name not in all_locations:
                continue
                
            location_info = all_locations[location_name]
            original_lat, original_lon = location_info['lat'], location_info['lon']
            
            # Determine final position
            if location_name in self.OFFSET_CENTERS and location_name in offset_positions:
                lon, lat = offset_positions[location_name]
            else:
                lat, lon = original_lat, original_lon
            
            pie_size = pie_sizes.get(location_name, scaled_base_pie_size)
            pie_positions_and_sizes.append((lon, lat, pie_size))
        
        # Auto-expand bounds if requested
        if auto_expand_bounds:
            self._expand_bounds_for_pies(ax, pie_positions_and_sizes, padding_factor)
        
        # Use appropriate aspect ratio for continental US (not equal)
        ax.set_aspect(1.3)  # Adjust this value to get the right map proportions
        
        # Create pie charts at each location using scatter-based approach
        legend_elements = []
        legend_labels = set()
        
        for location_name, data in pie_data.items():
            if location_name not in all_locations:
                logger.warning(f"Location '{location_name}' not found in location database")
                continue
            
            location_info = all_locations[location_name]
            original_lat, original_lon = location_info['lat'], location_info['lon']
            
            # Check if this location should be offset
            if location_name in self.OFFSET_CENTERS and location_name in offset_positions:
                # Use offset position
                lon, lat = offset_positions[location_name]
                
                # Draw connecting line from original position to offset position
                ax.plot([original_lon, lon], [original_lat, lat], 
                       color=offset_line_color, 
                       linestyle=offset_line_style, 
                       linewidth=offset_line_width,
                       alpha=0.7,
                       zorder=5)
                
                # Add a small marker at the original location
                ax.scatter(original_lon, original_lat, 
                          s=30, 
                          color=offset_line_color, 
                          alpha=0.7, 
                          zorder=6)
            else:
                # Use original position
                lat, lon = original_lat, original_lon
            
            # Get pie chart data
            values = data.get('values', [])
            labels = data.get('labels', [])
            colors = data.get('colors', self._get_default_pie_colors(len(values)))
            
            if not values:
                continue
            
            # Get pie size
            pie_size = pie_sizes.get(location_name, base_pie_size)
            
            # Draw pie chart using improved scatter-based method
            self._draw_pie_improved(values, lon, lat, pie_size, colors, ax, show_percentages, figsize, dpi, style)
            
            # Add center name label if requested
            if show_pie_labels:
                # Place label at the center of the pie chart
                ax.text(lon, lat, location_name, 
                       ha='center', va='center', 
                       fontsize=9, fontweight='bold',
                       color='black',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.9, edgecolor='none'),
                       zorder=20)  # Ensure label appears on top
            
            # Collect legend information (avoid duplicates)
            for label, color in zip(labels, colors):
                if label not in legend_labels:
                    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, edgecolor='white'))
                    legend_labels.add(label)
        
        # Add legend
        if legend_elements:
            # Reverse the order to match the visual (Cut first, then Retained)
            legend_labels_list = list(legend_labels)
            legend_labels_list.reverse()
            
            ax.legend(legend_elements, legend_labels_list, 
                     loc='lower left', 
                     fontsize=style.get("legend_size", 12),
                     frameon=True, fancybox=True)
        
        # Remove axes for cleaner look
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Apply layout adjustments
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _expand_bounds_for_pies(self, ax, pie_positions_and_sizes, padding_factor):
        """
        Expand the axis bounds to ensure all pie charts fit within the figure.
        
        Args:
            ax: Matplotlib axes
            pie_positions_and_sizes: List of tuples (lon, lat, pie_size)
            padding_factor: Extra padding as fraction of pie radius
        """
        current_xlim = ax.get_xlim()
        current_ylim = ax.get_ylim()
        
        min_x, max_x = current_xlim
        min_y, max_y = current_ylim
        
        # Track whether we actually need to expand bounds
        bounds_changed = False
        
        # Calculate the maximum radius in data coordinates
        for lon, lat, pie_size in pie_positions_and_sizes:
            # Estimate pie radius in data coordinates using the same method as the drawing function
            estimated_radius = self._calculate_consistent_pie_radius(pie_size, figsize=None, dpi=None, style=None)
            padding = estimated_radius * padding_factor
            
            # Check if pie extends beyond current bounds
            pie_min_x = lon - estimated_radius - padding
            pie_max_x = lon + estimated_radius + padding
            pie_min_y = lat - estimated_radius - padding
            pie_max_y = lat + estimated_radius + padding
            
            # Only expand bounds if necessary (pies extend beyond current bounds)
            if pie_min_x < min_x:
                min_x = pie_min_x
                bounds_changed = True
            if pie_max_x > max_x:
                max_x = pie_max_x
                bounds_changed = True
            if pie_min_y < min_y:
                min_y = pie_min_y
                bounds_changed = True
            if pie_max_y > max_y:
                max_y = pie_max_y
                bounds_changed = True
        
        # Only set bounds if they actually changed to avoid unnecessary padding
        if bounds_changed:
            # Add a small additional margin only if we expanded bounds
            margin_x = (max_x - min_x) * 0.01  # 2% margin
            margin_y = (max_y - min_y) * 0.01  # 2% margin
            
            ax.set_xlim(min_x - margin_x, max_x + margin_x)
            ax.set_ylim(min_y - margin_y, max_y + margin_y)
    
    def _calculate_position_independent_radius(self, scatter_size):
        """
        Calculate pie radius in data coordinates independent of chart position.
        
        This method provides consistent radius calculation regardless of where
        the pie chart is positioned (original location vs offset location).
        
        Args:
            scatter_size: The scatter plot size parameter
            
        Returns:
            float: Pie radius in data coordinates
        """
        # Convert scatter size to radius using a fixed conversion factor
        # This approach is independent of current axis limits or figure dimensions
        
        # scatter size is in points^2, so we take sqrt to get radius in points
        radius_points = np.sqrt(scatter_size)
        
        # Use a fixed conversion factor from points to data coordinates
        # This factor is calibrated for the typical US map coordinate system
        # (longitude range ~65 degrees, latitude range ~30 degrees)
        points_to_data_conversion = 0.02  # Adjust this value if needed
        
        radius_data = radius_points * points_to_data_conversion
        
        return radius_data

    def _draw_pie_improved(self, values, xpos, ypos, size, colors, ax, show_percentages=False, figsize=None, dpi=None, style=None):
        """
        Draw a pie chart using scatter plots with improved percentage positioning.
        
        Args:
            values: List of values for pie segments
            xpos: X position (longitude)
            ypos: Y position (latitude)
            size: Size of the pie chart
            colors: List of colors for each segment
            ax: Matplotlib axes to draw on
            show_percentages: Either bool (True/False for all segments) or list of bools 
                            (per-segment control, matching order of values)
            figsize: Figure size tuple for consistent radius calculation
            dpi: Figure DPI for consistent radius calculation
            style: Style dictionary to determine if desktop or mobile
        """
        # Normalize values for pie slices
        total = sum(values)
        if total == 0:
            return ax
        
        # Process show_percentages parameter
        if isinstance(show_percentages, bool):
            # Convert boolean to list for all segments
            show_percentages_list = [show_percentages] * len(values)
        elif isinstance(show_percentages, (list, tuple)):
            # Use provided list, padding with False if too short
            show_percentages_list = list(show_percentages)
            # Pad with False if the list is shorter than values
            while len(show_percentages_list) < len(values):
                show_percentages_list.append(False)
            # Truncate if the list is longer than values
            show_percentages_list = show_percentages_list[:len(values)]
        else:
            # Fallback for invalid input
            show_percentages_list = [False] * len(values)
        
        # Calculate cumulative proportions
        cumsum = np.cumsum(values)
        cumsum = cumsum / cumsum[-1]
        pie = [0] + cumsum.tolist()
        
        # Start angle offset to align all pies the same way (90 degrees = 12 o'clock)
        start_angle_offset = np.pi / 2  # 90 degrees in radians
        
        # Calculate consistent pie radius in data coordinates
        # Use a simpler, position-independent approach
        pie_radius_data = self._calculate_position_independent_radius(size)
        
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
            
            # Add percentage label if requested for this specific segment
            if show_percentages_list[i]:
                # Calculate percentage
                percentage = (values[i] / total) * 100
                
                # Show percentages for segments >= 1%
                if percentage >= 1:
                    # Calculate the middle angle of this segment for label positioning
                    mid_angle = (2 * np.pi * r1 + 2 * np.pi * r2) / 2 + start_angle_offset
                    
                    # Adjust label radius based on segment size for better visual balance
                    # Smaller segments get labels closer to center, larger segments farther out
                    if percentage < 35:
                        label_radius_factor = 2  # Closer to center for small segments
                    elif percentage < 50:
                        label_radius_factor = 3  # Medium distance for medium segments
                    else:
                        label_radius_factor = 3.5  # Farther out for large segments
                    
                    label_radius = pie_radius_data * label_radius_factor
                    
                    # Adjust for mobile display quirks
                    if style and style.get("type") == "mobile":
                        label_radius = label_radius * 1.3
                    
                    # Account for map aspect ratio to prevent horizontal shifting
                    # The map uses aspect ratio 1.3, so longitude coordinates are compressed
                    aspect_ratio = 1.3  # This should match the aspect ratio set in _create_chart
                    
                    # Calculate label position with aspect ratio correction
                    label_x = xpos + (label_radius * np.cos(mid_angle)) / aspect_ratio
                    label_y = (ypos + label_radius * np.sin(mid_angle)) * 0.98
                    
                    # Adjust font size based on style type for better readability
                    if style and style.get("type") == "desktop":
                        base_fontsize = 12 if percentage < 10 else 14
                    else:
                        base_fontsize = 9 if percentage < 10 else 10
                    
                    # Add percentage text
                    ax.text(
                        label_x, label_y,
                        f"{percentage:.0f}%",
                        ha='center',
                        va='center',
                        fontsize=base_fontsize,
                        fontweight='bold',
                        color=color,
                        bbox=dict(boxstyle="round,pad=0.2", facecolor='white', edgecolor=color),
                        zorder=15
                    )
        
        return ax
    
    def _calculate_consistent_pie_radius(self, scatter_size, figsize=None, dpi=None, style=None):
        """
        Calculate a consistent pie radius in data coordinates that works across different figure sizes and DPI.
        
        Args:
            scatter_size: The scatter plot size parameter (already scaled for desktop/mobile)
            figsize: Figure size tuple (width, height)
            dpi: Figure DPI
            style: Style dictionary to determine scaling factors
            
        Returns:
            float: Pie radius in data coordinates
        """
        # Base formula for converting scatter size to approximate radius
        # scatter size is in points^2, so we take sqrt to get radius in points
        radius_points = np.sqrt(scatter_size)
        
        # Convert points to data coordinates
        # 1 point = 1/72 inch
        radius_inches = radius_points / 72
        
        # Get current axis limits
        try:
            xlim = plt.gca().get_xlim()
            ylim = plt.gca().get_ylim()
        except:
            # Fallback to default map bounds
            xlim = (-122, -66)
            ylim = (22, 48)
        
        # Calculate data units per inch based on current axis and figure
        if figsize is not None:
            data_width = xlim[1] - xlim[0]
            data_height = ylim[1] - ylim[0]
            
            # Use the smaller dimension to be conservative
            data_units_per_inch = min(data_width / figsize[0], data_height / figsize[1])
        else:
            # Use a reasonable default conversion factor
            data_units_per_inch = 8
        
        # Convert radius from inches to data coordinates
        radius_data = radius_inches * data_units_per_inch
        
        # Apply a normalization factor to ensure consistent visual positioning
        # This accounts for the fact that matplotlib's scatter sizing may not be perfectly linear
        normalization_factor = 0.8  # Adjust this if needed based on visual testing
        
        return radius_data * normalization_factor
    
    def _calculate_offset_positions(self, pie_data, all_locations, ax, pie_sizes, base_pie_size):
        """
        Calculate offset positions for centers that need to be displaced.
        
        This method handles different offset strategies:
        - East Coast centers (HQ, GSFC, LaRC) are vertically aligned on the right side
        - JSC is moved northwest by one pie diameter  
        - ARC is moved north by one pie diameter
        - SSC is moved south by half a pie diameter
        
        Args:
            pie_data: Dictionary of pie chart data
            all_locations: Dictionary of all location coordinates
            ax: Matplotlib axes
            pie_sizes: Dictionary of pie sizes for each location
            base_pie_size: Base pie size for radius calculations
            
        Returns:
            Dictionary of offset positions {location_name: (lon, lat)}
        """
        offset_positions = {}
        
        # Define east coast centers that get vertical alignment
        east_coast_centers = {'GSFC', 'LaRC', 'HQ', 'Goddard Space Flight Center', 
                             'Langley Research Center', 'NASA Headquarters'}
        
        # Handle east coast centers first (existing logic)
        centers_to_offset_east = []
        for name in pie_data.keys():
            if name in east_coast_centers and name in all_locations:
                centers_to_offset_east.append(name)
        
        if centers_to_offset_east:
            # Sort centers by their original latitude (north to south)
            centers_to_offset_east.sort(key=lambda x: all_locations[x]['lat'], reverse=True)
            
            # Calculate offset positions for east coast centers
            # Place them to the right of the map, outside the main map area
            offset_lon = -64  # Further right, outside the map bounds
            
            # Calculate vertical spacing based on number of centers
            if len(centers_to_offset_east) == 1:
                positions = [35]  # Center vertically
            elif len(centers_to_offset_east) == 2:
                positions = [40, 28]  # More spread out vertically
            elif len(centers_to_offset_east) == 3:
                positions = [43, 35, 27]  # Specific positions for 3 centers
            else:  # 4 or more
                # Evenly space them with more room
                top_lat = 44
                bottom_lat = 26
                spacing = (top_lat - bottom_lat) / (len(centers_to_offset_east) - 1)
                positions = [top_lat - i * spacing for i in range(len(centers_to_offset_east))]
            
            # Assign positions to east coast centers
            for center_name, lat in zip(centers_to_offset_east, positions):
                offset_positions[center_name] = (offset_lon, lat)
        
        # Handle JSC offset (northwest by one pie diameter)
        jsc_names = {'JSC', 'Johnson Space Center'}
        for jsc_name in jsc_names:
            if jsc_name in pie_data and jsc_name in all_locations:
                original_location = all_locations[jsc_name]
                original_lat, original_lon = original_location['lat'], original_location['lon']
                
                # Calculate pie radius in data coordinates
                pie_size = pie_sizes.get(jsc_name, base_pie_size)
                pie_radius_data = self._calculate_consistent_pie_radius(pie_size)
                
                # Move northwest by one pie diameter (2 * radius)
                offset_distance = 1 * pie_radius_data
                
                # Northwest direction: negative longitude (west), positive latitude (north)
                # Using 45-degree angle for northwest
                angle_nw = np.pi * 3/4  # 135 degrees in radians (northwest)
                
                offset_lon = original_lon + offset_distance * np.cos(angle_nw)
                offset_lat = original_lat + offset_distance * np.sin(angle_nw)
                
                offset_positions[jsc_name] = (offset_lon, offset_lat)
                break  # Only process the first match
        
        # Handle ARC offset (north by one pie diameter)
        arc_names = {'ARC', 'Ames Research Center'}
        for arc_name in arc_names:
            if arc_name in pie_data and arc_name in all_locations:
                original_location = all_locations[arc_name]
                original_lat, original_lon = original_location['lat'], original_location['lon']
                
                # Calculate pie radius in data coordinates
                pie_size = pie_sizes.get(arc_name, base_pie_size)
                pie_radius_data = self._calculate_consistent_pie_radius(pie_size)
                
                # Move north by one pie diameter (2 * radius)
                offset_distance = 1 * pie_radius_data
                
                # North direction: same longitude, positive latitude
                offset_lon = original_lon
                offset_lat = original_lat + offset_distance
                
                offset_positions[arc_name] = (offset_lon, offset_lat)
                break  # Only process the first match
        
        # Handle SSC offset (south by half a pie diameter)
        ssc_names = {'SSC', 'Stennis Space Center'}
        for ssc_name in ssc_names:
            if ssc_name in pie_data and ssc_name in all_locations:
                original_location = all_locations[ssc_name]
                original_lat, original_lon = original_location['lat'], original_location['lon']
                
                # Calculate pie radius in data coordinates
                pie_size = pie_sizes.get(ssc_name, base_pie_size)
                pie_radius_data = self._calculate_consistent_pie_radius(pie_size)
                
                # Move south by half a pie diameter (1 * radius)
                offset_distance = pie_radius_data  # This is half the diameter
                
                # Southwestern direction
                angle_nw = np.pi * 1.33
                
                offset_lon = original_lon + offset_distance * np.cos(angle_nw)
                offset_lat = original_lat + offset_distance * np.sin(angle_nw)
                
                offset_positions[ssc_name] = (offset_lon, offset_lat)
                break  # Only process the first match
        
        return offset_positions
    
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