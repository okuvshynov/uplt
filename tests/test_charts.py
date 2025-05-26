import pytest
import sqlite3
from uplt.charts import (
    is_numeric_axis, 
    create_numeric_scale, 
    find_bin_index,
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
        # Check version labels
        assert "A: A" in result
        assert "B: B" in result
        
        # Check header
        assert "A score" in result
        assert "B score" in result
        assert "diff" in result
        
        # Check values
        assert "10" in result  # A's score for 128
        assert "15" in result  # B's score for 128
        assert "+5 (+50.0%)" in result  # Difference
        
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
        assert "12" in result  # B's latency for 128
        assert "+2 (+20.0%)" in result
    
    def test_comparison_without_value_field(self):
        """Test comparison with COUNT(*) when no value field is specified."""
        result = create_comparison(
            self.cursor, "model_id", "input_size", None, "test_data"
        )
        
        assert result is not None
        assert "A count" in result
        assert "B count" in result
        
        # Each combination should have count of 1
        assert "+0 (+0.0%)" in result
    
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
        assert "A: v1" in result
        assert "B: v2" in result
        assert "small" in result
        assert "medium" in result
        assert "large" in result
        assert "+5 (+50.0%)" in result  # small: 15-10
        assert "+5 (+25.0%)" in result  # medium: 25-20
        assert "-3 (-10.0%)" in result  # large: 27-30
    
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
