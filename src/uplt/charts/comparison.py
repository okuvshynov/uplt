"""Comparison chart implementation."""
import sqlite3
import sys
from typing import Optional


def create_comparison(
    cursor: sqlite3.Cursor,
    versions_field: str,
    metrics_field: str, 
    value_field: Optional[str],
    table_name: str,
    verbose: bool = False
) -> Optional[str]:
    """
    Create a comparison chart showing differences between versions.
    
    Args:
        cursor: Database cursor
        versions_field: Field containing version identifiers (typically 2 distinct values)
        metrics_field: Field containing metric names (rows in output)
        value_field: Optional field to aggregate (defaults to COUNT)
        table_name: Name of the table
        verbose: Whether to show additional debug info
    
    Returns:
        Formatted comparison chart as string
    """
    from ..query_builder import parse_aggregation
    from ..core import execute_query
    
    # Parse the aggregation function if provided
    if value_field:
        agg_func, field_name = parse_aggregation(value_field)
        if agg_func:
            value_expr = f"{agg_func.upper()}({field_name})"
        else:
            value_expr = value_field
    else:
        value_expr = "COUNT(*)"
        agg_func = "count"
    
    # First, get distinct versions
    version_query = f"""
    SELECT DISTINCT {versions_field}
    FROM {table_name}
    WHERE {versions_field} IS NOT NULL
    ORDER BY {versions_field}
    """
    
    try:
        version_results = execute_query(cursor, version_query)
        if not version_results:
            return "No versions found"
        
        versions = [row[0] for row in version_results]
        
        if len(versions) != 2:
            if verbose:
                print(f"Warning: Expected 2 versions but found {len(versions)}: {versions}", file=sys.stderr)
        
        # For now, handle only the first 2 versions
        if len(versions) < 2:
            return "Need at least 2 versions to compare"
        
        version_a = versions[0]
        version_b = versions[1]
        
        # Get all metrics and their values for both versions
        data_query = f"""
        SELECT 
            {metrics_field} as metric,
            {versions_field} as version,
            {value_expr} as value
        FROM {table_name}
        WHERE {versions_field} IN (?, ?)
            AND {metrics_field} IS NOT NULL
        GROUP BY {metrics_field}, {versions_field}
        ORDER BY {metrics_field}, {versions_field}
        """
        
        if verbose:
            print(f"Generated query: {data_query}", file=sys.stderr)
            print(f"Parameters: [{version_a}, {version_b}]", file=sys.stderr)
        
        cursor.execute(data_query, (version_a, version_b))
        results = cursor.fetchall()
        
        if not results:
            return "No data to compare"
        
        # Organize data by metric
        metric_data = {}
        for metric, version, value in results:
            if metric not in metric_data:
                metric_data[metric] = {}
            metric_data[metric][version] = value
        
        # Print data points in verbose mode
        if verbose:
            print("\nData points:", file=sys.stderr)
            for metric in sorted(metric_data.keys()):
                print(f"  {metric}:", file=sys.stderr)
                for version, value in sorted(metric_data[metric].items()):
                    value_str = f"{value:.6g}" if isinstance(value, (int, float)) else str(value)
                    print(f"    {version}: {value_str}", file=sys.stderr)
            print(file=sys.stderr)
        
        # Build the comparison table
        lines = []
        
        # Add version labels at the top
        lines.append(f"A: {version_a}")
        lines.append(f"B: {version_b}")
        lines.append("")
        
        # Calculate column widths
        metric_width = max(len(str(metric)) for metric in metric_data.keys())
        metric_width = max(metric_width, 7)  # Minimum width for header
        
        # Determine value widths
        a_values = []
        b_values = []
        for metric in metric_data.values():
            if version_a in metric:
                a_values.append(metric[version_a])
            if version_b in metric:
                b_values.append(metric[version_b])
        
        a_width = max(len(f"{val:.6g}" if isinstance(val, (int, float)) else str(val)) for val in a_values) if a_values else 8
        b_width = max(len(f"{val:.6g}" if isinstance(val, (int, float)) else str(val)) for val in b_values) if b_values else 8
        
        # Use shorter headers with just A/B
        value_suffix = f" {value_field}" if value_field else " count"
        a_header = f"A{value_suffix}"
        b_header = f"B{value_suffix}"
        a_width = max(a_width, len(a_header))
        b_width = max(b_width, len(b_header))
        
        diff_width = 15  # For diff column
        
        # Build header
        header = " " * metric_width + " | " + a_header.ljust(a_width) + " | " + b_header.ljust(b_width) + " | diff"
        lines.append(header)
        
        # Add separator
        separator = "-" * metric_width + "-+-" + "-" * a_width + "-+-" + "-" * b_width + "-+-" + "-" * diff_width
        lines.append(separator)
        
        # Add data rows
        for metric in sorted(metric_data.keys()):
            metric_values = metric_data[metric]
            
            # Get values for both versions
            val_a = metric_values.get(version_a, 0)
            val_b = metric_values.get(version_b, 0)
            
            # Format values
            val_a_str = f"{val_a:.6g}" if isinstance(val_a, (int, float)) else str(val_a)
            val_b_str = f"{val_b:.6g}" if isinstance(val_b, (int, float)) else str(val_b)
            
            # Calculate difference
            try:
                val_a_num = float(val_a)
                val_b_num = float(val_b)
                diff = val_b_num - val_a_num
                
                # Calculate percentage difference
                if val_a_num != 0:
                    pct_diff = (diff / val_a_num) * 100
                    diff_str = f"{diff:+.6g} ({pct_diff:+.1f}%)"
                else:
                    if diff == 0:
                        diff_str = "0"
                    else:
                        diff_str = f"{diff:+.6g} (inf%)"
            except (ValueError, TypeError):
                diff_str = "N/A"
            
            # Build row
            row = str(metric).ljust(metric_width) + " | " + val_a_str.ljust(a_width) + " | " + val_b_str.ljust(b_width) + " | " + diff_str
            lines.append(row)
        
        return "\n".join(lines)
        
    except Exception as e:
        if verbose:
            print(f"Error creating comparison: {e}", file=sys.stderr)
        return None