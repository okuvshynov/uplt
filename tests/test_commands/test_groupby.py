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
    
    def test_groupby_with_alias(self):
        """Test groupby with AS aliases for columns."""
        csv_data = "timestamp,category,value\n20240101_120000,Electronics,100\n20240101_130000,Electronics,150\n20240102_140000,Clothing,50"
        
        # Run uplt groupby with aliased fields
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "substr(timestamp,1,8) as day,category", "sum(value) as total"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers with aliases
        assert "day,category,total" in lines[0]
        
        # Check data
        assert "20240101,Electronics,250" in output
        assert "20240102,Clothing,50" in output
    
    def test_groupby_multiple_aliases(self):
        """Test groupby with multiple aliased fields and aggregations."""
        csv_data = "endpoint,model,latency,errors\n/api/v1/predict,test1,100,0\n/api/v1/predict,test1,150,1\n/api/v2/predict,test2,80,0"
        
        # Run uplt groupby with multiple aliases
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", 
             "substr(endpoint,-7) as api_version,model as model_name", 
             "avg(latency) as avg_latency,sum(errors) as total_errors"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check aliased headers
        assert "api_version,model_name,avg_latency,total_errors" in lines[0]
        
        # Check data
        assert "predict,test1,125" in output or "predict,test1,125.0" in output
        assert "predict,test1" in output and ",1" in output
        assert "predict,test2,80" in output or "predict,test2,80.0" in output
    
    def test_groupby_alias_with_shortcut(self):
        """Test groupby with aliases and aggregate-all shortcuts."""
        csv_data = "date,store_id,sales,returns\n2024-01-01,S001,1000,50\n2024-01-01,S002,1500,75\n2024-01-02,S001,1200,60"
        
        # Run uplt groupby with alias and sum shortcut
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "substr(date,1,7) as month", "sum"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - month alias should be used
        assert "month,sales_sum,returns_sum" in lines[0]
        
        # Check aggregated data
        assert "2024-01,3700,185" in output
    
    def test_groupby_mixed_alias_no_alias(self):
        """Test groupby with mix of aliased and non-aliased fields."""
        csv_data = "region,category,revenue\nNorth,Electronics,1000\nNorth,Clothing,500\nSouth,Electronics,1500"
        
        # Run uplt groupby with one aliased field
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "upper(region) as REGION,category", "sum(revenue)"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "REGION,category,sum(revenue)" in lines[0]
        
        # Check transformed data
        assert "NORTH,Electronics,1000" in output
        assert "NORTH,Clothing,500" in output
        assert "SOUTH,Electronics,1500" in output
    
    def test_groupby_with_iif_function(self):
        """Test groupby with IIF function containing commas."""
        csv_data = "name,status,score\nJohn,active,85\nJane,active,92\nBob,inactive,78\nAlice,inactive,88"
        
        # Run uplt groupby with IIF function
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "IIF(score > 90, 'excellent', 'good') as grade, status", "count(*) as count"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "grade,status,count" in lines[0]
        
        # Check data
        assert "excellent,active,1" in output  # Jane
        assert "good,active,1" in output       # John
        assert "good,inactive,2" in output     # Bob and Alice
    
    def test_groupby_with_case_expression(self):
        """Test groupby with CASE expression containing commas."""
        csv_data = "category,price,quantity\nelectronics,150,5\nbooks,25,10\nclothing,75,3\nelectronics,200,2"
        
        # Run uplt groupby with CASE expression
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", 
             "CASE WHEN price > 100 THEN 'expensive' WHEN price > 50 THEN 'moderate' ELSE 'cheap' END as price_tier", 
             "sum(quantity) as total_quantity"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "price_tier,total_quantity" in lines[0]
        
        # Check data
        assert "expensive,7" in output   # electronics items > 100
        assert "moderate,3" in output    # clothing item between 50-100
        assert "cheap,10" in output      # books item < 50
    
    def test_groupby_nested_functions_with_commas(self):
        """Test groupby with nested functions containing commas."""
        csv_data = "model_filename,n_gpu_layers,latency\nQwen3-4B-IQ4_NL.gguf,0,47.13\nQwen3-4B-IQ4_NL.gguf,99,91.92\nQwen3-4B-IQ4_XS.gguf,0,48.34"
        
        # Run uplt groupby with nested functions - same pattern as the bug report
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", 
             "substr(model_filename, 10) as model, IIF(n_gpu_layers > 0, 'gpu', 'cpu') as device", 
             "avg(latency) as avg_latency"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers - both 'model' and 'device' should be present
        assert "model,device,avg_latency" in lines[0]
        
        # Check data
        assert "IQ4_NL.gguf,cpu,47.13" in output
        assert "IQ4_NL.gguf,gpu,91.92" in output
        assert "IQ4_XS.gguf,cpu,48.34" in output
    
    def test_groupby_multiple_complex_aggregations(self):
        """Test groupby with multiple complex aggregation expressions containing commas."""
        csv_data = "product,category,sales,returns,cost\nlaptop,electronics,1000,50,800\nphone,electronics,800,20,600\nshirt,clothing,100,5,60"
        
        # Run uplt groupby with multiple complex aggregations
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", "category", 
             "SUM(sales - cost) as profit, AVG(returns * 100.0 / sales) as return_rate, COUNT(*) as products"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "category,profit,return_rate,products" in lines[0]
        
        # Check data for electronics: profit = (1000-800) + (800-600) = 400, return_rate = avg(5.0, 2.5) = 3.75
        assert "electronics,400" in output
        assert "electronics" in output and ",2" in output  # 2 products
        # Check clothing: profit = 100-60 = 40, return_rate = 5.0
        assert "clothing,40" in output
        assert "clothing" in output and ",1" in output  # 1 product
    
    def test_groupby_quoted_strings_with_commas(self):
        """Test groupby with expressions containing quoted strings with commas."""
        csv_data = "name,status,value\ntest_active,active,100\ntest_inactive,inactive,50\nother_active,active,75"
        
        # Run uplt groupby with REPLACE function containing comma in quoted string
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", 
             "REPLACE(status, 'active', 'on') as new_status", 
             "sum(value) as total"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "new_status,total" in lines[0]
        
        # Check data
        assert "on,175" in output      # active -> on, sum = 100 + 75
        assert "inon,50" in output     # inactive -> inon (replace 'active' with 'on')
    
    def test_groupby_arithmetic_in_grouping(self):
        """Test groupby with arithmetic expressions in grouping fields."""
        csv_data = "item,price,quantity,discount\nlaptop,1000,2,10\nphone,800,5,5\nmouse,50,10,0"
        
        # Run uplt groupby with arithmetic in grouping
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", 
             "ROUND(price / 100, 0) * 100 as price_tier", 
             "sum(quantity) as total_qty, avg(discount) as avg_discount"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "price_tier,total_qty,avg_discount" in lines[0]
        
        # Check data - items grouped by price tier (rounded to hundreds)
        assert "1000.0,2" in output  # laptop: ROUND(1000/100) * 100 = 1000
        assert "800.0,5" in output   # phone: ROUND(800/100) * 100 = 800  
        assert "0.0,10" in output    # mouse: ROUND(50/100) * 100 = 0
    
    def test_groupby_complex_string_functions(self):
        """Test groupby with complex string manipulation functions."""
        csv_data = "endpoint,method,response_time\n/api/v1/users,GET,150\n/api/v1/orders,POST,200\n/api/v2/users,GET,120\n/api/v2/orders,POST,180"
        
        # Run uplt groupby with complex string functions
        proc = subprocess.run(
            [sys.executable, "-m", "uplt", "groupby", 
             "UPPER(substr(endpoint, INSTR(endpoint, '/v') + 1, 2)) as version, method", 
             "avg(response_time) as avg_time"],
            input=csv_data,
            capture_output=True,
            text=True
        )
        
        assert proc.returncode == 0
        output = proc.stdout.strip()
        lines = output.splitlines()
        
        # Check headers
        assert "version,method,avg_time" in lines[0]
        
        # Check data
        assert "V1,GET,150" in output
        assert "V1,POST,200" in output  
        assert "V2,GET,120" in output
        assert "V2,POST,180" in output