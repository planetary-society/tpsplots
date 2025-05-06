"""Concrete NASA budget charts."""
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FormatStrFormatter
from base import BaseChart
from data_sources.nasa_budget_data_source import Historical  # existing module

class NASABudgetChart(BaseChart):
    """NASA PBR trends, etc."""

    def __init__(self):
        super().__init__(Historical(), outdir=Path("charts") / "nasa_budget")

    def pbrs(self) -> None:
        """
        NASA Presidential Budget Requests by fiscal year.
        Saves SVG + PNG in 16×9 and 1×1 aspect ratios via BaseChart._export().
        """

        # ---------- data prep --------------------------------------------------
        df = (
            self.data_source.data()          # fetch dataframe
              .astype({"PBR": "float"})      # cast from nullable Float64 → float64
              .dropna(subset=["PBR"])        # remove rows where PBR is <NA>
        )

        # ---------- build figure ----------------------------------------------
        fig, ax = plt.subplots(figsize=(12, 6))

        sns.lineplot(
            data=df,
            x="Fiscal Year",
            y="PBR",
            marker="o",
            ax=ax
        )

        # ---------- styling tweaks --------------------------------------------
        ax.set_title("NASA PBR by Fiscal Year", fontweight="bold")
        ax.set_xlabel("Fiscal Year")
        ax.set_ylabel("PBR (Billions USD)")
        ax.yaxis.set_major_formatter(FormatStrFormatter("$%1.2fB"))

        if len(df) > 15:
            ax.xaxis.set_major_locator(plt.MaxNLocator(15))

        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        # ---------- save -------------------------------------------------------
        self._export(fig, "nasa_pbr_by_year")


if __name__ == "__main__":
    NASABudgetChart().pbrs()
    print("All done.")