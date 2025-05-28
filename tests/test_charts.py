import pytest
import sqlite3
from uplt.charts.utils import (
    is_numeric_axis, 
    create_numeric_scale, 
    find_bin_index
)
from uplt.charts import (
    create_heatmap,
    create_comparison
)


class TestNumericAxisFunctions:
    def test_is_numeric_axis(self):
        assert is_numeric_axis([1, 2, 3, 4]) == True
        assert is_numeric_axis(["1", "2", "3"]) == True
        assert is_numeric_axis([1.5, 2.5, 3.5]) == True
        assert is_numeric_axis(["1.5", "2.5", "3.5"]) == True
        
        assert is_numeric_axis(["a", "b", "c"]) == False
        assert is_numeric_axis([1, "two", 3]) == False
        assert is_numeric_axis([]) == False
        assert is_numeric_axis(["Engineering", "Marketing"]) == False
    
    def test_create_numeric_scale(self):
        # Basic scale
        scale = create_numeric_scale(0, 10)
        assert scale[0] == 0
        assert scale[-1] == 10
        assert len(scale) > 2
        
        # Single value
        scale = create_numeric_scale(5, 5)
        assert 5 in scale
        assert len(scale) >= 1
        
        # Large numbers
        scale = create_numeric_scale(1000, 5000)
        assert scale[0] <= 1000
        assert scale[-1] >= 5000
        
        # Decimals
        scale = create_numeric_scale(0.1, 0.9)
        assert scale[0] <= 0.1
        assert scale[-1] >= 0.89  # Allow for floating point precision
    
    def test_find_bin_index(self):
        scale = [0, 10, 20, 30, 40]
        
        assert find_bin_index(5, scale) == 0
        assert find_bin_index(15, scale) == 1
        assert find_bin_index(25, scale) == 2
        assert find_bin_index(35, scale) == 3
        
        # Edge cases
        assert find_bin_index(0, scale) == 0
        assert find_bin_index(40, scale) == 3  # Last value goes in last bin
        assert find_bin_index(-5, scale) == -1
        assert find_bin_index(45, scale) == -1


class TestHeatmapAggregation:
    """Test the new SQL-based aggregation for heatmaps."""
    
    def setup_method(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create a test table with duplicate x,y pairs
        self.cursor.execute("""
            CREATE TABLE test_data (x INTEGER, y INTEGER, value INTEGER)
        """)
        
        # Insert test data with multiple values per cell
        test_data = [
            (1, 1, 10), (1, 1, 20), (1, 1, 30),  # avg=20, sum=60, min=10, max=30
            (2, 2, 100), (2, 2, 200), (2, 2, 300),  # avg=200, sum=600, min=100, max=300
        ]
        self.cursor.executemany("INSERT INTO test_data VALUES (?, ?, ?)", test_data)
    
    def teardown_method(self):
        self.conn.close()
    
    def test_sum_aggregation(self):
        result = create_heatmap(
            self.cursor, "x", "y", "sum(value)", "test_data"
        )
        
        assert result is not None
        # The sum values should be 60 and 600
        assert "60" in result
        assert "600" in result
    
    def test_avg_aggregation(self):
        result = create_heatmap(
            self.cursor, "x", "y", "avg(value)", "test_data"
        )
        
        assert result is not None
        # The avg values should be 20 and 200
        assert "20" in result
        assert "200" in result
    
    def test_min_aggregation(self):
        result = create_heatmap(
            self.cursor, "x", "y", "min(value)", "test_data"
        )
        
        assert result is not None
        # The min values should be 10 and 100
        assert "10" in result
        assert "100" in result
    
    def test_max_aggregation(self):
        result = create_heatmap(
            self.cursor, "x", "y", "max(value)", "test_data"
        )
        
        assert result is not None
        # The max values should be 30 and 300
        assert "30" in result
        assert "300" in result


class TestComparison:
    """Test the comparison chart functionality."""
    
    def setup_method(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create a test table matching the example in todo.txt
        self.cursor.execute("""
            CREATE TABLE test_data (
                model_id TEXT,
                input_size INTEGER,
                latency INTEGER,
                score INTEGER
            )
        """)
        
        # Insert test data
        test_data = [
            ('A', 128, 10, 10),
            ('A', 256, 18, 9),
            ('A', 512, 31, 11),
            ('B', 128, 12, 15),
            ('B', 256, 25, 17),
            ('B', 512, 55, 13),
        ]
        self.cursor.executemany("INSERT INTO test_data VALUES (?, ?, ?, ?)", test_data)
    
    def teardown_method(self):
        self.conn.close()
    
    def test_basic_comparison(self):
        """Test basic comparison with raw value field."""
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data"
        )
        
        assert result is not None
        # With short names like A and B, they should be used directly
        assert "| A score" in result
        assert "| B score" in result
        # Should NOT have letter label legend since names are short
        assert "A: A" not in result
        assert "B: B" not in result
        
        # Check values
        assert "10" in result  # A's score for 128
        assert "15 (+50.0%)" in result  # B's score for 128 with percentage (default mode)
        
        # Check all rows are present
        assert "128" in result
        assert "256" in result
        assert "512" in result
    
    def test_comparison_with_aggregation(self):
        """Test comparison with aggregation function."""
        result = create_comparison(
            self.cursor, "model_id", "input_size", "avg(latency)", "test_data"
        )
        
        assert result is not None
        assert "A avg(latency)" in result
        assert "B avg(latency)" in result
        
        # Check specific values
        assert "10" in result  # A's latency for 128
        assert "12 (+20.0%)" in result  # B's latency for 128 with percentage
    
    def test_comparison_without_value_field(self):
        """Test comparison with COUNT(*) when no value field is specified."""
        result = create_comparison(
            self.cursor, "model_id", "input_size", None, "test_data"
        )
        
        assert result is not None
        assert "A count" in result
        assert "B count" in result
        
        # Each combination should have count of 1
        assert "1 (+0.0%)" in result
    
    def test_comparison_with_missing_values(self):
        """Test comparison when one version has missing data."""
        # Add data where B doesn't have a value for input_size 1024
        self.cursor.execute("INSERT INTO test_data VALUES ('A', 1024, 100, 20)")
        
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data"
        )
        
        assert result is not None
        assert "1024" in result
        assert "20" in result  # A's value
        assert "0" in result   # B's missing value defaults to 0
    
    def test_comparison_with_non_numeric_values(self):
        """Test comparison with non-numeric metrics."""
        # Create a different test table
        self.cursor.execute("""
            CREATE TABLE cat_data (
                version TEXT,
                category TEXT,
                count INTEGER
            )
        """)
        
        data = [
            ('v1', 'small', 10),
            ('v1', 'medium', 20),
            ('v1', 'large', 30),
            ('v2', 'small', 15),
            ('v2', 'medium', 25),
            ('v2', 'large', 27),
        ]
        self.cursor.executemany("INSERT INTO cat_data VALUES (?, ?, ?)", data)
        
        result = create_comparison(
            self.cursor, "version", "category", "count", "cat_data"
        )
        
        assert result is not None
        # v1 and v2 are short enough to use directly
        assert "| v1 count" in result
        assert "| v2 count" in result
        # Should NOT have letter label legend
        assert "A: v1" not in result
        assert "B: v2" not in result
        assert "small" in result
        assert "medium" in result
        assert "large" in result
        assert "15 (+50.0%)" in result  # small: 15 with +50% increase
        assert "25 (+25.0%)" in result  # medium: 25 with +25% increase
        assert "27 (-10.0%)" in result  # large: 27 with -10% decrease
    
    def test_comparison_verbose_mode(self):
        """Test comparison with verbose mode enabled."""
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data",
            verbose=True
        )
        
        assert result is not None
        # Result should still be generated in verbose mode
        assert "A score" in result
        assert "B score" in result
    
    def test_comparison_with_null_values(self):
        """Test comparison handles NULL values correctly."""
        self.cursor.execute("INSERT INTO test_data VALUES ('A', 768, NULL, 25)")
        self.cursor.execute("INSERT INTO test_data VALUES ('B', 768, 40, NULL)")
        
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data"
        )
        
        assert result is not None
        assert "768" in result
    
    def test_comparison_single_version(self):
        """Test comparison with only one version returns appropriate message."""
        # Create table with only one version
        self.cursor.execute("DELETE FROM test_data WHERE model_id = 'B'")
        
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data"
        )
        
        assert result == "Need at least 2 versions to compare"
    
    def test_comparison_no_data(self):
        """Test comparison with no data."""
        self.cursor.execute("DELETE FROM test_data")
        
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data"
        )
        
        assert result == "No versions found"
    
    def test_comparison_multiple_versions(self):
        """Test comparison with more than 2 versions (should use first 2)."""
        # Add a third model
        self.cursor.execute("INSERT INTO test_data VALUES ('C', 128, 15, 20)")
        self.cursor.execute("INSERT INTO test_data VALUES ('C', 256, 30, 25)")
        self.cursor.execute("INSERT INTO test_data VALUES ('C', 512, 60, 18)")
        
        result = create_comparison(
            self.cursor, "model_id", "input_size", "score", "test_data"
        )
        
        assert result is not None
        # Should compare A and B (first two alphabetically)
        # With short names, they're used directly
        assert "| A score" in result
        assert "| B score" in result
        # Should NOT have letter label legend
        assert "A: A" not in result
        assert "B: B" not in result
        assert "C:" not in result  # C should not appear
        
        # Check it still shows correct values for A and B
        assert "10" in result  # A's score for 128
        assert "15" in result  # B's score for 128


class TestChartsWithSQLiteFunctions:
    """Test charts work correctly with SQLite functions in field arguments."""
    
    def setup_method(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create a test table with mixed case and various data types
        self.cursor.execute("""
            CREATE TABLE products (
                name TEXT,
                category TEXT,
                price REAL,
                quantity INTEGER,
                date TEXT
            )
        """)
        
        # Insert test data with varied case for testing string functions
        test_data = [
            ('laptop', 'Electronics', 999.99, 10, '2024-01-15'),
            ('MOUSE', 'electronics', 29.99, 50, '2024-01-20'),
            ('Desk Chair', 'FURNITURE', 299.50, 15, '2024-02-01'),
            ('notebook', 'Stationery', 5.99, 100, '2024-02-10'),
            ('MONITOR', 'Electronics', 399.00, 25, '2024-02-15'),
            ('desk lamp', 'furniture', 49.99, 30, '2024-03-01'),
            ('Keyboard', 'ELECTRONICS', -89.99, 20, '2024-03-05'),  # negative price
            ('PENCIL', 'stationery', 1.99, 200, '2024-03-10'),
        ]
        
        self.cursor.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?)",
            test_data
        )
    
    def teardown_method(self):
        self.conn.close()
    
    def test_heatmap_with_upper_function(self):
        """Test heatmap using UPPER() to normalize categories."""
        result = create_heatmap(
            self.cursor, "UPPER(category)", "substr(date, 1, 7)", "sum(quantity)", "products"
        )
        
        assert result is not None
        # All electronics should be grouped together as ELECTRONICS
        assert "ELECTRONICS" in result
        assert "FURNITURE" in result
        assert "STATIONERY" in result
        # Should not have lowercase versions
        assert "electronics" not in result
        assert "furniture" not in result
    
    def test_heatmap_with_substr_function(self):
        """Test heatmap using SUBSTR() for date grouping."""
        # Use substr to extract year-month to create categorical grouping
        result = create_heatmap(
            self.cursor, "category", "substr(date, 1, 7)", "count(*)", "products"
        )
        
        assert result is not None, "Heatmap creation failed"
        # Should have year-month combinations from our test data
        assert "2024-01" in result  # January
        assert "2024-02" in result  # February
        assert "2024-03" in result  # March
    
    def test_heatmap_with_abs_function(self):
        """Test heatmap using ABS() for negative values."""
        result = create_heatmap(
            self.cursor, "category", "CASE WHEN abs(price) < 50 THEN 'low' ELSE 'high' END", 
            "avg(abs(price))", "products"
        )
        
        assert result is not None
        # Should have low and high price categories
        assert "low" in result or "high" in result
    
    def test_heatmap_with_length_function(self):
        """Test heatmap using LENGTH() function."""
        result = create_heatmap(
            self.cursor, "LENGTH(name)", "category", "count(*)", "products"
        )
        
        assert result is not None
        # Product names have different lengths
        # Check for some expected length values in the result
        
    def test_heatmap_with_lower_function(self):
        """Test heatmap using LOWER() function."""
        result = create_heatmap(
            self.cursor, "LOWER(name)", "category", "avg(price)", "products"
        )
        
        assert result is not None
        # All names should be lowercase in the result
        assert "laptop" in result or "mouse" in result or "keyboard" in result
        
    def test_comparison_with_upper_function(self):
        """Test comparison using UPPER() to normalize version field."""
        # Add version field with actual different versions when normalized
        self.cursor.execute("ALTER TABLE products ADD COLUMN version TEXT")
        self.cursor.execute("UPDATE products SET version = 'v1' WHERE rowid <= 4")
        self.cursor.execute("UPDATE products SET version = 'v2' WHERE rowid > 4")
        
        from uplt.charts.comparison import create_comparison
        result = create_comparison(
            self.cursor, "UPPER(version)", "UPPER(category)", "sum(quantity)", "products"
        )
        
        assert result is not None
        # Should show V1 and V2 as versions
        assert "V1" in result
        assert "V2" in result
        assert "ELECTRONICS" in result
        assert "FURNITURE" in result
        assert "STATIONERY" in result
    
    def test_comparison_with_substr_function(self):
        """Test comparison using SUBSTR() function."""
        # Add model field to products table
        self.cursor.execute("ALTER TABLE products ADD COLUMN model TEXT")
        self.cursor.execute("UPDATE products SET model = 'model_v1' WHERE rowid <= 4")
        self.cursor.execute("UPDATE products SET model = 'model_v2' WHERE rowid > 4")
        
        from uplt.charts.comparison import create_comparison
        result = create_comparison(
            self.cursor, "substr(model, -2)", "category", "avg(price)", "products"
        )
        
        assert result is not None
        # Should extract v1 and v2 from model names
        assert "v1" in result or "v2" in result
    
    def test_multi_comparison_with_sqlite_functions(self):
        """Test multi-comparison with SQLite functions."""
        # Create test data with multiple models
        self.cursor.execute("ALTER TABLE products ADD COLUMN model TEXT")
        self.cursor.execute("UPDATE products SET model = 'model_a_v1' WHERE rowid <= 3")
        self.cursor.execute("UPDATE products SET model = 'model_b_v2' WHERE rowid BETWEEN 4 AND 6")
        self.cursor.execute("UPDATE products SET model = 'model_c_v3' WHERE rowid > 6")
        
        from uplt.charts.multi_comparison import create_multi_comparison
        result = create_multi_comparison(
            self.cursor, "substr(model, 7, 1)", "UPPER(category)", "sum(quantity)", "products"
        )
        
        assert result is not None
        # Should extract a, b, c from model names
        # Since a, b, c are very short, they should be used directly
        assert "| a " in result
        assert "| b " in result
        assert "| c " in result
        # Should NOT have letter label legend
        assert "Baseline (A): a" not in result
        
    def test_query_builder_with_sqlite_functions(self):
        """Test that query builder handles SQLite functions correctly."""
        from uplt.query_builder import parse_aggregation, parse_chart_command
        
        # Test parse_aggregation with SQLite expressions
        func, field = parse_aggregation("avg(price * quantity)")
        assert func == "avg"
        assert field == "price * quantity"
        
        # Test parse_chart_command with SQLite functions in field names
        chart_type, options = parse_chart_command([
            "heatmap", 
            "substr(field1, 1, 3)", 
            "UPPER(field2)", 
            "avg(value)"
        ])
        assert chart_type == "heatmap"
        assert options["x_field"] == "substr(field1, 1, 3)"
        assert options["y_field"] == "UPPER(field2)"
        assert options["value_field"] == "avg(value)"


class TestVersionLabeling:
    """Test version labeling behavior in comparison charts."""
    
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        
        # Create test table for short names
        self.cursor.execute("""
            CREATE TABLE short_names (
                version TEXT,
                metric TEXT,
                value INTEGER
            )
        """)
        
        # Insert test data with short version names
        short_data = [
            ('v1', 'test1', 10),
            ('v2', 'test1', 15),
            ('v1', 'test2', 20),
            ('v2', 'test2', 30),
        ]
        self.cursor.executemany("INSERT INTO short_names VALUES (?, ?, ?)", short_data)
        
        # Create test table for long names
        self.cursor.execute("""
            CREATE TABLE long_names (
                version TEXT,
                metric TEXT,
                value INTEGER
            )
        """)
        
        # Insert test data with long version names
        long_data = [
            ('model_version_1', 'test1', 10),
            ('model_version_2', 'test1', 15),
            ('model_version_1', 'test2', 20),
            ('model_version_2', 'test2', 30),
        ]
        self.cursor.executemany("INSERT INTO long_names VALUES (?, ?, ?)", long_data)
        
        # Create test table for multi-comparison
        self.cursor.execute("""
            CREATE TABLE multi_versions (
                version TEXT,
                metric TEXT,
                value INTEGER
            )
        """)
        
        # Insert test data with multiple versions
        multi_data = [
            ('v1', 'test1', 10),
            ('v2', 'test1', 15),
            ('v3', 'test1', 12),
            ('v1', 'test2', 20),
            ('v2', 'test2', 30),
            ('v3', 'test2', 25),
        ]
        self.cursor.executemany("INSERT INTO multi_versions VALUES (?, ?, ?)", multi_data)
    
    def teardown_method(self):
        self.conn.close()
    
    def test_comparison_with_short_names(self):
        """Test that short version names are used directly in comparison."""
        from uplt.charts.comparison import create_comparison
        result = create_comparison(
            self.cursor, "version", "metric", "value", "short_names"
        )
        
        assert result is not None
        # Should use original names v1 and v2
        assert "| v1 " in result
        assert "| v2 " in result
        # Should NOT have letter labels
        assert "A: v1" not in result
        assert "B: v2" not in result
    
    def test_comparison_with_long_names(self):
        """Test that long version names use letter labels in comparison."""
        from uplt.charts.comparison import create_comparison
        result = create_comparison(
            self.cursor, "version", "metric", "value", "long_names"
        )
        
        assert result is not None
        # Should have letter labels
        assert "A: model_version_1" in result
        assert "B: model_version_2" in result
        # Should use A/B in table headers
        assert "| A " in result
        assert "| B " in result
    
    def test_multi_comparison_with_short_names(self):
        """Test that short version names are used directly in multi-comparison."""
        from uplt.charts.multi_comparison import create_multi_comparison
        result = create_multi_comparison(
            self.cursor, "version", "metric", "value", "multi_versions"
        )
        
        assert result is not None
        # Should use original names v1, v2, v3
        assert "| v1 " in result
        assert "| v2 " in result
        assert "| v3 " in result
        # Should NOT have letter labels
        assert "Baseline (A):" not in result
        assert "B: v2" not in result
        assert "C: v3" not in result
    
    def test_multi_comparison_with_mixed_lengths(self):
        """Test multi-comparison with mixed name lengths."""
        # Create table with mixed length names
        self.cursor.execute("""
            CREATE TABLE mixed_names (
                version TEXT,
                metric TEXT,
                value INTEGER
            )
        """)
        
        mixed_data = [
            ('v1', 'test1', 10),
            ('model_long_name', 'test1', 15),
            ('v3', 'test1', 12),
        ]
        self.cursor.executemany("INSERT INTO mixed_names VALUES (?, ?, ?)", mixed_data)
        
        from uplt.charts.multi_comparison import create_multi_comparison
        result = create_multi_comparison(
            self.cursor, "version", "metric", "value", "mixed_names"
        )
        
        assert result is not None
        # Should use letter labels because one name is too long
        assert "Baseline (A):" in result
        assert "B:" in result
        assert "C:" in result


class TestChartsWithArithmeticExpressions:
    """Test charts with arithmetic and complex expressions."""
    
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        
        # Create test table
        self.cursor.execute("""
            CREATE TABLE products (
                name TEXT,
                category TEXT,
                price REAL,
                quantity INTEGER,
                date TEXT
            )
        """)
        
        # Insert test data
        test_data = [
            ('laptop', 'Electronics', 999.99, 10, '2024-01-15'),
            ('mouse', 'Electronics', 29.99, 50, '2024-01-20'),
            ('desk', 'Furniture', 299.50, 15, '2024-02-01'),
            ('notebook', 'Stationery', 5.99, 100, '2024-02-10'),
            ('monitor', 'Electronics', 399.00, 25, '2024-02-15'),
        ]
        
        self.cursor.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?)",
            test_data
        )
    
    def teardown_method(self):
        self.conn.close()
    
    def test_heatmap_with_arithmetic_expression(self):
        """Test heatmap with arithmetic expressions."""
        result = create_heatmap(
            self.cursor, "category", "CASE WHEN price * quantity > 1000 THEN 'high_value' ELSE 'low_value' END",
            "count(*)", "products"
        )
        
        assert result is not None
        assert "high_value" in result or "low_value" in result
    
    def test_heatmap_with_round_function(self):
        """Test heatmap using ROUND() function."""
        result = create_heatmap(
            self.cursor, "category", "round(price / 100) * 100", "count(*)", "products"
        )
        
        assert result is not None
        # Prices should be rounded to nearest hundred
    
    def test_comparison_with_case_expression(self):
        """Test comparison with complex CASE expression."""
        # Add a version field
        self.cursor.execute("ALTER TABLE products ADD COLUMN version TEXT")
        self.cursor.execute("UPDATE products SET version = 'v1' WHERE rowid % 2 = 0")
        self.cursor.execute("UPDATE products SET version = 'v2' WHERE rowid % 2 = 1")
        
        result = create_comparison(
            self.cursor, 
            "version", 
            "CASE WHEN quantity < 30 THEN 'low_stock' WHEN quantity < 100 THEN 'medium_stock' ELSE 'high_stock' END",
            "avg(price)", 
            "products"
        )
        
        assert result is not None
        assert "low_stock" in result or "medium_stock" in result or "high_stock" in result
    
    def test_charts_with_concatenation(self):
        """Test charts with string concatenation."""
        result = create_heatmap(
            self.cursor,
            "substr(category, 1, 3) || '_cat'",
            "substr(date, 1, 7)",
            "count(*)",
            "products"
        )
        
        assert result is not None
        # Categories should be truncated and suffixed
        assert "_cat" in result
