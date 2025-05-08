from chart_view import ChartView
from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker # Import the ticker module

class SubplotView(ChartView):
    """
    Subclass of ChartView for generating subplots.
    
    This class is designed to create subplots with multiple axes and shared
    properties. It extends the functionality of ChartView to support
    subplot generation.
    """
    
    def __init__(self, outdir: Path = Path("charts")):
        """
        Initialize a subplot view.
        
        Args:
            outdir: Output directory for chart files
        """
        super().__init__()
    
    def quadrants(self):
        #plt.show()
        with plt.style.context(self.TPS_STYLE):
            fig = plt.gcf()
            all_axes = fig.get_axes()

            # --- Now, iterate through the list of axes and apply customization ---
            # Let's set a max of 4 ticks on the y-axis for *each* subplot
            max_x_ticks = 5
            x_locator = ticker.MaxNLocator(max_x_ticks)
            # Define the desired spacing in data units (e.g., 1 billion)
            y_spacing = 1e9

            # Create a MultipleLocator instance with the desired spacing
            y_locator = ticker.MultipleLocator(base=y_spacing)
            titles = ["Planetary Science", "Astrophysics", "Earth Science", "Heliophysics"]
            
            for i, ax in enumerate(all_axes):
                # Apply the locator to the y-axis of the current axes object in the loop
                print(f"Processing Axes {i+1}...")
                ax.xaxis.set_major_locator(x_locator)
                self._apply_scale_formatter(ax, scale="billions",axis="y", decimals="0")
                ax.yaxis.set_major_locator(y_locator)
                ax.set_ylim(bottom=0, top=4e9)
                ax.set_title(titles[i])
                
            
            fig.set_size_inches(ChartView.DESKTOP["figsize"])
            fig.savefig(f"{self.outdir}/quadtest_desktop.png", dpi=self.DESKTOP["dpi"])
            
            fig.set_size_inches(ChartView.MOBILE["figsize"])
            fig.savefig(f"{self.outdir}/quadtest_mobile.png", dpi=self.DESKTOP["dpi"])
            
            # self._save_chart(fig,"science_divisions_quadrants")