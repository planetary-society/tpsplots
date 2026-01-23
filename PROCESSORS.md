# Creating Processors

Processors live in `tpsplots/processors/` and handle data transformation. They follow a strict pattern to maintain separation of concerns.

## Core Principles

### 1. Single Responsibility

Each processor does exactly ONE thing:
- `AccountsFilterProcessor` - filters rows to specified accounts
- `InflationAdjustmentProcessor` - applies inflation adjustment
- `GroupedBarTransformProcessor` - reshapes data for grouped bars

**Don't** combine filtering + calculation + formatting in one processor.

### 2. No Presentation Logic

Processors handle DATA, not DISPLAY:
- **Don't** include colors, fonts, labels, or formatting
- **Don't** scale values (e.g., divide by 1e9 for billions)
- **Don't** resolve color names to hex codes
- **Do** let the view handle all presentation concerns

### 3. Always Return DataFrame

Enables pipeline chaining:
```python
df = FilterProcessor(config).process(df)
df = CalculationProcessor(config).process(df)
result = DataFrameToYAMLProcessor().process(df)
```

### 4. Use DataFrame.attrs for Metadata

Store computed metadata that downstream processors or views need:
```python
df.attrs["categories"] = categories_list
df.attrs["fiscal_year"] = 2026
```

## Processor Structure

```python
"""One-line description of what this processor does.

Longer explanation of the transformation, inputs, and outputs.
"""

from dataclasses import dataclass, field
import pandas as pd


@dataclass
class MyProcessorConfig:
    """Configuration for MyProcessor.

    Attributes:
        param1: Description of param1
        param2: Description of param2
    """
    param1: str
    param2: list[str] = field(default_factory=list)


class MyProcessor:
    """Transforms X into Y.

    Returns a DataFrame (not dict) to enable pipeline chaining.
    """

    def __init__(self, config: MyProcessorConfig):
        self.config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the transformation.

        Args:
            df: Input DataFrame

        Returns:
            Transformed DataFrame
        """
        df = df.copy()  # Don't mutate input
        # ... transformation logic ...
        return df
```

## Unit Tests Required

Every processor must have unit tests in `tests/test_processors.py`:

```python
def test_my_processor_basic():
    """Test basic transformation."""
    df = pd.DataFrame({"col": [1, 2, 3]})
    config = MyProcessorConfig(param1="value")
    result = MyProcessor(config).process(df)
    assert "expected_col" in result.columns

def test_my_processor_edge_cases():
    """Test empty input, missing columns, etc."""
    ...
```

## Checklist for New Processors

- [ ] Single responsibility - does exactly one transformation
- [ ] No presentation logic (colors, scaling, formatting)
- [ ] Returns DataFrame (not dict)
- [ ] Uses `@dataclass` for configuration
- [ ] Copies input DataFrame (`df = df.copy()`)
- [ ] Has docstrings for class, config, and process method
- [ ] Exported in `tpsplots/processors/__init__.py`
- [ ] Has unit tests covering normal and edge cases
- [ ] Validates required columns exist with helpful error messages

## Examples

See existing processors for reference:
- `calculated_column_processor.py` - Adding computed columns
- `accounts_filter_processor.py` - Row filtering with renaming
- `grouped_bar_transform_processor.py` - Reshaping for chart type
- `inflation_adjustment_processor.py` - Applying transformations to columns
