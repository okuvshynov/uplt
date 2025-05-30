"""Test the groupby command functionality."""
import subprocess
import sys
import pytest


class TestGroupByCommand:
    """Test the groupby command functionality."""
    
    def test_groupby_full_syntax(self):
        """Test groupby with full syntax specifying aggregations."""
        csv_data = "category,region,sales,quantity\nElectronics,North,1000,5\nElectronics,South,1500,7\nClothing,North,800,10\nClothing,South,1200,15"
        
        # Run uplt groupby command with full syntax
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category", "sum(sales),avg(quantity)"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "category,sum(sales),avg(quantity)" in lines[0]
        
        # Check aggregated data
        assert len(lines) == 3  # header + 2 categories
        assert "Electronics,2500" in output
        assert "Clothing,2000" in output
        # Check averages
        assert ",6.0" in output or ",6" in output  # Electronics avg quantity
        assert ",12.5" in output  # Clothing avg quantity
    
    def test_groupby_multiple_fields(self):
        """Test groupby with multiple fields."""
        csv_data = "category,region,sales\nElectronics,North,1000\nElectronics,North,500\nElectronics,South,1500\nClothing,North,800"
        
        # Run uplt groupby command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category,region", "sum(sales)"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check results
        assert len(lines) == 4  # header + 3 groups
        assert "Electronics,North,1500" in output
        assert "Electronics,South,1500" in output
        assert "Clothing,North,800" in output
    
    def test_groupby_aggregate_all_shortcut(self):
        """Test groupby with aggregate-all shortcut."""
        csv_data = "category,price,quantity,revenue\nElectronics,100,5,500\nElectronics,150,3,450\nClothing,50,10,500\nClothing,75,8,600"
        
        # Run uplt groupby with 'sum' shortcut
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category", "sum"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - all numeric columns should be summed
        assert "category,price_sum,quantity_sum,revenue_sum" in lines[0]
        
        # Check aggregated data
        assert len(lines) == 3  # header + 2 categories
        assert "Electronics,250,8,950" in output
        assert "Clothing,125,18,1100" in output
    
    def test_groupby_default_avg(self):
        """Test groupby with no aggregation specified (defaults to avg)."""
        csv_data = "category,price,rating\nElectronics,100,4.5\nElectronics,200,4.0\nClothing,50,3.5\nClothing,60,4.5"
        
        # Run uplt groupby without specifying aggregation
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - should default to avg
        assert "category,price_avg,rating_avg" in lines[0]
        
        # Check aggregated data
        assert len(lines) == 3  # header + 2 categories
        assert "Electronics,150" in output or "Electronics,150.0" in output
        assert "Electronics" in output and ",4.25" in output
        assert "Clothing,55" in output or "Clothing,55.0" in output
        assert "Clothing" in output and ",4.0" in output or ",4" in output
    
    def test_groupby_short_alias(self):
        """Test using 'g' as short alias for groupby."""
        csv_data = "type,value\nA,10\nA,20\nB,30\nB,40"
        
        # Run uplt g command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "g", "type", "sum"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check results
        assert len(lines) == 3  # header + 2 types
        assert "type,value_sum" in lines[0]
        assert "A,30" in output
        assert "B,70" in output
    
    def test_groupby_mixed_columns(self):
        """Test groupby with mixed numeric and non-numeric columns."""
        csv_data = "category,description,price,quantity\nElectronics,TV,1000,2\nElectronics,Phone,500,5\nClothing,Shirt,50,10"
        
        # Run uplt groupby - should only aggregate numeric columns
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category", "avg"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - description should be excluded
        assert "category,price_avg,quantity_avg" in lines[0]
        assert "description" not in lines[0]
        
        # Check data
        assert "Electronics,750" in output or "Electronics,750.0" in output
        assert "Electronics" in output and ",3.5" in output
    
    def test_groupby_with_null_values(self):
        """Test groupby handling null values correctly."""
        csv_data = "category,value\nA,10\nA,\nA,20\nB,30\nB,40"
        
        # Run uplt groupby
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category", "avg(value)"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Note: Empty strings in numeric columns are treated as 0 in SQLite
        # So avg for A is (10+0+20)/3 = 10
        assert "A,10" in output or "A,10.0" in output
        assert "B,35" in output or "B,35.0" in output