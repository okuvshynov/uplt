# uplt Development Notes

## Project Overview
uplt is a Python package that allows users to execute SQL queries on CSV data from stdin and create terminal-based charts. It supports both raw SQL queries and built-in chart types like heatmaps.

## Key Components

### Core Modules
- `src/uplt/core.py`: Core CSV parsing and SQL execution functionality
- `src/uplt/query_builder.py`: SQL query construction for chart commands
- `src/uplt/charts.py`: Terminal chart rendering using Unicode characters
- `src/uplt/cli.py`: Command-line interface

### Testing
- Comprehensive test suite in `tests/` directory
- Run all tests: `python -m pytest`
- Run with coverage: `python -m pytest --cov=uplt`

### Key Commands to Run
Before committing changes, always run:
```bash
python -m pytest  # Run all tests
python -m pytest --cov=uplt  # Run tests with coverage
```

### CI/CD
GitHub Actions are configured to run automatically on:
- Pull requests to main branch
- Pushes to main branch

The CI pipeline includes:
1. **Linting** (ruff, black, isort) - currently set to continue on error
2. **Unit tests** - runs on multiple Python versions (3.8-3.12) and OS (Ubuntu, Windows, macOS)
3. **Integration tests** - tests the CLI commands with real data
4. **Code coverage** - uploads results to Codecov

Configuration files:
- `.github/workflows/ci.yml` - Main CI workflow
- `.github/dependabot.yml` - Automated dependency updates
- Linting config in `pyproject.toml`

## Usage Examples

### SQL Query Mode
```bash
cat data/test.csv | uplt query "SELECT * FROM data WHERE age > 30"

# Auto-detection will recognize headerless CSV files
echo -e "1,10,100\n2,20,200" | uplt query "SELECT * FROM data"

# Force header interpretation
cat data.csv | uplt --header query "SELECT * FROM data"

# Force no headers (columns named f1, f2, ..., fn)
cat data.csv | uplt --no-header query "SELECT f1, f2 FROM data WHERE f3 > 100"
```

### Chart Mode (Heatmap)
```bash
# Count occurrences
cat data/test.csv | uplt heatmap department age

# With aggregation
cat data/test.csv | uplt heatmap department age "avg(salary)"
cat data/test.csv | uplt heatmap department age "sum(salary)"
cat data/test.csv | uplt heatmap department age "min(salary)"
cat data/test.csv | uplt heatmap department age "max(salary)"
```

## Implementation Notes

### Heatmap Visualization
- Uses Unicode block characters: ░▒▓█
- Automatically normalizes values to character intensity
- Handles missing cells and non-numeric values gracefully
- **Automatic axis type detection:**
  - Numeric axes: Creates proper scales with binning (e.g., 0-10, 10-20, etc.)
  - Categorical axes: Shows distinct values as-is
  - Mixed mode: Can have one numeric and one categorical axis
- Sparse numeric data is properly binned into the grid
- All data points are correctly displayed, including edge values at scale boundaries
- **Enhanced legend**: Shows exact value ranges for each character (e.g., '░': [10, 20))
- **SQL-based aggregation**: Respects user's chosen aggregation function (sum, avg, min, max) without double aggregation

### SQL Query Builder
- Parses aggregation functions: avg(), sum(), min(), max(), count()
- Generates appropriate GROUP BY queries for charts
- Sanitizes field names but doesn't fully prevent SQL injection (future improvement)

### CSV Handling
- **Automatic Header Detection**: By default, uplt automatically detects whether the first row contains headers
  - Analyzes the first few rows to determine if the first row is likely headers
  - Compares numeric field counts between rows
  - If first row has no numeric fields but second row does → headers exist
  - If first row is ≥70% numeric → no headers
- **Manual Header Control**: Use flags to override auto-detection
  - `--header`: Force treating first row as headers
  - `--no-header`: Force treating first row as data
  - Columns without headers are automatically named f1, f2, ..., fn
- **Header Detection Implementation**: See `auto_detect_headers()` in `core.py`

## Future Enhancements
- Add more chart types (bar charts, line charts, scatter plots)
- Improve SQL injection prevention
- Add configuration file support
- Support for multiple input formats beyond CSV
- Interactive mode with real-time updates