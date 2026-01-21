"""Data processors for transforming raw data into chart-ready formats."""

from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig

# Note: YAMLChartProcessor is not exported here to avoid RuntimeWarning when running
# as `python -m tpsplots.processors.yaml_chart_processor`. Import directly if needed:
#   from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

__all__ = ["AwardDataProcessor", "FiscalYearConfig"]
