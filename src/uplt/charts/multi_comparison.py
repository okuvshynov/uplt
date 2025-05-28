"""Multi-comparison chart implementation."""
import sqlite3
import sys
from typing import Optional
from .display_mode import DisplayMode


def create_multi_comparison(
    cursor: sqlite3.Cursor,
    versions_field: str,
    metrics_field: str, 
    value_field: Optional[str],
    table_name: str,
    verbose: bool = False,
    display_mode: str = 'full'
) -> Optional[str]:
    """
    Create a multi-comparison chart showing differences between multiple versions.
    Uses the first version as baseline and compares all others to it.
    
    Args:
        cursor: Database cursor
        versions_field: Field containing version identifiers
        metrics_field: Field containing metric names (rows in output)
        value_field: Optional field to aggregate (defaults to COUNT)
        table_name: Name of the table
        verbose: Whether to show additional debug info
    
    Returns:
        Formatted multi-comparison chart as string
    """
    from ..query_builder import parse_aggregation
    from ..core import execute_query
    
    # Parse display mode
    try:
        mode = DisplayMode.from_string(display_mode)
    except ValueError as e:
        if verbose:
            print(f"Invalid display mode: {e}", file=sys.stderr)
        mode = DisplayMode.FULL
    
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
        
        if len(versions) < 2:
            return "Need at least 2 versions to compare"
        
        # Use first version as baseline
        baseline_version = versions[0]
        comparison_versions = versions[1:]
        
        if verbose:
            print(f"Baseline: {baseline_version}", file=sys.stderr)
            print(f"Comparing against: {comparison_versions}", file=sys.stderr)
        
        # Get all metrics and their values for all versions
        data_query = f"""
        SELECT 
            {metrics_field} as metric,
            {versions_field} as version,
            {value_expr} as value
        FROM {table_name}
        WHERE {metrics_field} IS NOT NULL
        GROUP BY {metrics_field}, {versions_field}
        ORDER BY {metrics_field}, {versions_field}
        """
        
        if verbose:
            print(f"Generated query: {data_query}", file=sys.stderr)
            print(f"Display mode: {mode.name.lower()} - {mode.describe()}", file=sys.stderr)
        
        results = execute_query(cursor, data_query)
        
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
        
        # Build the multi-comparison table
        lines = []
        
        # Add version labels at the top
        lines.append(f"Baseline (A): {baseline_version}")
        
        # Create letter labels for comparison versions
        version_labels = {}
        for i, version in enumerate(comparison_versions):
            label = chr(ord('B') + i)  # B, C, D, ...
            version_labels[version] = label
            lines.append(f"{label}: {version}")
        
        lines.append("")
        
        # Calculate column widths
        metric_width = max(len(str(metric)) for metric in metric_data.keys())
        metric_width = max(metric_width, 7)  # Minimum width for header
        
        # Calculate widths for baseline and each comparison version
        baseline_values = []
        for metric in metric_data.values():
            if baseline_version in metric:
                baseline_values.append(metric[baseline_version])
        
        baseline_width = max(len(f"{val:.6g}" if isinstance(val, (int, float)) else str(val)) for val in baseline_values) if baseline_values else 8
        baseline_header = "A"
        baseline_width = max(baseline_width, len(baseline_header))
        
        # Calculate widths for comparison versions and diff columns
        version_widths = {}
        diff_widths = {}
        
        for version in comparison_versions:
            version_values = []
            diff_strings = []
            
            for metric in metric_data.values():
                if version in metric:
                    version_values.append(metric[version])
                    
                    # Calculate diff string to determine width
                    baseline_val = metric.get(baseline_version, 0)
                    comp_val = metric.get(version, 0)
                    
                    try:
                        baseline_num = float(baseline_val)
                        comp_num = float(comp_val)
                        diff = comp_num - baseline_num
                        
                        if baseline_num != 0:
                            pct_diff = (diff / baseline_num) * 100
                            diff_str = f"{diff:+.6g} ({pct_diff:+.1f}%)"
                        else:
                            if diff == 0:
                                diff_str = "0"
                            else:
                                diff_str = f"{diff:+.6g} (inf%)"
                    except (ValueError, TypeError):
                        diff_str = "N/A"
                    
                    diff_strings.append(diff_str)
            
            val_width = max(len(f"{val:.6g}" if isinstance(val, (int, float)) else str(val)) for val in version_values) if version_values else 8
            # Use letter labels
            version_header = version_labels[version]
            val_width = max(val_width, len(version_header))
            version_widths[version] = (val_width, version_header)
            
            # Calculate actual diff width needed based on display mode
            diff_width = max(len(s) for s in diff_strings) if diff_strings else mode.get_diff_column_width()
            diff_width = max(diff_width, 4)  # Minimum width for "diff" header
            diff_widths[version] = diff_width
        
        # Build header
        header_parts = [" " * metric_width, baseline_header.ljust(baseline_width)]
        
        for version in comparison_versions:
            width, letter_label = version_widths[version]
            diff_width = diff_widths[version]
            header_parts.extend([letter_label.ljust(width), "diff".ljust(diff_width)])
        
        header = " | ".join(header_parts)
        lines.append(header)
        
        # Add separator
        sep_parts = ["-" * metric_width, "-" * baseline_width]
        for version in comparison_versions:
            width, _ = version_widths[version]
            diff_width = diff_widths[version]
            sep_parts.extend(["-" * width, "-" * diff_width])
        
        separator = "-+-".join(sep_parts)
        lines.append(separator)
        
        # Add data rows
        for metric in sorted(metric_data.keys()):
            metric_values = metric_data[metric]
            
            # Get baseline value
            baseline_val = metric_values.get(baseline_version, 0)
            baseline_str = f"{baseline_val:.6g}" if isinstance(baseline_val, (int, float)) else str(baseline_val)
            
            # Start building row
            row_parts = [str(metric).ljust(metric_width), baseline_str.ljust(baseline_width)]
            
            # Add comparison values and differences
            for version in comparison_versions:
                comp_val = metric_values.get(version, 0)
                comp_str = f"{comp_val:.6g}" if isinstance(comp_val, (int, float)) else str(comp_val)
                
                # Calculate difference based on display mode
                try:
                    baseline_num = float(baseline_val)
                    comp_num = float(comp_val)
                    diff = comp_num - baseline_num
                    
                    # Calculate percentage difference
                    if baseline_num != 0:
                        pct_diff = (diff / baseline_num) * 100
                    else:
                        pct_diff = float('inf') if diff != 0 else 0
                    
                    # Format based on display mode
                    if mode.should_show_value_in_diff_column():
                        # For VALUE mode variants, show the comparison value instead of diff
                        if mode == DisplayMode.VALUE:
                            diff_str = comp_str
                        elif mode == DisplayMode.VALUE_DIFF:
                            diff_str = f"{comp_str} ({diff:+.6g})"
                        else:  # VALUE_PERCENT
                            if baseline_num == 0 and diff != 0:
                                diff_str = f"{comp_str} (inf%)"
                            else:
                                diff_str = f"{comp_str} ({pct_diff:+.1f}%)"
                    else:
                        # Use the display mode's formatting method
                        diff_str = mode.format_diff_cell(diff, pct_diff, baseline_num)
                except (ValueError, TypeError):
                    diff_str = "N/A"
                
                width, _ = version_widths[version]
                diff_width = diff_widths[version]
                row_parts.extend([comp_str.ljust(width), diff_str.ljust(diff_width)])
            
            row = " | ".join(row_parts)
            lines.append(row)
        
        return "\n".join(lines)
        
    except Exception as e:
        if verbose:
            print(f"Error creating multi-comparison: {e}", file=sys.stderr)
        return None