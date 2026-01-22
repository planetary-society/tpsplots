"""Data processors for transforming raw data into chart-ready formats."""

from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig
from tpsplots.processors.budget_projection_processor import (
    BudgetProjectionConfig,
    BudgetProjectionProcessor,
)
from tpsplots.processors.calculated_column_processor import (
    CALCULATION_REGISTRY,
    CalculatedColumnConfig,
    CalculatedColumnProcessor,
    ColumnCalculation,
    register_calculation,
)
from tpsplots.processors.dataframe_to_yaml_processor import (
    DataFrameToYAMLConfig,
    DataFrameToYAMLProcessor,
)
from tpsplots.processors.inflation_adjustment_processor import (
    InflationAdjustmentConfig,
    InflationAdjustmentProcessor,
)

# Note: YAMLChartProcessor is not exported here to avoid RuntimeWarning when running
# as `python -m tpsplots.processors.yaml_chart_processor`. Import directly if needed:
#   from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

__all__ = [
    "CALCULATION_REGISTRY",
    "AwardDataProcessor",
    "BudgetProjectionConfig",
    "BudgetProjectionProcessor",
    "CalculatedColumnConfig",
    "CalculatedColumnProcessor",
    "ColumnCalculation",
    "DataFrameToYAMLConfig",
    "DataFrameToYAMLProcessor",
    "FiscalYearConfig",
    "InflationAdjustmentConfig",
    "InflationAdjustmentProcessor",
    "register_calculation",
]
