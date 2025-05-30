# uplt Development Notes

## Project Overview
uplt is a Python package that allows users to execute SQL queries on CSV data from stdin and create terminal-based charts. It supports both raw SQL queries and built-in chart types like heatmaps, comparisons, and multi-comparisons.

## Key Components

### Core Modules
- `src/uplt/core.py`: Core CSV parsing and SQL execution functionality
- `src/uplt/query_builder.py`: SQL query construction for chart commands
- `src/uplt/charts.py`: Terminal chart rendering using Unicode characters
- `src/uplt/cli.py`: Command-line interface
- `src/uplt/charts/`: Chart implementations
  - `heatmap.py`: Heatmap visualization with automatic axis detection
  - `multi_comparison.py`: Unified comparison charts (supports 2+ versions) with baseline selection
  - `display_mode.py`: Display mode configuration for comparison charts
  - `utils.py`: Shared utilities for chart rendering

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
# Short form
cat data/test.csv | uplt q "SELECT * FROM data WHERE age > 30"

# Auto-detection will recognize headerless CSV files
echo -e "1,10,100\n2,20,200" | uplt query "SELECT * FROM data"

# Force header interpretation
cat data.csv | uplt --header query "SELECT * FROM data"

# Force no headers (columns named f1, f2, ..., fn)
cat data.csv | uplt --no-header query "SELECT f1, f2 FROM data WHERE f3 > 100"

# Verbose mode shows the generated SQL
cat data.csv | uplt -v query "SELECT * FROM data"
```

### SQLite Functions in Field Arguments
```bash
# All chart commands support SQLite functions in field arguments
# This allows dynamic data transformation and grouping

# Extract substring from model names
cat data/qwen30b3a_q2.csv | uplt mcmp "substr(model_filename, -15)" n_depth avg_ts -m compact

# Normalize case for consistent grouping
cat data.csv | uplt heatmap "UPPER(category)" "substr(date, 1, 7)" "sum(revenue)"

# Group by string length
cat data.csv | uplt comparison version "LENGTH(name)" "avg(score)"

# Use arithmetic expressions
cat data.csv | uplt heatmap category "price * quantity" "count(*)"

# Complex CASE expressions
cat data.csv | uplt cmp model "CASE WHEN latency < 100 THEN 'fast' ELSE 'slow' END" "avg(throughput)"

# Nested functions
cat data.csv | uplt hm "UPPER(substr(product_code, 1, 3))" month "sum(sales)"
```

### Add Column Mode
```bash
# Add calculated columns
cat data.csv | uplt add "price * quantity as total"
# Short form
cat data.csv | uplt a "price * 0.1 as tax"

# Conditional columns
cat data.csv | uplt add "case when price > 100 then 'expensive' else 'cheap' end as category"
cat data.csv | uplt add "if(status = 'active', 1, 0) as is_active"

# Using SQLite functions
cat data.csv | uplt add "lower(name) as name_lower"
cat data.csv | uplt add "substr(date, 1, 7) as month"
cat data.csv | uplt add "round(price, 2) as price_rounded"

# Chaining with other commands
cat latency.csv | uplt add "if(n_items > 1000, 1, 0) as large_query" | uplt cmp version large_query latency_ms

# Complex pipelines
cat sales.csv | \
  uplt add "quantity * unit_price as total" | \
  uplt add "total * 0.08 as tax" | \
  uplt add "total + tax as grand_total" | \
  uplt query "SELECT category, SUM(grand_total) FROM data GROUP BY category"
```

### Filter Mode
```bash
# Filter rows based on conditions
cat data.csv | uplt filter "price > 100"
# Short form
cat data.csv | uplt f "status = 'active'"

# Complex conditions
cat data.csv | uplt filter "price > 100 AND quantity < 50"
cat data.csv | uplt filter "category IN ('electronics', 'computers')"
cat data.csv | uplt filter "name LIKE '%laptop%'"

# Using SQLite functions in conditions
cat data.csv | uplt filter "UPPER(category) = 'ELECTRONICS'"
cat data.csv | uplt filter "LENGTH(name) > 10"
cat data.csv | uplt filter "substr(date, 1, 4) = '2024'"

# Filter with headerless data
echo -e "laptop,1000,5\nmouse,50,100" | uplt filter "f2 > 100"

# Chaining with other commands
cat products.csv | \
  uplt filter "price > 50" | \
  uplt add "price * 0.1 as discount" | \
  uplt filter "discount > 10" | \
  uplt query "SELECT * FROM data ORDER BY discount DESC"

# Common use cases
cat logs.csv | uplt filter "status = 'ERROR'"  # Get error logs
cat sales.csv | uplt filter "date >= '2024-01-01'"  # Recent sales
cat inventory.csv | uplt filter "quantity = 0"  # Out of stock items
```

### Group By Mode
```bash
# Full syntax with specific aggregations
cat data.csv | uplt groupby "category,region" "sum(sales),avg(price),count(*)"
# Short form
cat data.csv | uplt g category "sum(revenue)"

# Group by multiple fields
cat data.csv | uplt groupby "store,month" "sum(sales),avg(customers)"

# Aggregate-all shortcuts (apply same function to all numeric columns)
cat data.csv | uplt groupby category sum    # Sum all numeric columns
cat data.csv | uplt groupby category avg    # Average all numeric columns
cat data.csv | uplt groupby category min    # Min of all numeric columns
cat data.csv | uplt groupby category max    # Max of all numeric columns
cat data.csv | uplt groupby category count  # Count all numeric columns

# Default behavior (no aggregation specified = avg)
cat data.csv | uplt groupby category        # Same as: uplt g category avg

# Complex grouping with SQLite functions
cat logs.csv | uplt groupby "substr(timestamp,1,10),status" "count(*)"
cat sales.csv | uplt groupby "UPPER(region)" "sum(amount)"

# Groupby pipelines
cat orders.csv | \
  uplt filter "year = 2024" | \
  uplt groupby "customer_id,quarter" "sum(total),count(*) as orders" | \
  uplt filter "orders > 10"

# Verbose mode shows SQL and numeric columns detected
cat data.csv | uplt -v groupby category sum
```

### Chart Mode (Heatmap)
```bash
# Count occurrences
cat data/test.csv | uplt heatmap department age
# Short form
cat data/test.csv | uplt hm department age

# With aggregation
cat data/test.csv | uplt heatmap department age "avg(salary)"
cat data/test.csv | uplt heatmap department age "sum(salary)"
cat data/test.csv | uplt heatmap department age "min(salary)"
cat data/test.csv | uplt heatmap department age "max(salary)"

# Verbose mode shows generated SQL and data points
cat data/test.csv | uplt -v heatmap department age "sum(salary)"
```

### Chart Mode (Comparison)
```bash
# Basic comparison between two versions
cat data/comparison_test.csv | uplt comparison model_id input_size score
# Short form
cat data/comparison_test.csv | uplt cmp model_id input_size score

# With aggregation
cat data/comparison_test.csv | uplt cmp model_id input_size "avg(latency)"
cat data/comparison_test.csv | uplt cmp model_id input_size "sum(value)"
cat data/comparison_test.csv | uplt cmp model_id input_size "min(value)"
cat data/comparison_test.csv | uplt cmp model_id input_size "max(value)"

# Without value field (counts occurrences)
cat data/comparison_test.csv | uplt cmp model_id input_size

# Display modes (default: value-percent)
cat data.csv | uplt cmp models metrics value --display-mode=value     # Values only
cat data.csv | uplt cmp models metrics value --display-mode=diff      # Differences only
cat data.csv | uplt cmp models metrics value --display-mode=percent   # Percentages only
cat data.csv | uplt cmp models metrics value -m compact               # Same as percent
cat data.csv | uplt cmp models metrics value -m value-diff            # Value with diff
cat data.csv | uplt cmp models metrics value -m full                  # Everything

# Verbose mode shows generated SQL and data points
cat data/comparison_test.csv | uplt -v cmp model_id input_size score
```

### Chart Mode (Multi-Comparison)
```bash
# Compare multiple versions against a baseline
cat data/multi_group_test.csv | uplt multi-comparison model test_case latency
# Short form
cat data/multi_group_test.csv | uplt mcmp model test_case latency

# With aggregation
cat data/multi_group_test.csv | uplt mcmp model test_case "avg(latency)"

# Specify custom baseline (default: first version alphabetically)
cat data/multi_group_test.csv | uplt mcmp model test_case latency --baseline ModelB
cat data/multi_group_test.csv | uplt mcmp model test_case latency -b ModelC

# Display modes work the same as comparison
cat data.csv | uplt mcmp models metrics value -m percent

# Verbose mode shows baseline selection
cat data.csv | uplt -v mcmp models metrics value
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
- **Zero-based scale for non-negative data**: When all values are ≥ 0, the scale starts at 0 to properly distinguish between no data (space) and small positive values
- **Verbose mode support**: Use `-v` or `--verbose` flag to see:
  - Generated SQL query
  - Complete list of aggregated data points as `(x, y) -> value`

### SQL Query Builder
- Parses aggregation functions: avg(), sum(), min(), max(), count()
- Generates appropriate GROUP BY queries for charts
- Sanitizes field names but doesn't fully prevent SQL injection (future improvement)
- **SQLite Function Support**: Field arguments in charts can use any SQLite function:
  - String functions: substr(), upper(), lower(), length(), trim(), replace()
  - Date functions: date(), time(), strftime()
  - Math functions: abs(), round(), min(), max()
  - Conditional logic: CASE expressions
  - Arithmetic expressions: field1 * field2, field1 + field2
  - Function nesting: UPPER(substr(field, 1, 5))
  - This enables dynamic data transformation without preprocessing CSV files

### Comparison Visualization (Deprecated - use Multi-comparison)
- **Note**: The standalone comparison mode has been deprecated. Use `mcmp` or `cmp` which now both route to multi-comparison
- **Purpose**: Compares values between two versions/variants across multiple metrics
- **Layout** (simplified in recent update): 
  - Version labels shown at the top (A: version_name, B: version_name)
  - Table format with merged B column showing value and difference:
    - First column: metric names
    - Second column: values from version A
    - Third column: values from version B with difference (format depends on display mode)
- **Display Modes**:
  - `value-percent` (default): Shows value with percentage, e.g., `15 (+50.0%)`
  - `value`: Shows only raw values
  - `diff`: Shows only absolute differences
  - `percent` or `compact`: Shows only percentage changes
  - `value-diff`: Shows value with absolute difference
  - `full`: Shows value, absolute difference, and percentage
- **Usage**:
  - `versions_field`: Field containing version identifiers (typically 2 distinct values)
  - `metrics_field`: Field containing metric names (rows in the output)
  - `value_field`: Optional field to aggregate (defaults to COUNT if not specified)
- **Features**:
  - Compact display with A/B labels to fit in narrow terminals
  - Automatic percentage calculation
  - Handles missing values (defaults to 0)
  - Supports all aggregation functions: avg(), sum(), min(), max(), count()
  - Verbose mode shows generated SQL and all data points
  - When more than 2 groups exist, compares first 2 alphabetically (with warning in verbose mode)
- **Difference Calculation**: B - A, with percentage relative to A
- **Multiple Groups**: For datasets with >2 groups, use multi-comparison or filter to select exactly 2 groups

### Multi-Comparison Visualization
- **Purpose**: Compares 2 or more versions/models (unified comparison mode)
- **Note**: Both `cmp` and `mcmp` commands route here, supporting any number of versions
- **Layout**: 
  - Baseline and comparison versions shown at the top
  - Table format with baseline in first data column:
    - First column: metric names
    - Second column: baseline values (labeled A)
    - Subsequent columns: comparison values with differences (labeled B, C, D, ...)
- **Baseline Selection**:
  - Default: First version alphabetically
  - Custom: Use `--baseline` or `-b` to specify
  - Error handling: Shows available versions if baseline not found
- **Features**:
  - Supports 3+ versions
  - All comparisons relative to the baseline
  - Same display modes as comparison charts
  - Letter labels for compact display
  - Handles missing values gracefully

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

## Recent Changes (2025)

### Major Refactoring
- **PR #9 & #8**: Significant codebase cleanup removing ~800 lines of unused/duplicate code
- Simplified query building architecture
- Consolidated chart rendering logic

### Feature Improvements
- **New groupby command**: Group and aggregate data with `groupby` or `g` command with flexible syntax
- **New filter command**: Filter rows with WHERE conditions using `filter` or `f` command for easy data subsetting
- **New add command**: Add computed columns to CSV data with `add` or `a` command for easy data transformation and piping
- **Unified comparison mode**: Both `cmp` and `mcmp` now use multi-comparison, supporting any number of versions (2+)
- **Deprecated comparison chart**: The separate comparison mode has been deprecated in favor of unified multi-comparison
- **Short command aliases**: Use `q` for `query`, `a` for `add`, `f` for `filter`, `g` for `groupby`, `hm` for `heatmap`, `cmp` for `comparison`, and `mcmp` for `multi-comparison`
- **Verbose mode**: Added `-v`/`--verbose` flag to display generated SQL queries and data points
- **Automatic header detection**: Intelligently determines if CSV has headers (PR #6)
- **Enhanced heatmap legend**: Shows exact value ranges for each character (PR #5)
- **Fixed aggregation**: Proper SQL-based aggregation without double processing (PR #4)
- **Zero-based scale**: For non-negative data, scale starts at 0 for better visualization (PR #7)
- **Display modes for comparisons**: Customizable output format with `--display-mode` or `-m` flag
- **Baseline selection**: Choose baseline for multi-comparison with `--baseline` or `-b` flag
- **Simplified comparison layout**: Merged value and difference columns for more concise output
- **SQLite function support**: Use any SQLite function in field arguments for dynamic data transformation

## Future Enhancements
- Add more chart types (bar charts, line charts, scatter plots)
- Improve SQL injection prevention
- Add configuration file support
- Support for multiple input formats beyond CSV
- Interactive mode with real-time updates