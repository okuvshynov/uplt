"""Test the add command functionality."""
import subprocess
import sys
import pytest


class TestAddCommand:
    """Test the add command functionality."""
    
    def test_add_simple_expression(self):
        """Test adding a simple calculated column."""
        csv_data = "item,price,quantity\nlaptop,1000,2\nmouse,50,10"
        
        # Run uplt add command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "price * quantity as total"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "item,price,quantity,total"
        
        # Check data
        assert "laptop,1000,2,2000" in output
        assert "mouse,50,10,500" in output
    
    def test_add_conditional_expression(self):
        """Test adding a column with conditional logic."""
        csv_data = "item,price\nlaptop,1000\nmouse,50"
        
        # Run uplt add command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "case when price > 100 then 'expensive' else 'cheap' end as category"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        
        assert "item,price,category" in output
        assert "laptop,1000,expensive" in output
        assert "mouse,50,cheap" in output
    
    def test_add_headerless_data(self):
        """Test adding a column to headerless CSV data."""
        csv_data = "laptop,1000,2\nmouse,50,10"
        
        # Run uplt add command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "f2 * f3 as total"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check generated headers
        assert lines[0] == "f1,f2,f3,total"
        
        # Check data
        assert "laptop,1000,2,2000" in output
        assert "mouse,50,10,500" in output
    
    def test_add_without_alias(self):
        """Test adding a column without AS alias."""
        csv_data = "a,b\n1,2\n3,4"
        
        # Run uplt add command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "a + b"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - should generate default name
        assert lines[0].startswith("a,b,expr_")
        
        # Check data
        assert ",3" in lines[1]  # 1 + 2 = 3
        assert ",7" in lines[2]  # 3 + 4 = 7
    
    def test_add_with_sqlite_functions(self):
        """Test adding a column using SQLite functions."""
        csv_data = "name,value\nHELLO,100\nworld,200"
        
        # Run uplt add command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "lower(name) as name_lower"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        
        assert "name,value,name_lower" in output
        assert "HELLO,100,hello" in output
        assert "world,200,world" in output
    
    def test_add_short_alias(self):
        """Test using 'a' as short alias for add."""
        csv_data = "x,y\n1,2\n3,4"
        
        # Run uplt a command
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "a", "x * y as product"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        
        assert "x,y,product" in output
        assert "1,2,2" in output
        assert "3,4,12" in output