#!/bin/bash

# Demonstrate pairwise comparisons with multi-group data

echo "=== Pairwise Comparison Demo ==="
echo "Data: multi_group_test.csv (ModelA, ModelB, ModelC)"
echo

echo "=== LATENCY COMPARISONS ==="
echo
echo "1. ModelA vs ModelB (default - first two groups)"
cat multi_group_test.csv | uplt cmp model test_case latency

echo
echo "2. ModelA vs ModelC"
cat multi_group_test.csv | grep -E "model|ModelA|ModelC" | uplt cmp model test_case latency

echo
echo "3. ModelB vs ModelC"
cat multi_group_test.csv | grep -E "model|ModelB|ModelC" | uplt cmp model test_case latency

echo
echo "=== ACCURACY COMPARISONS ==="
echo
echo "4. All models accuracy (A vs B)"
cat multi_group_test.csv | uplt cmp model test_case accuracy

echo
echo "=== THROUGHPUT COMPARISONS ==="
echo
echo "5. ModelB vs ModelC throughput"
cat multi_group_test.csv | grep -E "model|ModelB|ModelC" | uplt cmp model test_case throughput

echo
echo "=== FILTERING WITH SQL ==="
echo
echo "6. Compare only 'large_input' test cases"
cat multi_group_test.csv | uplt q "SELECT * FROM data WHERE test_case = 'large_input'" | uplt cmp model test_case latency

echo
echo "=== VERBOSE MODE (shows warning about >2 groups) ==="
echo
echo "7. Running with -v flag"
cat multi_group_test.csv | uplt -v cmp model test_case latency 2>&1 | head -20