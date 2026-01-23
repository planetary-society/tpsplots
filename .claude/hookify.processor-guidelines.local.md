---
name: processor-guidelines
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: tpsplots/processors/.*\.py$
---

## Processor Guidelines Reminder

You are creating or modifying a processor. Review **PROCESSORS.md** before proceeding.

### Core Principles

1. **Single Responsibility** - One transformation per processor
2. **No Presentation Logic** - No colors, scaling, or formatting (that's the view's job)
3. **Always Return DataFrame** - Enables pipeline chaining
4. **Don't Mutate Input** - Always `df = df.copy()` first

### Checklist

- [ ] Does exactly one transformation
- [ ] No colors, fonts, or visual formatting
- [ ] No value scaling (e.g., dividing by 1e9)
- [ ] Returns DataFrame (not dict)
- [ ] Uses `@dataclass` for configuration
- [ ] Copies input DataFrame
- [ ] Has docstrings
- [ ] Will have unit tests

### Quick Reference

```python
@dataclass
class MyProcessorConfig:
    param: str

class MyProcessor:
    def __init__(self, config: MyProcessorConfig):
        self.config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # transformation only
        return df
```

See `PROCESSORS.md` for full documentation.
