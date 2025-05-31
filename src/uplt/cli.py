import sys
import sqlite3
import argparse
from .core import create_table_from_csv, execute_query, format_output, parse_field_with_alias, split_expressions
from .query_builder import parse_chart_command


def main():
    parser = argparse.ArgumentParser(
        description='Execute SQL queries on CSV data from stdin or create terminal charts',
        epilog='Examples:\n'
               '  SQL query: cat data.csv | uplt query "SELECT * FROM data"\n'
               '  SQL query (short): cat data.csv | uplt q "SELECT * FROM data"\n'
               '  Add column: cat data.csv | uplt add "price * quantity as total"\n'
               '  Add column (short): cat data.csv | uplt a "if(price > 100, 1, 0) as expensive"\n'
               '  Filter rows: cat data.csv | uplt filter "price > 100"\n'
               '  Filter rows (short): cat data.csv | uplt f "status = \'active\'"\n'
               '  Group by: cat data.csv | uplt groupby "category,region" "avg(price),sum(quantity)"\n'
               '  Group by (short): cat data.csv | uplt g category avg\n'
               '  Heatmap: cat data.csv | uplt heatmap x_field y_field "avg(value)"\n'
               '  Heatmap (short): cat data.csv | uplt hm x_field y_field "avg(value)"\n'
               '  Comparison (2+ versions): cat data.csv | uplt mcmp versions metrics "avg(value)"\n'
               '  Comparison (short): cat data.csv | uplt cmp versions metrics "avg(value)"\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Make command positional but with nargs='*' to handle variable arguments
    parser.add_argument('command', nargs='*', 
                       help='Command: "query"/"q" for SQL or chart type (e.g., "heatmap"/"hm")')
    parser.add_argument('--table-name', '-t', default='data', 
                       help='Name for the SQLite table (default: data)')
    parser.add_argument('--delimiter', '-d', 
                       help='CSV delimiter (auto-detected if not specified)')
    # Create mutually exclusive group for header options
    header_group = parser.add_mutually_exclusive_group()
    header_group.add_argument('--header', action='store_true',
                             help='Force treating first row as headers')
    header_group.add_argument('--no-header', action='store_true',
                             help='Force treating first row as data')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show additional information')
    parser.add_argument('--display-mode', '-m', default='value-percent',
                       help='Display mode for comparison charts: value-percent (default), full, compact, value, diff, percent, value-diff')
    parser.add_argument('--baseline', '-b',
                       help='Baseline version for multi-comparison (defaults to first version)')
    
    args = parser.parse_args()
    
    # Handle backward compatibility: if no command specified, treat as raw SQL
    if not args.command:
        print("Error: No command specified. Use 'query' for SQL or a chart type.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    try:
        # Read CSV data from stdin
        if sys.stdin.isatty():
            print("Error: No input data. Please pipe CSV data to this script.", file=sys.stderr)
            print("Example: cat data.csv | uplt \"SELECT * FROM data\"", file=sys.stderr)
            sys.exit(1)
        
        csv_data = sys.stdin.read().strip()
        
        if not csv_data:
            print("Error: No input data received.", file=sys.stderr)
            sys.exit(1)
        
        # Create in-memory SQLite database
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Create and populate table
        if args.verbose:
            print(f"Creating table '{args.table_name}'...", file=sys.stderr)
        
        # Determine header mode
        if args.header:
            header_mode = 'yes'
        elif args.no_header:
            header_mode = 'no'
        else:
            header_mode = 'auto'
        
        headers = create_table_from_csv(cursor, csv_data, args.table_name, header_mode)
        
        if args.verbose:
            print(f"Table created with columns: {', '.join(headers)}", file=sys.stderr)
            cursor.execute(f"SELECT COUNT(*) FROM {args.table_name}")
            count = cursor.fetchone()[0]
            print(f"Loaded {count} rows", file=sys.stderr)
        
        # Determine mode and execute
        command_type = args.command[0]
        
        # Map short versions to full commands
        # Note: 'cmp' and 'comparison' now both map to 'multi-comparison'
        command_aliases = {
            'q': 'query',
            'a': 'add',
            'f': 'filter',
            'g': 'groupby',
            'hm': 'heatmap',
            'cmp': 'multi-comparison',  # Deprecated: now maps to multi-comparison
            'comparison': 'multi-comparison',  # Deprecated: now maps to multi-comparison
            'mcmp': 'multi-comparison'
        }
        command_type = command_aliases.get(command_type, command_type)
        
        if command_type == "query":
            # Raw SQL mode
            if len(args.command) < 2:
                print("Error: SQL query required after 'query'", file=sys.stderr)
                sys.exit(1)
            
            query = args.command[1]
            results = execute_query(cursor, query)
            
            # Output results as CSV
            if results:
                output = format_output(results, cursor.description)
                print(output, end='')
            elif args.verbose:
                print("Query returned no results.", file=sys.stderr)
        
        elif command_type == "add":
            # Add column mode
            if len(args.command) < 2:
                print("Error: Column expression required after 'add'", file=sys.stderr)
                sys.exit(1)
            
            column_expr = args.command[1]
            
            # Get original column names
            original_columns = headers
            
            # Build query to select all columns plus the new one
            query = f"SELECT *, {column_expr} FROM {args.table_name}"
            
            if args.verbose:
                print(f"Generated query: {query}", file=sys.stderr)
            
            results = execute_query(cursor, query)
            
            # Output results as CSV with headers
            if results:
                # Parse multiple column expressions (comma-separated, respecting parentheses)
                raw_expressions = split_expressions(column_expr)
                new_column_names = []
                
                for i, expr in enumerate(raw_expressions):
                    expr_parsed, alias = parse_field_with_alias(expr)
                    if alias:
                        new_column_names.append(alias)
                    else:
                        # Default name if no alias provided
                        new_column_names.append(f"expr_{len(original_columns)+i+1}")
                
                # Output headers
                all_headers = original_columns + new_column_names
                print(','.join(all_headers))
                
                # Output data
                for row in results:
                    # Format each value appropriately
                    formatted_values = []
                    for val in row:
                        if val is None:
                            formatted_values.append('')
                        elif isinstance(val, str) and (',' in val or '"' in val or '\n' in val):
                            # Escape quotes and wrap in quotes if needed
                            escaped = val.replace('"', '""')
                            formatted_values.append(f'"{escaped}"')
                        else:
                            formatted_values.append(str(val))
                    print(','.join(formatted_values))
            elif args.verbose:
                print("Query returned no results.", file=sys.stderr)
        
        elif command_type == "filter":
            # Filter rows mode
            if len(args.command) < 2:
                print("Error: Filter expression required after 'filter'", file=sys.stderr)
                sys.exit(1)
            
            filter_expr = args.command[1]
            
            # Build query to select all rows that match the filter
            query = f"SELECT * FROM {args.table_name} WHERE {filter_expr}"
            
            if args.verbose:
                print(f"Generated query: {query}", file=sys.stderr)
            
            results = execute_query(cursor, query)
            
            # Always output headers for filter command
            print(','.join(headers))
            
            # Output data if any results
            if results:
                for row in results:
                    # Format each value appropriately
                    formatted_values = []
                    for val in row:
                        if val is None:
                            formatted_values.append('')
                        elif isinstance(val, str) and (',' in val or '"' in val or '\n' in val):
                            # Escape quotes and wrap in quotes if needed
                            escaped = val.replace('"', '""')
                            formatted_values.append(f'"{escaped}"')
                        else:
                            formatted_values.append(str(val))
                    print(','.join(formatted_values))
            elif args.verbose:
                print("Filter returned no matching rows.", file=sys.stderr)
        
        elif command_type == "groupby":
            # Group by mode
            if len(args.command) < 2:
                print("Error: Group by fields required after 'groupby'", file=sys.stderr)
                sys.exit(1)
            
            # Parse group by fields (comma-separated, respecting parentheses)
            raw_groupby_fields = split_expressions(args.command[1])
            
            # Parse each field for potential aliases
            groupby_fields = []
            groupby_expressions = []
            for field in raw_groupby_fields:
                expr, alias = parse_field_with_alias(field)
                groupby_expressions.append(expr)
                if alias:
                    groupby_fields.append(f"{expr} as {alias}")
                else:
                    groupby_fields.append(expr)
            
            # Parse aggregations if provided
            if len(args.command) >= 3:
                agg_spec = args.command[2]
                
                # Check if it's a shortcut (single function name like 'avg', 'sum', etc.)
                if agg_spec.lower() in ['avg', 'sum', 'min', 'max', 'count']:
                    # Aggregate all numeric columns with the same function
                    agg_func = agg_spec.lower()
                    
                    # Find numeric columns (excluding groupby fields)
                    numeric_columns = []
                    for col in headers:
                        if col not in groupby_expressions:
                            # Check if column has numeric values
                            check_query = f"SELECT {col} FROM {args.table_name} WHERE {col} IS NOT NULL LIMIT 10"
                            sample_results = execute_query(cursor, check_query)
                            if sample_results:
                                # Check if values are numeric
                                is_numeric = True
                                for row in sample_results:
                                    try:
                                        float(row[0])
                                    except (ValueError, TypeError):
                                        is_numeric = False
                                        break
                                if is_numeric:
                                    numeric_columns.append(col)
                    
                    if not numeric_columns:
                        print("Error: No numeric columns found to aggregate", file=sys.stderr)
                        sys.exit(1)
                    
                    # Build aggregation expressions
                    agg_expressions = [f"{agg_func}({col}) as {col}_{agg_func}" for col in numeric_columns]
                else:
                    # Full syntax: parse comma-separated aggregation expressions
                    raw_agg_expressions = split_expressions(agg_spec)
                    # Parse each aggregation expression for potential aliases
                    agg_expressions = []
                    for agg_expr in raw_agg_expressions:
                        expr, alias = parse_field_with_alias(agg_expr)
                        if alias:
                            agg_expressions.append(f"{expr} as {alias}")
                        else:
                            agg_expressions.append(expr)
            else:
                # No aggregation specified - default to avg on all numeric columns
                agg_func = 'avg'
                
                # Find numeric columns (excluding groupby fields)
                numeric_columns = []
                for col in headers:
                    if col not in groupby_expressions:
                        # Check if column has numeric values
                        check_query = f"SELECT {col} FROM {args.table_name} WHERE {col} IS NOT NULL LIMIT 10"
                        sample_results = execute_query(cursor, check_query)
                        if sample_results:
                            # Check if values are numeric
                            is_numeric = True
                            for row in sample_results:
                                try:
                                    float(row[0])
                                except (ValueError, TypeError):
                                    is_numeric = False
                                    break
                            if is_numeric:
                                numeric_columns.append(col)
                
                if not numeric_columns:
                    print("Error: No numeric columns found to aggregate", file=sys.stderr)
                    sys.exit(1)
                
                # Build aggregation expressions
                agg_expressions = [f"{agg_func}({col}) as {col}_{agg_func}" for col in numeric_columns]
            
            # Build the GROUP BY query
            select_parts = groupby_fields + agg_expressions
            query = f"SELECT {', '.join(select_parts)} FROM {args.table_name} GROUP BY {', '.join(groupby_expressions)} ORDER BY {', '.join(groupby_expressions)}"
            
            if args.verbose:
                print(f"Generated query: {query}", file=sys.stderr)
                print(f"Numeric columns found: {', '.join(numeric_columns) if 'numeric_columns' in locals() else 'N/A'}", file=sys.stderr)
            
            results = execute_query(cursor, query)
            
            # Output results as CSV
            if results:
                output = format_output(results, cursor.description)
                print(output, end='')
            elif args.verbose:
                print("Query returned no results.", file=sys.stderr)
        
        else:
            # Chart mode
            try:
                # Create modified command list with mapped chart type
                mapped_command = [command_type] + args.command[1:]
                chart_type, options = parse_chart_command(mapped_command)
                
                # Build appropriate query based on chart type
                if chart_type == "heatmap":
                    # Import here to avoid circular dependency
                    from .charts import create_heatmap
                    
                    chart = create_heatmap(
                        cursor,
                        options["x_field"],
                        options["y_field"],
                        options["value_field"],
                        args.table_name,
                        verbose=args.verbose
                    )
                    
                    if chart:
                        print(chart)
                    else:
                        print("No data to plot.", file=sys.stderr)
                elif chart_type == "multi-comparison":
                    # Import here to avoid circular dependency
                    from .charts import create_multi_comparison
                    
                    chart = create_multi_comparison(
                        cursor,
                        options["versions_field"],
                        options["metrics_field"],
                        options["value_field"],
                        args.table_name,
                        verbose=args.verbose,
                        display_mode=args.display_mode,
                        baseline=args.baseline
                    )
                    
                    if chart:
                        print(chart)
                    else:
                        print("No data to compare.", file=sys.stderr)
                else:
                    print(f"Chart type '{chart_type}' not yet implemented", file=sys.stderr)
                    sys.exit(1)
                    
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
