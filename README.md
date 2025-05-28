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

# Compare two versions/models
cat data.csv | uplt comparison model_id metric_name score
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

#### Comparison chart
```bash
# Basic comparison (shows difference in values between two versions)
cat data/comparison_test.csv | uplt comparison model_id input_size score

# Short form
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
```

Output format (default: value-percent mode):
```
A: model_a_name
B: model_b_name

        | A score | B score    
--------+---------+------------
128     | 10      | 15 (+50.0%)
256     | 9       | 17 (+88.9%)
512     | 11      | 13 (+18.2%)
```

The comparison chart:
- Shows version/model names at the top to avoid long column headers
- Uses A/B labels in the table for compact display
- Compares values between exactly 2 versions/variants
- Shows values and differences in a single column for B (customizable with display modes)
- Calculates difference as: B - A
- Supports all aggregation functions: avg(), sum(), min(), max()
- Handles missing values by defaulting to 0

#### Multi-comparison chart
```bash
# Compare multiple versions against a baseline
cat data/multi_group_test.csv | uplt multi-comparison model test_case latency

# Short form
cat data/multi_group_test.csv | uplt mcmp model test_case latency

# With aggregation
cat data/multi_group_test.csv | uplt mcmp model test_case "avg(latency)"

# Specify custom baseline (default is first version alphabetically)
cat data/multi_group_test.csv | uplt mcmp model test_case latency --baseline ModelB
cat data/multi_group_test.csv | uplt mcmp model test_case latency -b ModelC
```

Output format:
```
Baseline (A): ModelA
B: ModelB
C: ModelC

             | A   | B            | C           
-------------+-----+--------------+-------------
large_input  | 125 | 105 (-16.0%) | 140 (+12.0%)
medium_input | 78  | 65 (-16.7%)  | 85 (+9.0%)  
small_input  | 45  | 38 (-15.6%)  | 52 (+15.6%) 
xlarge_input | 210 | 175 (-16.7%) | 230 (+9.5%)
```

The multi-comparison chart:
- Compares 3 or more versions/models
- Uses the first version alphabetically as baseline by default
- Allows custom baseline selection with `--baseline` or `-b`
- Shows all comparisons relative to the baseline
- Uses letter labels (A, B, C, ...) for compact display
- Supports all display modes like comparison charts

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
- `cmp` → `comparison`
- `mcmp` → `multi-comparison`

Example:
```bash
cat data.csv | uplt q "SELECT * FROM data"
cat data.csv | uplt hm x_field y_field
cat data.csv | uplt cmp version metric value
cat data.csv | uplt mcmp models metrics value
```

## Features

- Automatic CSV header detection
- Automatic delimiter detection (comma, semicolon, tab, space, pipe)
- Column type inference (INTEGER, REAL, TEXT)
- Sanitized column names for valid SQL identifiers
- In-memory SQLite database for fast queries
- Standard CSV output format
- Multiple chart types: heatmaps, comparisons, and multi-comparisons
- Customizable display modes for comparison charts
- Baseline selection for multi-comparison charts
- Verbose mode for debugging with `-v` flag

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest
```

## License

MIT
