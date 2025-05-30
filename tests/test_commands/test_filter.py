"""Test the filter command functionality."""
import subprocess
import sys
import pytest


class TestFilterCommand:
    """Test the filter command functionality."""
    
    def test_filter_simple_condition(self):
        """Test filtering with a simple condition."""
        csv_data = "name,age,salary\nJohn,25,50000\nJane,30,65000\nBob,35,70000"
        
        # Run uplt filter command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "filter", "age > 30"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,age,salary"
        
        # Check filtered data
        assert len(lines) == 2  # header + 1 row
        assert "Bob,35,70000" in output
        assert "John" not in output
        assert "Jane" not in output
    
    def test_filter_string_condition(self):
        """Test filtering with string comparison."""
        csv_data = "name,status,value\nAlice,active,100\nBob,inactive,200\nCarol,active,150"
        
        # Run uplt filter command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "filter", "status = 'active'"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,status,value"
        
        # Check filtered data
        assert len(lines) == 3  # header + 2 rows
        assert "Alice,active,100" in output
        assert "Carol,active,150" in output
        assert "Bob" not in output
    
    def test_filter_complex_condition(self):
        """Test filtering with complex conditions."""
        csv_data = "product,price,quantity\nlaptop,1000,5\nmouse,50,100\nkeyboard,150,20\nmonitor,300,10"
        
        # Run uplt filter command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "filter", "price > 100 AND quantity < 50"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "product,price,quantity"
        
        # Check filtered data
        assert len(lines) == 4  # header + 3 rows
        assert "laptop,1000,5" in output
        assert "keyboard,150,20" in output
        assert "monitor,300,10" in output
        assert "mouse" not in output
    
    def test_filter_with_functions(self):
        """Test filtering with SQLite functions."""
        csv_data = "name,category\nLaptop,ELECTRONICS\nmouse,electronics\nDesk,FURNITURE\nchair,furniture"
        
        # Run uplt filter command with --header flag since all values are strings
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "--header", "filter", "UPPER(category) = 'ELECTRONICS'"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,category"
        
        # Check filtered data
        assert len(lines) == 3  # header + 2 rows
        assert "Laptop,ELECTRONICS" in output
        assert "mouse,electronics" in output
        assert "Desk" not in output
    
    def test_filter_headerless_data(self):
        """Test filtering headerless CSV data."""
        csv_data = "laptop,1000,5\nmouse,50,100\nkeyboard,150,20"
        
        # Run uplt filter command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "filter", "f2 > 100"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check generated headers
        assert lines[0] == "f1,f2,f3"
        
        # Check filtered data
        assert len(lines) == 3  # header + 2 rows
        assert "laptop,1000,5" in output
        assert "keyboard,150,20" in output
        assert "mouse,50,100" not in output
    
    def test_filter_no_matches(self):
        """Test filtering when no rows match."""
        csv_data = "name,age\nJohn,25\nJane,30"
        
        # Run uplt filter command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "filter", "age > 50"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Only headers should be present
        assert len(lines) == 1
        assert lines[0] == "name,age"
    
    def test_filter_short_alias(self):
        """Test using 'f' as short alias for filter."""
        csv_data = "x,y\n1,10\n2,20\n3,30"
        
        # Run uplt f command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "f", "y >= 20"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check results
        assert len(lines) == 3  # header + 2 rows
        assert "x,y" in lines[0]
        assert "2,20" in output
        assert "3,30" in output
        assert "1,10" not in output