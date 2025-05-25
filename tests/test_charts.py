import pytest
import sqlite3
from uplt.charts import (
    is_numeric_axis, 
    create_numeric_scale, 
    find_bin_index,
    create_heatmap
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
