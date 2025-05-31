import sqlite3
import csv
import io
import re
from typing import List, Any, Optional, Tuple


def split_expressions(expr_string: str) -> List[str]:
    """Split comma-separated expressions while respecting parentheses.
    
    Examples:
        "a, b" -> ["a", "b"]
        "IIF(a > 0, 'yes', 'no'), b" -> ["IIF(a > 0, 'yes', 'no')", "b"]
        "substr(name, 1, 5) as prefix, upper(type) as TYPE" -> ["substr(name, 1, 5) as prefix", "upper(type) as TYPE"]
    """
    expressions = []
    current_expr = ""
    paren_depth = 0
    quote_char = None
    
    i = 0
    while i < len(expr_string):
        char = expr_string[i]
        
        # Handle quotes
        if char in ('"', "'") and quote_char is None:
            quote_char = char
        elif char == quote_char:
            quote_char = None
        
        # Only count parentheses when not inside quotes
        if quote_char is None:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                # This is a top-level comma, split here
                expressions.append(current_expr.strip())
                current_expr = ""
                i += 1
                continue
        
        current_expr += char
        i += 1
    
    # Add the last expression
    if current_expr.strip():
        expressions.append(current_expr.strip())
    
    return expressions


def parse_field_with_alias(field_expr: str) -> Tuple[str, Optional[str]]:
    """Parse a field expression that may contain an AS alias.
    
    Examples:
        "column" -> ("column", None)
        "column as alias" -> ("column", "alias")
        "substr(col, 1, 5) as prefix" -> ("substr(col, 1, 5)", "prefix")
        "UPPER(name) AS NAME" -> ("UPPER(name)", "NAME")
    
    Returns:
        Tuple of (expression, alias) where alias is None if not specified
    """
    # Case-insensitive match for ' as ' or ' AS '
    # Use negative lookbehind to avoid matching 'as' within function names
    as_pattern = re.compile(r'\s+[aA][sS]\s+', re.IGNORECASE)
    
    # Find the last occurrence of ' as ' to handle cases where AS might appear in the expression
    matches = list(as_pattern.finditer(field_expr))
    
    if matches:
        # Use the last match to split
        last_match = matches[-1]
        expression = field_expr[:last_match.start()].strip()
        alias = field_expr[last_match.end():].strip()
        
        # Remove quotes from alias if present
        if alias and len(alias) >= 2:
            if (alias[0] == '"' and alias[-1] == '"') or (alias[0] == "'" and alias[-1] == "'"):
                alias = alias[1:-1]
        
        return (expression, alias)
    
    return (field_expr.strip(), None)


def detect_delimiter(sample: str) -> str:
    """Detect the most likely delimiter in the CSV data."""
    delimiters = [',', ';', '\t', ' ', '|']
    delimiter_counts = {}
    
    # Count occurrences of each delimiter in the first few lines
    lines = sample.split('\n')[:5]  # Check first 5 lines
    for delimiter in delimiters:
        count = sum(line.count(delimiter) for line in lines)
        delimiter_counts[delimiter] = count
    
    # Return the delimiter with the highest count
    return max(delimiter_counts, key=delimiter_counts.get)


def sanitize_column_name(name: str) -> str:
    """Sanitize column names to be valid SQL identifiers."""
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[^\w]', '_', str(name).strip())
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = 'col_' + sanitized
    # Handle empty names
    if not sanitized:
        sanitized = 'unnamed_column'
    return sanitized


def infer_column_type(values: List[Any]) -> str:
    """Infer the SQL column type based on the values."""
    # Remove None/empty values for type inference
    non_empty_values = [v for v in values if v is not None and str(v).strip()]
    
    if not non_empty_values:
        return 'TEXT'
    
    # Check if all values can be integers
    try:
        for val in non_empty_values:
            int(str(val))
        return 'INTEGER'
    except ValueError:
        pass
    
    # Check if all values can be floats
    try:
        for val in non_empty_values:
            float(str(val))
        return 'REAL'
    except ValueError:
        pass
    
    return 'TEXT'


def auto_detect_headers(rows: List[List[str]]) -> bool:
    """Auto-detect if the first row contains headers by comparing numeric field counts.
    
    Args:
        rows: List of CSV rows (at least 2 rows needed)
    
    Returns:
        True if first row likely contains headers, False otherwise
    """
    if len(rows) < 2:
        # Not enough data to detect, assume headers exist
        return True
    
    first_row = rows[0]
    second_row = rows[1]
    
    # Count numeric fields in each row
    def count_numeric_fields(row):
        count = 0
        for field in row:
            field_stripped = field.strip()
            if not field_stripped:
                continue
            try:
                # Try to parse as number
                float(field_stripped)
                count += 1
            except ValueError:
                pass
        return count
    
    first_numeric_count = count_numeric_fields(first_row)
    second_numeric_count = count_numeric_fields(second_row)
    
    # If the second row has significantly more numeric fields than the first,
    # it's likely the first row contains headers
    # Also, if first row has no numeric fields but second row does, likely headers
    if first_numeric_count == 0 and second_numeric_count > 0:
        return True
    
    # If first row has many numeric fields, likely not headers
    if first_numeric_count >= len(first_row) * 0.7:  # 70% or more numeric
        return False
    
    return first_numeric_count < second_numeric_count


def create_table_from_csv(cursor: sqlite3.Cursor, csv_data: str, table_name: str = 'data', header_mode: Optional[str] = None) -> List[str]:
    """Create and populate an SQLite table from CSV data.
    
    Args:
        cursor: SQLite cursor
        csv_data: CSV data as string
        table_name: Name for the created table
        header_mode: 'auto' (default), 'yes', or 'no' for header detection
    
    Returns:
        List of column names
    """
    
    # Detect delimiter
    delimiter = detect_delimiter(csv_data)
    
    # Parse CSV
    csv_reader = csv.reader(io.StringIO(csv_data), delimiter=delimiter)
    
    try:
        # Read all rows first
        all_rows = list(csv_reader)
        
        if not all_rows:
            raise ValueError("No data found in CSV")
        
        # Determine headers and data rows
        if header_mode is None or header_mode == 'auto':
            # Auto-detect headers
            has_headers = auto_detect_headers(all_rows)
        elif header_mode == 'yes':
            has_headers = True
        elif header_mode == 'no':
            has_headers = False
        else:
            raise ValueError(f"Invalid header_mode: {header_mode}")
        
        if not has_headers:
            # Generate column names f1, f2, ..., fn
            num_columns = len(all_rows[0])
            headers = [f"f{i+1}" for i in range(num_columns)]
            rows = all_rows
        else:
            # First row contains headers
            headers = [sanitize_column_name(h) for h in all_rows[0]]
            rows = all_rows[1:]
        
        if not rows:
            raise ValueError("No data rows found in CSV")
        
        # Infer column types
        column_types = []
        for i, header in enumerate(headers):
            column_values = [row[i] if i < len(row) else None for row in rows]
            col_type = infer_column_type(column_values)
            column_types.append(f"{header} {col_type}")
        
        # Create table
        create_sql = f"CREATE TABLE {table_name} ({', '.join(column_types)})"
        cursor.execute(create_sql)
        
        # Insert data
        placeholders = ', '.join(['?' for _ in headers])
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        
        for row in rows:
            # Pad row with None if it has fewer columns than headers
            padded_row = row + [None] * (len(headers) - len(row))
            # Truncate row if it has more columns than headers
            padded_row = padded_row[:len(headers)]
            cursor.execute(insert_sql, padded_row)
        
        return headers
        
    except Exception as e:
        raise ValueError(f"Error parsing CSV: {e}")


def execute_query(cursor: sqlite3.Cursor, query: str) -> List[Tuple]:
    """Execute SQL query and return results."""
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        raise ValueError(f"SQL Error: {e}")


def format_output(results: List[Tuple], description: List[Tuple]) -> str:
    """Format query results as CSV."""
    if not results:
        return ""
    
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    
    # Write headers
    headers = [desc[0] for desc in description]
    writer.writerow(headers)
    
    # Write data
    for row in results:
        writer.writerow(row)
    
    return output.getvalue()