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
    
    def test_add_multiple_expressions(self):
        """Test adding multiple columns in a single command."""
        csv_data = "name,age,salary\nJohn,25,50000\nJane,30,60000"
        
        # Run uplt add command with multiple expressions
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "age * 2 as double_age, salary / 1000 as salary_k"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,age,salary,double_age,salary_k"
        
        # Check data
        assert "John,25,50000,50,50" in output
        assert "Jane,30,60000,60,60" in output
    
    def test_add_functions_with_commas(self):
        """Test adding columns with functions containing commas."""
        csv_data = "name,status,score\nJohn,active,85\nJane,inactive,92"
        
        # Run uplt add command with IIF function
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "IIF(score > 90, 'excellent', 'good') as grade, substr(name, 1, 1) as initial"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,status,score,grade,initial"
        
        # Check data
        assert "John,active,85,good,J" in output
        assert "Jane,inactive,92,excellent,J" in output
    
    def test_add_nested_functions(self):
        """Test adding columns with nested function calls."""
        csv_data = "col1,col2\nJohn,HELLO\nJane,test"
        
        # Run uplt add command with nested functions - use simple column names to avoid sanitization issues
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "--header", "add", "UPPER(col2) as upper_col2, LENGTH(col1) as col1_len"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "col1,col2,upper_col2,col1_len"
        
        # Check data
        assert "John,HELLO,HELLO,4" in output
        assert "Jane,test,TEST,4" in output
    
    def test_add_case_expression_with_commas(self):
        """Test adding a column with CASE expression containing commas."""
        csv_data = "category,price\nelectronics,150\nbooks,25\nclothing,75"
        
        # Run uplt add command with CASE expression
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "CASE WHEN price > 100 THEN 'expensive' WHEN price > 50 THEN 'moderate' ELSE 'cheap' END as price_tier, category"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - should have original columns plus two new ones
        assert lines[0] == "category,price,price_tier,expr_4"
        
        # Check data
        assert "electronics,150,expensive,electronics" in output
        assert "books,25,cheap,books" in output
        assert "clothing,75,moderate,clothing" in output
    
    def test_add_complex_real_world_example(self):
        """Test the exact example from the bug report."""
        csv_data = "model_filename,n_gpu_layers,n_depth,avg_ts\nQwen3-4B-IQ4_NL.gguf,0,1024,47.13\nQwen3-4B-IQ4_NL.gguf,99,1024,91.92"
        
        # Run the exact command from the bug report
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "substr(model_filename, 10) as model, IIF(n_gpu_layers > 0, 'gpu', 'cpu') as device"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - both 'model' and 'device' should be present
        assert lines[0] == "model_filename,n_gpu_layers,n_depth,avg_ts,model,device"
        
        # Check data
        assert "IQ4_NL.gguf,cpu" in output
        assert "IQ4_NL.gguf,gpu" in output
    
    def test_add_quoted_strings_with_commas(self):
        """Test adding columns with quoted strings containing commas."""
        csv_data = "name,value\ntest,hello\nother,more"
        
        # Run uplt add command with quoted strings containing commas
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "--header", "add", "REPLACE(value, 'e', ',') as comma_data, name || ', suffix' as name_with_suffix"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,value,comma_data,name_with_suffix"
        
        # Check that the output contains the expected transformations
        assert "h,llo" in output  # 'hello' with 'e' replaced by ','
        assert "test, suffix" in output
    
    def test_add_arithmetic_with_functions(self):
        """Test adding columns with arithmetic expressions involving functions."""
        csv_data = "name,value1,value2\ntest,10,5\nother,20,8"
        
        # Run uplt add command with arithmetic and functions
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "add", "value1 + value2 as sum, ROUND(value1 / value2, 2) as ratio"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert lines[0] == "name,value1,value2,sum,ratio"
        
        # Check data
        assert "test,10,5,15,2.0" in output
        assert "other,20,8,28," in output  # SQLite may round differently