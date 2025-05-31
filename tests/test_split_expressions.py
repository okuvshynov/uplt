"""Tests for the split_expressions function."""

import pytest
from uplt.core import split_expressions


class TestSplitExpressions:
    """Test cases for split_expressions function."""
    
    def test_simple_expressions(self):
        """Test splitting simple comma-separated expressions."""
        result = split_expressions("a, b, c")
        assert result == ["a", "b", "c"]
    
    def test_no_spaces(self):
        """Test splitting without spaces around commas."""
        result = split_expressions("a,b,c")
        assert result == ["a", "b", "c"]
    
    def test_single_expression(self):
        """Test single expression (no comma)."""
        result = split_expressions("single_field")
        assert result == ["single_field"]
    
    def test_empty_string(self):
        """Test empty string."""
        result = split_expressions("")
        assert result == []
    
    def test_expressions_with_parentheses(self):
        """Test expressions containing parentheses with commas."""
        result = split_expressions("IIF(a > 0, 'yes', 'no'), b")
        assert result == ["IIF(a > 0, 'yes', 'no')", "b"]
    
    def test_multiple_functions_with_commas(self):
        """Test multiple functions each containing commas."""
        result = split_expressions("substr(name, 1, 5), IIF(age > 18, 'adult', 'minor'), upper(status)")
        expected = ["substr(name, 1, 5)", "IIF(age > 18, 'adult', 'minor')", "upper(status)"]
        assert result == expected
    
    def test_nested_functions(self):
        """Test nested function calls."""
        result = split_expressions("UPPER(substr(name, 1, 3)), LENGTH(TRIM(description))")
        expected = ["UPPER(substr(name, 1, 3))", "LENGTH(TRIM(description))"]
        assert result == expected
    
    def test_case_expressions(self):
        """Test CASE expressions with nested commas."""
        expr = "CASE WHEN status = 'active' THEN 'on' ELSE 'off' END, category"
        result = split_expressions(expr)
        expected = ["CASE WHEN status = 'active' THEN 'on' ELSE 'off' END", "category"]
        assert result == expected
    
    def test_complex_case_with_functions(self):
        """Test complex CASE expression with function calls."""
        expr = "CASE WHEN LENGTH(name) > 5 THEN substr(name, 1, 5) ELSE name END, status"
        result = split_expressions(expr)
        expected = ["CASE WHEN LENGTH(name) > 5 THEN substr(name, 1, 5) ELSE name END", "status"]
        assert result == expected
    
    def test_expressions_with_aliases(self):
        """Test expressions with AS aliases."""
        result = split_expressions("substr(name, 1, 5) as prefix, age * 2 as double_age")
        expected = ["substr(name, 1, 5) as prefix", "age * 2 as double_age"]
        assert result == expected
    
    def test_quoted_strings_with_commas(self):
        """Test expressions with quoted strings containing commas."""
        result = split_expressions("REPLACE(name, ',', ';'), status")
        expected = ["REPLACE(name, ',', ';')", "status"]
        assert result == expected
    
    def test_double_quoted_strings(self):
        """Test expressions with double-quoted strings."""
        result = split_expressions('REPLACE(name, ",", ";"), status')
        expected = ['REPLACE(name, ",", ";")', "status"]
        assert result == expected
    
    def test_mixed_quotes(self):
        """Test expressions with mixed quote types."""
        result = split_expressions("CONCAT(first_name, ' ', last_name), status")
        expected = ["CONCAT(first_name, ' ', last_name)", "status"]
        assert result == expected
    
    def test_arithmetic_expressions(self):
        """Test arithmetic expressions."""
        result = split_expressions("price * quantity, tax_rate / 100")
        expected = ["price * quantity", "tax_rate / 100"]
        assert result == expected
    
    def test_deeply_nested_parentheses(self):
        """Test deeply nested parentheses."""
        expr = "func1(func2(func3(a, b), c), d), simple_field"
        result = split_expressions(expr)
        expected = ["func1(func2(func3(a, b), c), d)", "simple_field"]
        assert result == expected
    
    def test_empty_expressions_in_list(self):
        """Test handling of empty expressions (consecutive commas)."""
        result = split_expressions("a, , b")
        expected = ["a", "", "b"]
        assert result == expected
    
    def test_trailing_comma(self):
        """Test expression with trailing comma."""
        result = split_expressions("a, b,")
        expected = ["a", "b"]
        assert result == expected
    
    def test_leading_comma(self):
        """Test expression with leading comma."""
        result = split_expressions(",a, b")
        expected = ["", "a", "b"]
        assert result == expected
    
    def test_whitespace_handling(self):
        """Test proper whitespace trimming."""
        result = split_expressions("  a  ,  b  ,  c  ")
        expected = ["a", "b", "c"]
        assert result == expected
    
    def test_complex_real_world_example(self):
        """Test complex real-world example from the bug report."""
        expr = "substr(model_filename, 10) as model, IIF(n_gpu_layers > 0, 'gpu', 'cpu') as device"
        result = split_expressions(expr)
        expected = ["substr(model_filename, 10) as model", "IIF(n_gpu_layers > 0, 'gpu', 'cpu') as device"]
        assert result == expected
    
    def test_unmatched_parentheses(self):
        """Test behavior with unmatched parentheses (should still work reasonably)."""
        # This tests robustness - the function should handle malformed input gracefully
        result = split_expressions("func(a, b, missing_close, other_field")
        expected = ["func(a, b, missing_close, other_field"]
        assert result == expected
    
    def test_unmatched_quotes(self):
        """Test behavior with unmatched quotes."""
        # This tests robustness - should handle malformed input
        result = split_expressions("'unclosed string, other_field")
        expected = ["'unclosed string, other_field"]
        assert result == expected