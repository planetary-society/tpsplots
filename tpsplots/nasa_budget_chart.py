"""Concrete NASA budget charts."""
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from base import BaseChart, apply_chart_styles
from styles import TPS_COLORS
from data_sources.nasa_budget_data_source import Historical  # existing module

class NASABudgetChart(BaseChart):
    """NASA PBR trends, etc."""

    def __init__(self):
        super().__init__(Historical(), outdir=Path("charts") / "nasa_budget")

    @apply_chart_styles(stem="nasa_pbr_by_year")
    def nasa_historical_inflation_adjusted(self) -> None:
        """
        NASA Presidential Budget Requests by fiscal year.
        Saves SVG + PNG in 16x9 and 1x1 aspect ratios via BaseChart._export().
        """

        # ---------- data prep --------------------------------------------------
        df = (
            self.data_source.data()          # fetch dataframe
              .dropna(subset=["PBR"])        # remove rows where PBR is <NA>
        )

        # ---------- build figure ----------------------------------------------
        fig, ax = plt.subplots()

        ax.plot(
            df["Fiscal Year"], 
            df["PBR_adjusted_nnsi"], 
            color=TPS_COLORS["light_blue"],
            linestyle="--",
            label="Presidential Budget Request"
        )
        
        ax.plot(
            df["Fiscal Year"], 
            df["Appropriation_adjusted_nnsi"], 
            color=TPS_COLORS["blue"], 
            label="Congressional Appropriation"
        )
        ax.legend(title="Legend")

        # ---------- styling tweaks --------------------------------------------
        ax.set_title("NASA PBR by Fiscal Year", fontweight="bold")
    
        ax.set_xlim(df["Fiscal Year"].min(), df["Fiscal Year"].max())
        self.apply_scale_formatter(ax=ax, scale="billions", decimals=0)

        if len(df) > 20:
            ax.xaxis.set_major_locator(plt.MaxNLocator(20))

        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        # ---------- save -------------------------------------------------------
        return fig


if __name__ == "__main__":
    NASABudgetChart().nasa_historical_inflation_adjusted()
    print("All done.")