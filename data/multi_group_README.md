# Multi-Group Comparison Test Data

This file (`multi_group_test.csv`) contains performance metrics for three models (ModelA, ModelB, ModelC) across different test cases.

## Data Structure

- **model**: ModelA, ModelB, ModelC
- **test_case**: small_input, medium_input, large_input, xlarge_input
- **latency**: Response time in milliseconds
- **accuracy**: Model accuracy (0-1 scale)
- **throughput**: Requests per second

## Usage Examples

Since `uplt cmp` compares exactly 2 groups at a time, you need to filter the data for pairwise comparisons when you have more than 2 groups.

### Compare all pairs

```bash
# ModelA vs ModelB (default - first two groups)
cat multi_group_test.csv | uplt cmp model test_case latency

# ModelA vs ModelC
cat multi_group_test.csv | grep -E "model|ModelA|ModelC" | uplt cmp model test_case latency

# ModelB vs ModelC
cat multi_group_test.csv | grep -E "model|ModelB|ModelC" | uplt cmp model test_case latency
```

### Compare different metrics

```bash
# Accuracy comparison
cat multi_group_test.csv | uplt cmp model test_case accuracy

# Throughput comparison
cat multi_group_test.csv | uplt cmp model test_case throughput

# With aggregation (if you had multiple runs)
cat multi_group_test.csv | uplt cmp model test_case "avg(latency)"
```

### Using SQL queries for filtering

You can also use uplt's query mode to filter before comparison:

```bash
# Compare only large inputs
cat multi_group_test.csv | uplt q "SELECT * FROM data WHERE test_case = 'large_input'" | uplt cmp model test_case latency
```

## Expected Behavior

When the data contains more than 2 distinct values in the versions field:
- By default, only the first 2 groups (alphabetically) are compared
- A warning is shown in verbose mode: `Warning: Expected 2 versions but found 3: ['ModelA', 'ModelB', 'ModelC']`
- Use filtering (grep, SQL, etc.) to select exactly 2 groups for comparison