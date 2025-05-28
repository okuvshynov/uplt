import pytest
import sqlite3
from io import StringIO
from uplt.core import (
    detect_delimiter,
    sanitize_column_name,
    infer_column_type,
    create_table_from_csv,
    execute_query,
    format_output,
    auto_detect_headers,
)


class TestAutoDetectHeaders:
    def test_detect_headers_with_text_headers(self):
        # Clear headers with text in first row
        rows = [['name', 'age', 'salary'], ['John', '25', '50000'], ['Jane', '30', '65000']]
        assert auto_detect_headers(rows) == True
    
    def test_detect_no_headers_all_numeric(self):
        # All numeric data
        rows = [['1', '10', '100'], ['2', '20', '200'], ['3', '30', '300']]
        assert auto_detect_headers(rows) == False
    
    def test_detect_headers_mixed_types(self):
        # First row has mix of text/numbers, second row mostly numbers
        rows = [['id', 'value1', 'value2'], ['1', '100', '200'], ['2', '300', '400']]
        assert auto_detect_headers(rows) == True
    
    def test_detect_no_headers_mostly_numeric_first_row(self):
        # First row is 75% numeric
        rows = [['1', '2', '3', 'text'], ['4', '5', '6', 'more'], ['7', '8', '9', 'data']]
        assert auto_detect_headers(rows) == False
    
    def test_detect_headers_empty_values(self):
        # Handle empty values gracefully
        rows = [['', 'header2', ''], ['1', '2', '3'], ['4', '5', '6']]
        assert auto_detect_headers(rows) == True
    
    def test_detect_single_row(self):
        # Not enough data to detect
        rows = [['header1', 'header2', 'header3']]
        assert auto_detect_headers(rows) == True
    
    def test_detect_empty_rows(self):
        # Edge case: empty list
        rows = []
        assert auto_detect_headers(rows) == True


class TestDetectDelimiter:
    def test_comma_delimiter(self):
        sample = "a,b,c\n1,2,3\n4,5,6"
        assert detect_delimiter(sample) == ","
    
    def test_semicolon_delimiter(self):
        sample = "a;b;c\n1;2;3\n4;5;6"
        assert detect_delimiter(sample) == ";"
    
    def test_tab_delimiter(self):
        sample = "a\tb\tc\n1\t2\t3\n4\t5\t6"
        assert detect_delimiter(sample) == "\t"
    
    def test_pipe_delimiter(self):
        sample = "a|b|c\n1|2|3\n4|5|6"
        assert detect_delimiter(sample) == "|"
    
    def test_mixed_delimiters(self):
        # Should pick the most common one
        sample = "a,b;c\n1,2;3\n4,5;6"
        assert detect_delimiter(sample) == ","


class TestSanitizeColumnName:
    def test_normal_name(self):
        assert sanitize_column_name("column_name") == "column_name"
    
    def test_name_with_spaces(self):
        assert sanitize_column_name("column name") == "column_name"
    
    def test_name_with_special_chars(self):
        assert sanitize_column_name("column-name!") == "column_name_"
        assert sanitize_column_name("column@name#") == "column_name_"
    
    def test_name_starting_with_number(self):
        assert sanitize_column_name("123column") == "col_123column"
    
    def test_empty_name(self):
        assert sanitize_column_name("") == "unnamed_column"
        assert sanitize_column_name("   ") == "unnamed_column"
    
    def test_unicode_characters(self):
        # \w in Python regex includes unicode word characters by default
        assert sanitize_column_name("café") == "café"


class TestInferColumnType:
    def test_integer_column(self):
        values = ["1", "2", "3", "4", "5"]
        assert infer_column_type(values) == "INTEGER"
    
    def test_float_column(self):
        values = ["1.5", "2.7", "3.14", "4.0", "5.99"]
        assert infer_column_type(values) == "REAL"
    
    def test_text_column(self):
        values = ["hello", "world", "test", "data"]
        assert infer_column_type(values) == "TEXT"
    
    def test_mixed_numeric_types(self):
        # Integers can be floats, so this should be REAL
        values = ["1", "2.5", "3", "4.7"]
        assert infer_column_type(values) == "REAL"
    
    def test_empty_values(self):
        values = ["", None, "  ", None]
        assert infer_column_type(values) == "TEXT"
    
    def test_integers_with_empty(self):
        values = ["1", "", "3", None, "5"]
        assert infer_column_type(values) == "INTEGER"


class TestCreateTableFromCSV:
    def setup_method(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
    
    def teardown_method(self):
        self.conn.close()
    
    def test_basic_csv(self):
        csv_data = "name,age,salary\nJohn,25,50000\nJane,30,65000"
        headers = create_table_from_csv(self.cursor, csv_data)
        
        assert headers == ["name", "age", "salary"]
        
        # Check table was created
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 2
        
        # Check data types
        self.cursor.execute("PRAGMA table_info(data)")
        columns = self.cursor.fetchall()
        assert columns[0][2] == "TEXT"  # name
        assert columns[1][2] == "INTEGER"  # age
        assert columns[2][2] == "INTEGER"  # salary
    
    def test_custom_table_name(self):
        csv_data = "col1,col2\nval1,val2"
        headers = create_table_from_csv(self.cursor, csv_data, "custom_table", header_mode='yes')
        
        # Check custom table was created
        self.cursor.execute("SELECT COUNT(*) FROM custom_table")
        assert self.cursor.fetchone()[0] == 1
    
    def test_csv_with_special_headers(self):
        csv_data = "First Name,Last-Name,Age (years),2024\nJohn,Doe,25,Yes"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='yes')
        
        assert headers == ["First_Name", "Last_Name", "Age__years_", "col_2024"]
    
    def test_csv_with_missing_values(self):
        csv_data = "a,b,c\n1,2,3\n4,,6\n7,8"
        headers = create_table_from_csv(self.cursor, csv_data)
        
        self.cursor.execute("SELECT * FROM data")
        rows = self.cursor.fetchall()
        assert len(rows) == 3
        # CSV reader returns empty strings for missing values, and types are inferred
        assert rows[1] == (4, '', 6)  # a and c are integers, b is empty string
        assert rows[2] == (7, 8, None)  # Last value is None due to padding
    
    def test_empty_csv_error(self):
        csv_data = "header1,header2"
        with pytest.raises(ValueError, match="No data rows found"):
            create_table_from_csv(self.cursor, csv_data)
    
    def test_no_headers_mode(self):
        csv_data = "John,25,50000\nJane,30,65000\nBob,35,70000"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='no')
        
        # Check generated headers
        assert headers == ["f1", "f2", "f3"]
        
        # Check table was created with all data
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 3
        
        # Check data
        self.cursor.execute("SELECT * FROM data ORDER BY f2")
        rows = self.cursor.fetchall()
        assert rows[0] == ('John', 25, 50000)
        assert rows[1] == ('Jane', 30, 65000)
        assert rows[2] == ('Bob', 35, 70000)
    
    def test_yes_headers_mode(self):
        csv_data = "name,age,salary\nJohn,25,50000\nJane,30,65000"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='yes')
        
        assert headers == ["name", "age", "salary"]
        
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 2
    
    def test_auto_detect_with_headers(self):
        # This should detect headers (first row has text, second row has numbers)
        csv_data = "name,age,salary\nJohn,25,50000\nJane,30,65000"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='auto')
        
        assert headers == ["name", "age", "salary"]
        
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 2
    
    def test_auto_detect_without_headers(self):
        # This should detect no headers (all numeric data)
        csv_data = "1,10,100\n2,20,200\n3,30,300"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='auto')
        
        assert headers == ["f1", "f2", "f3"]
        
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 3
    
    def test_no_headers_single_row(self):
        csv_data = "value1,value2,value3"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='no')
        
        assert headers == ["f1", "f2", "f3"]
        
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 1
        
        self.cursor.execute("SELECT * FROM data")
        assert self.cursor.fetchone() == ('value1', 'value2', 'value3')
    
    def test_no_headers_different_column_counts(self):
        csv_data = "a,b,c,d,e\n1,2,3\n4,5,6,7,8,9,10"
        headers = create_table_from_csv(self.cursor, csv_data, header_mode='no')
        
        # Headers based on first row
        assert headers == ["f1", "f2", "f3", "f4", "f5"]
        
        # All rows should be present
        self.cursor.execute("SELECT COUNT(*) FROM data")
        assert self.cursor.fetchone()[0] == 3


class TestExecuteQuery:
    def setup_method(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        # Create a test table
        self.cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        self.cursor.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")
    
    def teardown_method(self):
        self.conn.close()
    
    def test_select_query(self):
        results = execute_query(self.cursor, "SELECT * FROM test")
        assert len(results) == 2
        assert results[0] == (1, 'Alice')
        assert results[1] == (2, 'Bob')
    
    def test_aggregate_query(self):
        results = execute_query(self.cursor, "SELECT COUNT(*) FROM test")
        assert results[0][0] == 2
    
    def test_invalid_query(self):
        with pytest.raises(ValueError, match="SQL Error"):
            execute_query(self.cursor, "SELECT * FROM nonexistent")
    
    def test_syntax_error(self):
        with pytest.raises(ValueError, match="SQL Error"):
            execute_query(self.cursor, "SELCT * FROM test")


class TestSQLiteFunctions:
    """Test SQLite function support in queries and field arguments."""
    
    def setup_method(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        # Create test table with various data types
        self.cursor.execute("""
            CREATE TABLE products (
                id INTEGER,
                name TEXT,
                category TEXT,
                price REAL,
                quantity INTEGER,
                description TEXT,
                created_date TEXT
            )
        """)
        
        # Insert test data
        test_data = [
            (1, 'laptop', 'electronics', 999.99, 10, 'High-end laptop', '2024-01-15'),
            (2, 'MOUSE', 'electronics', 29.99, 50, 'Wireless mouse', '2024-01-20'),
            (3, 'Desk Chair', 'furniture', 299.50, 15, 'Ergonomic office chair', '2024-02-01'),
            (4, 'notebook', 'stationery', 5.99, 100, 'Spiral notebook', '2024-02-10'),
            (5, 'MONITOR', 'electronics', 399.00, 25, 'LED monitor 27"', '2024-02-15'),
            (6, 'desk lamp', 'furniture', 49.99, 30, 'Adjustable desk lamp', '2024-03-01'),
            (7, 'keyboard', 'electronics', -89.99, 20, 'Mechanical keyboard', '2024-03-05'),  # negative price for abs() test
        ]
        
        self.cursor.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            test_data
        )
    
    def teardown_method(self):
        self.conn.close()
    
    def test_string_functions_upper_lower(self):
        # Test UPPER function
        results = execute_query(self.cursor, "SELECT name, UPPER(name) FROM products WHERE id = 2")
        assert results[0] == ('MOUSE', 'MOUSE')
        
        # Test LOWER function
        results = execute_query(self.cursor, "SELECT name, LOWER(name) FROM products WHERE id = 3")
        assert results[0] == ('Desk Chair', 'desk chair')
    
    def test_string_function_substr(self):
        # Test SUBSTR function
        results = execute_query(self.cursor, "SELECT name, SUBSTR(name, 1, 4) FROM products WHERE id = 1")
        assert results[0] == ('laptop', 'lapt')
        
        # Test SUBSTR with negative position
        results = execute_query(self.cursor, "SELECT name, SUBSTR(name, -3) FROM products WHERE id = 4")
        assert results[0] == ('notebook', 'ook')
    
    def test_string_function_length(self):
        # Test LENGTH function
        results = execute_query(self.cursor, "SELECT name, LENGTH(name) FROM products ORDER BY id LIMIT 3")
        assert results[0] == ('laptop', 6)
        assert results[1] == ('MOUSE', 5)
        assert results[2] == ('Desk Chair', 10)
    
    def test_string_function_trim(self):
        # Insert data with spaces
        self.cursor.execute("INSERT INTO products VALUES (8, '  spaced  ', 'test', 10, 1, 'test', '2024-04-01')")
        
        # Test TRIM function
        results = execute_query(self.cursor, "SELECT name, TRIM(name) FROM products WHERE id = 8")
        assert results[0] == ('  spaced  ', 'spaced')
    
    def test_numeric_functions_abs_round(self):
        # Test ABS function
        results = execute_query(self.cursor, "SELECT price, ABS(price) FROM products WHERE id = 7")
        assert results[0] == (-89.99, 89.99)
        
        # Test ROUND function
        results = execute_query(self.cursor, "SELECT price, ROUND(price) FROM products WHERE id = 1")
        assert results[0] == (999.99, 1000.0)
        
        # Test ROUND with precision
        results = execute_query(self.cursor, "SELECT price, ROUND(price, 1) FROM products WHERE id = 3")
        assert results[0] == (299.50, 299.5)
    
    def test_aggregate_with_string_functions(self):
        # Test COUNT with UPPER
        results = execute_query(self.cursor, 
            "SELECT COUNT(DISTINCT UPPER(category)) FROM products")
        assert results[0][0] == 3  # electronics, furniture, stationery
        
        # Test MAX with LENGTH
        results = execute_query(self.cursor,
            "SELECT MAX(LENGTH(name)) FROM products")
        assert results[0][0] == 10  # 'Desk Chair' has length 10
    
    def test_aggregate_with_numeric_functions(self):
        # Test SUM with ABS
        results = execute_query(self.cursor,
            "SELECT SUM(ABS(price)) FROM products WHERE category = 'electronics'")
        # laptop: 999.99, mouse: 29.99, monitor: 399.00, keyboard: 89.99 (abs)
        expected = 999.99 + 29.99 + 399.00 + 89.99
        assert abs(results[0][0] - expected) < 0.01
        
        # Test AVG with ROUND
        results = execute_query(self.cursor,
            "SELECT AVG(ROUND(price)) FROM products WHERE category = 'furniture'")
        # desk chair: 300, desk lamp: 50, avg = 175
        assert results[0][0] == 175.0
    
    def test_case_expression(self):
        # Test CASE expression
        results = execute_query(self.cursor, """
            SELECT name, 
                   CASE 
                       WHEN price < 50 THEN 'cheap'
                       WHEN price < 300 THEN 'medium'
                       ELSE 'expensive'
                   END as price_category
            FROM products
            ORDER BY id
            LIMIT 4
        """)
        assert results[0] == ('laptop', 'expensive')
        assert results[1] == ('MOUSE', 'cheap')
        assert results[2] == ('Desk Chair', 'medium')
        assert results[3] == ('notebook', 'cheap')
    
    def test_complex_expressions(self):
        # Test arithmetic operations
        results = execute_query(self.cursor,
            "SELECT name, price * quantity as total_value FROM products WHERE id = 1")
        assert results[0] == ('laptop', 9999.9)
        
        # Test concatenation
        results = execute_query(self.cursor,
            "SELECT name || ' - ' || category as full_name FROM products WHERE id = 2")
        assert results[0] == ('MOUSE - electronics',)
    
    def test_group_by_with_functions(self):
        # Test GROUP BY with UPPER to normalize case
        results = execute_query(self.cursor, """
            SELECT UPPER(category) as cat, COUNT(*) as cnt, AVG(price) as avg_price
            FROM products
            GROUP BY UPPER(category)
            ORDER BY cat
        """)
        assert len(results) == 3
        assert results[0][0] == 'ELECTRONICS'  # normalized to uppercase
        assert results[0][1] == 4  # count of electronics
    
    def test_where_clause_with_functions(self):
        # Test WHERE with string function
        results = execute_query(self.cursor,
            "SELECT name FROM products WHERE LOWER(name) LIKE '%desk%'")
        assert len(results) == 2
        assert ('Desk Chair',) in results
        assert ('desk lamp',) in results
        
        # Test WHERE with numeric function
        results = execute_query(self.cursor,
            "SELECT name FROM products WHERE ABS(price) > 100")
        assert len(results) == 3  # laptop, desk chair, monitor
    
    def test_order_by_with_functions(self):
        # Test ORDER BY with LENGTH
        results = execute_query(self.cursor,
            "SELECT name FROM products ORDER BY LENGTH(name) LIMIT 3")
        assert results[0] == ('MOUSE',)  # length 5
        assert results[1] == ('laptop',)  # length 6
        
        # Test ORDER BY with expression
        results = execute_query(self.cursor,
            "SELECT name, price * quantity as total FROM products ORDER BY price * quantity DESC LIMIT 2")
        assert results[0][0] == 'laptop'  # highest total value
        assert results[1][0] == 'MONITOR'  # second highest


class TestFormatOutput:
    def test_basic_formatting(self):
        results = [(1, 'Alice'), (2, 'Bob')]
        description = [('id',), ('name',)]
        
        output = format_output(results, description)
        # Use splitlines() to handle different line endings properly
        lines = output.strip().splitlines()
        
        assert lines[0] == "id,name"
        assert lines[1] == "1,Alice"
        assert lines[2] == "2,Bob"
    
    def test_empty_results(self):
        results = []
        description = [('id',), ('name',)]
        
        output = format_output(results, description)
        assert output == ""
    
    def test_values_with_commas(self):
        results = [('John, Jr.', 'Doe')]
        description = [('first_name',), ('last_name',)]
        
        output = format_output(results, description)
        lines = output.strip().splitlines()
        
        assert lines[0] == "first_name,last_name"
        assert lines[1] == '"John, Jr.",Doe'
    
    def test_numeric_values(self):
        results = [(1, 2.5, 'test')]
        description = [('int_col',), ('float_col',), ('text_col',)]
        
        output = format_output(results, description)
        lines = output.strip().splitlines()
        
        assert lines[0] == "int_col,float_col,text_col"
        assert lines[1] == "1,2.5,test"


class TestAddCommand:
    """Test the add command functionality."""
    
    def test_add_simple_expression(self):
        """Test adding a simple calculated column."""
        import subprocess
        import sys
        
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
        lines = output.split('\n')
        
        # Check headers
        assert lines[0] == "item,price,quantity,total"
        
        # Check data
        assert "laptop,1000,2,2000" in output
        assert "mouse,50,10,500" in output
    
    def test_add_conditional_expression(self):
        """Test adding a column with conditional logic."""
        import subprocess
        import sys
        
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
        import subprocess
        import sys
        
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
        lines = output.split('\n')
        
        # Check generated headers
        assert lines[0] == "f1,f2,f3,total"
        
        # Check data
        assert "laptop,1000,2,2000" in output
        assert "mouse,50,10,500" in output
    
    def test_add_without_alias(self):
        """Test adding a column without AS alias."""
        import subprocess
        import sys
        
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
        lines = output.split('\n')
        
        # Check headers - should generate default name
        assert lines[0].startswith("a,b,expr_")
        
        # Check data
        assert ",3" in lines[1]  # 1 + 2 = 3
        assert ",7" in lines[2]  # 3 + 4 = 7
    
    def test_add_with_sqlite_functions(self):
        """Test adding a column using SQLite functions."""
        import subprocess
        import sys
        
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