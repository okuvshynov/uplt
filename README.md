# uplt

Execute SQL queries on CSV data from stdin and create terminal charts.

## Installation

```bash
pip install uplt
```

or with uv:

```bash
uv pip install uplt
```

## Usage

uplt supports two modes:
1. **SQL Query Mode**: Execute raw SQL queries on CSV data
2. **Chart Mode**: Create terminal-based charts from CSV data (heatmaps, comparisons)

### SQL Query Mode

Pipe CSV data to `uplt` with the `query` command:

```bash
cat data.csv | uplt query "SELECT foo, bar, SUM(baz) FROM data GROUP BY foo, bar"
```

### Chart Mode

Create visualizations directly in your terminal:

```bash
# Basic heatmap counting occurrences
cat data.csv | uplt heatmap x_field y_field

# Heatmap with aggregation
cat data.csv | uplt heatmap department age "avg(salary)"

# Compare versions/models (works with 2+ versions)
cat data.csv | uplt mcmp model_id metric_name score

# Short form (cmp is an alias for mcmp)
cat data.csv | uplt cmp model_id metric_name score
```

## Examples

### SQL Queries

#### Basic query
```bash
cat data/test.csv | uplt query "SELECT * FROM data WHERE age > 30"
```

#### Aggregation
```bash
cat data/test.csv | uplt query "SELECT department, AVG(salary) FROM data GROUP BY department"
```

#### Custom table name
```bash
cat data.csv | uplt -t employees query "SELECT * FROM employees WHERE department = 'Engineering'"
```

#### Working with headerless CSV files
```bash
# Auto-detection will recognize this as headerless data
echo -e "1,100,200\n2,150,300\n3,200,400" | uplt query "SELECT f1, f2+f3 as total FROM data"

# Or explicitly specify no headers
cat no_headers.csv | uplt --no-header query "SELECT f1, f2 FROM data WHERE f3 > 100"
```

#### Using SQLite functions in field arguments
```bash
# Extract substring from model names for grouping
cat data/qwen30b3a_q2.csv | uplt mcmp "substr(model_filename, -15)" n_depth avg_ts

# Normalize case for consistent grouping
cat data.csv | uplt heatmap "UPPER(category)" month "sum(revenue)"

# Group by string length
cat data.csv | uplt comparison version "LENGTH(name)" "avg(score)"

# Extract date parts
cat logs.csv | uplt heatmap "substr(timestamp, 1, 10)" status "count(*)"

# Use CASE expressions for custom grouping
cat data.csv | uplt heatmap category "CASE WHEN price < 50 THEN 'low' ELSE 'high' END" "count(*)"

# Combine multiple functions
cat data.csv | uplt cmp "UPPER(substr(model, 1, 3))" metric value
```

### Charts

#### Basic heatmap (counts occurrences)
```bash
cat data/test.csv | uplt heatmap department age
```

#### Heatmap with aggregation
```bash
cat data/test.csv | uplt heatmap department age "avg(salary)"
cat data/test.csv | uplt heatmap department age "sum(salary)"
cat data/test.csv | uplt heatmap department age "max(salary)"
```

The heatmap uses Unicode block characters (░▒▓█) to show intensity. It automatically detects numeric vs categorical axes:
- Numeric axes are displayed with proper scales and binning
- Categorical axes show distinct values
- Sparse numeric data is handled with interpolated bins
- The legend shows exact value ranges for each character (e.g., '░': [10, 20))
- For non-negative data, the scale starts at 0 to properly distinguish between no data (space) and small positive values
- SQLite functions can be used in field arguments for dynamic grouping

#### Comparison chart
```bash
# Compare 2 or more versions/models
cat data/comparison_test.csv | uplt mcmp model_id input_size score

# Short form (cmp is an alias for mcmp)
cat data/comparison_test.csv | uplt cmp model_id input_size score

# With aggregation
cat data/comparison_test.csv | uplt cmp model_id input_size "avg(latency)"

# Count occurrences (when no value field specified)
cat data/comparison_test.csv | uplt cmp model_id category

# Different display modes
cat data.csv | uplt cmp models metrics value --display-mode=value     # Show only values
cat data.csv | uplt cmp models metrics value --display-mode=diff      # Show only differences
cat data.csv | uplt cmp models metrics value --display-mode=percent   # Show only percentages
cat data.csv | uplt cmp models metrics value -m compact               # Short form

# Specify custom baseline (default is first version alphabetically)
cat data.csv | uplt cmp model test_case latency --baseline ModelB
cat data.csv | uplt cmp model test_case latency -b ModelC
```

Output format with 2 versions:
```
        | v1 | v2         
--------+----+------------
test1   | 10 | 15 (+50.0%)
test2   | 20 | 30 (+50.0%)
```

Output format with 3+ versions:
```
        | v1 | v2          | v3         
--------+----+-------------+------------
test1   | 10 | 15 (+50.0%) | 12 (+20.0%)
test2   | 20 | 30 (+50.0%) | 25 (+25.0%)
```

The comparison chart:
- Works with any number of versions (2 or more)
- Uses original names when short enough (≤8 chars), otherwise shows letter labels with legend
- First version (alphabetically) is used as baseline for percentage calculations
- Supports custom baseline selection with `--baseline` or `-b`
- Shows all comparisons relative to the baseline
- Supports all aggregation functions: avg(), sum(), min(), max()
- Handles missing values by defaulting to 0


## Options

- `--table-name`, `-t`: Name for the SQLite table (default: data)
- `--delimiter`, `-d`: CSV delimiter (auto-detected if not specified)
- `--header`: Force treating first row as headers
- `--no-header`: Force treating first row as data (columns named f1, f2, ..., fn)
- `--verbose`, `-v`: Show additional information (including generated SQL for charts and aggregated data points)
- `--display-mode`, `-m`: Display mode for comparison charts (default: value-percent)
  - `value-percent`: Show value with percentage change (e.g., `15 (+50.0%)`)
  - `value`: Show only raw values
  - `diff`: Show only absolute differences
  - `percent` or `compact`: Show only percentage changes
  - `value-diff`: Show value with absolute difference
  - `full`: Show value, absolute difference, and percentage
- `--baseline`, `-b`: Baseline version for multi-comparison (defaults to first version alphabetically)

### Header Detection

By default, uplt automatically detects whether the first row contains headers by analyzing the data:
- If the first row contains mostly text and subsequent rows contain more numeric values, it's treated as headers
- If the first row contains mostly numeric values (≥70%), it's treated as data
- Use `--header` or `--no-header` to override auto-detection

## Short Command Aliases

For convenience, uplt provides short aliases for common commands:
- `q` → `query`
- `hm` → `heatmap`
- `cmp` → `mcmp` (comparison, works with 2+ versions)
- `mcmp` → `multi-comparison` (explicit multi-comparison command)

Example:
```bash
cat data.csv | uplt q "SELECT * FROM data"
cat data.csv | uplt hm x_field y_field
cat data.csv | uplt cmp version metric value  # Works with any number of versions
```

## Features

- Automatic CSV header detection
- Automatic delimiter detection (comma, semicolon, tab, space, pipe)
- Column type inference (INTEGER, REAL, TEXT)
- Sanitized column names for valid SQL identifiers
- In-memory SQLite database for fast queries
- Standard CSV output format
- Multiple chart types: heatmaps and comparisons (supports 2+ versions)
- Customizable display modes for comparison charts
- Baseline selection for comparisons with 3+ versions
- Verbose mode for debugging with `-v` flag
- **SQLite function support**: Use any SQLite function (substr, upper, lower, length, etc.) in field arguments for dynamic data transformation and grouping

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest
```

## License

MIT
