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

uplt supports five modes:
1. **SQL Query Mode**: Execute raw SQL queries on CSV data
2. **Add Column Mode**: Add computed columns to CSV data for piping
3. **Filter Mode**: Filter rows based on WHERE conditions
4. **Group By Mode**: Aggregate data by one or more fields
5. **Chart Mode**: Create terminal-based charts from CSV data (heatmaps, comparisons)

### SQL Query Mode

Pipe CSV data to `uplt` with the `query` command:

```bash
cat data.csv | uplt query "SELECT foo, bar, SUM(baz) FROM data GROUP BY foo, bar"
```

### Add Column Mode

Add computed columns to your CSV data:

```bash
# Add a calculated column
cat data.csv | uplt add "price * quantity as total"

# Add multiple columns in one command
cat data.csv | uplt add "price * quantity as total, price * 0.1 as tax"

# Functions with commas are properly parsed
cat data.csv | uplt add "IIF(price > 100, 'expensive', 'cheap') as category, substr(name, 1, 3) as prefix"

# Add a conditional column
cat data.csv | uplt add "case when price > 100 then 'expensive' else 'cheap' end as category"

# Use SQLite functions
cat data.csv | uplt add "lower(name) as name_lower"

# Complex expressions with nested functions
cat data.csv | uplt add "UPPER(TRIM(description)) as clean_desc, LENGTH(TRIM(name)) as name_len"

# Chain with other commands
cat latency.csv | uplt add "if(n_items > 1000, 1, 0) as large_query" | uplt cmp version large_query latency_ms
```

### Filter Mode

Filter rows based on WHERE conditions:

```bash
# Simple filtering
cat data.csv | uplt filter "price > 100"

# Complex conditions
cat data.csv | uplt filter "price > 100 AND quantity < 50"

# String comparisons
cat data.csv | uplt filter "status = 'active'"

# Use SQLite functions
cat data.csv | uplt filter "UPPER(category) = 'ELECTRONICS'"

# Chain with other commands
cat data.csv | uplt filter "price > 50" | uplt add "price * 0.1 as discount"
```

### Group By Mode

Aggregate data with flexible syntax:

```bash
# Full syntax with specific aggregations
cat data.csv | uplt groupby "category,region" "sum(sales),avg(price)"

# Shortcut: apply same function to all numeric columns
cat data.csv | uplt groupby category sum
cat data.csv | uplt groupby category avg
cat data.csv | uplt groupby category min

# Default: averages all numeric columns
cat data.csv | uplt groupby category

# Short alias
cat data.csv | uplt g category sum
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

### Adding Columns

#### Simple calculations
```bash
# Add a total column
cat sales.csv | uplt add "price * quantity as total"

# Add multiple columns by chaining
cat sales.csv | uplt add "price * quantity as total" | uplt add "total * 0.1 as tax"

# Add multiple columns in one command (more efficient)
cat sales.csv | uplt add "price * quantity as total, total * 0.1 as tax"
```

#### Conditional columns
```bash
# Categorize based on conditions
cat products.csv | uplt add "case when price > 100 then 'premium' else 'budget' end as tier"

# Binary flags
cat logs.csv | uplt add "if(response_time > 1000, 1, 0) as slow_request"
```

#### Data transformation pipelines
```bash
# Transform data then create charts
cat performance.csv | uplt add "if(cpu_usage > 80, 'high', 'normal') as load" | uplt cmp server load avg_response_time

# Complex multi-step analysis
cat orders.csv | \
  uplt add "quantity * unit_price as order_total" | \
  uplt add "case when order_total > 1000 then 'large' else 'small' end as order_size" | \
  uplt cmp region order_size "sum(order_total)"
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

### Filtering Data

#### Basic filtering
```bash
# Filter rows by condition
cat products.csv | uplt filter "price > 100"

# With multiple conditions
cat products.csv | uplt filter "price > 100 AND quantity > 0"

# String comparisons
cat logs.csv | uplt filter "status = 'ERROR'"
cat users.csv | uplt filter "country IN ('US', 'CA', 'MX')"
```

#### Using SQLite functions
```bash
# Case-insensitive filtering
cat products.csv | uplt filter "LOWER(category) = 'electronics'"

# Date filtering
cat logs.csv | uplt filter "substr(timestamp, 1, 10) = '2024-01-15'"

# Pattern matching
cat users.csv | uplt filter "email LIKE '%@gmail.com'"
```

#### Filtering pipelines
```bash
# Filter then aggregate
cat sales.csv | uplt filter "date >= '2024-01-01'" | uplt query "SELECT SUM(amount) FROM data"

# Filter, transform, then chart
cat performance.csv | uplt filter "response_time > 100" | uplt add "if(response_time > 1000, 'slow', 'normal') as speed" | uplt heatmap server speed "count(*)"

# Multi-step filtering
cat products.csv | uplt filter "price > 50" | uplt add "price * 0.1 as discount" | uplt filter "discount > 10"
```

### Grouping and Aggregation

#### Basic groupby
```bash
# Group by single field with specific aggregations
cat sales.csv | uplt groupby region "sum(sales),avg(price)"

# Group by multiple fields
cat sales.csv | uplt groupby "category,region" "sum(sales),count(*)"

# Functions with commas are properly parsed
cat data.csv | uplt groupby "IIF(price > 100, 'expensive', 'cheap') as tier, category" "sum(sales)"

# Using SQLite aggregate functions
cat data.csv | uplt groupby category "min(price),max(price),avg(price)"

# Complex expressions in both grouping and aggregation
cat data.csv | uplt groupby "substr(model_filename, 10) as model, IIF(n_gpu_layers > 0, 'gpu', 'cpu') as device" "avg(latency)"
```

#### Aggregate-all shortcuts
```bash
# Apply same function to all numeric columns
cat sales.csv | uplt groupby region sum    # Sums all numeric columns
cat sales.csv | uplt groupby region avg    # Averages all numeric columns
cat sales.csv | uplt groupby region min    # Finds minimum of all numeric columns
cat sales.csv | uplt groupby region max    # Finds maximum of all numeric columns
cat sales.csv | uplt groupby region count  # Counts all numeric columns

# Default behavior (no function specified = avg)
cat sales.csv | uplt groupby region        # Same as: uplt groupby region avg
```

#### Groupby pipelines
```bash
# Filter, then group
cat sales.csv | uplt filter "date >= '2024-01-01'" | uplt groupby category "sum(revenue)"

# Group, then filter results
cat sales.csv | uplt groupby store "sum(sales)" | uplt filter "sum(sales) > 10000"

# Complex analysis pipeline
cat orders.csv | \
  uplt filter "status = 'completed'" | \
  uplt add "quantity * unit_price as total" | \
  uplt groupby "customer_id,month" "sum(total),count(*) as order_count" | \
  uplt filter "order_count >= 5"
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
- `a` → `add`
- `f` → `filter`
- `g` → `groupby`
- `hm` → `heatmap`
- `cmp` → `mcmp` (comparison, works with 2+ versions)
- `mcmp` → `multi-comparison` (explicit multi-comparison command)

Example:
```bash
cat data.csv | uplt q "SELECT * FROM data"
cat data.csv | uplt a "price * 0.1 as tax"
cat data.csv | uplt f "price > 100"
cat data.csv | uplt g category sum
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
