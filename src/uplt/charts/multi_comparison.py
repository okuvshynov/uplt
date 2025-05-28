"""Multi-comparison chart implementation."""
import sqlite3
import sys
from typing import Optional, List
from .display_mode import DisplayMode


def should_use_original_names(names: List[str], max_length: int = 8) -> bool:
    """
    Determine if original names should be used instead of letter labels.
    
    Args:
        names: List of version/model names
        max_length: Maximum acceptable length for any name (shorter for multi-comparison)
    
    Returns:
        True if all names are short enough to use directly
    """
    if not names:
        return False
    
    # Check if all names are short enough
    return all(len(str(name)) <= max_length for name in names)


def create_multi_comparison(
    cursor: sqlite3.Cursor,
    versions_field: str,
    metrics_field: str, 
    value_field: Optional[str],
    table_name: str,
    verbose: bool = False,
    display_mode: str = 'value-percent',
    baseline: Optional[str] = None
) -> Optional[str]:
    """
    Create a multi-comparison chart showing differences between multiple versions.
    Uses the first version as baseline (or specified baseline) and compares all others to it.
    
    Args:
        cursor: Database cursor
        versions_field: Field containing version identifiers
        metrics_field: Field containing metric names (rows in output)
        value_field: Optional field to aggregate (defaults to COUNT)
        table_name: Name of the table
        verbose: Whether to show additional debug info
        display_mode: Display mode for difference formatting
        baseline: Optional baseline version to compare against (defaults to first version)
    
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
        
        # Determine baseline version
        if baseline:
            if baseline not in versions:
                return f"Baseline version '{baseline}' not found. Available versions: {', '.join(versions)}"
            baseline_version = baseline
            comparison_versions = [v for v in versions if v != baseline]
        else:
            # Use first version as baseline by default
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
        
        # Determine whether to use original names or letter labels
        all_versions = [baseline_version] + comparison_versions
        use_original = should_use_original_names(all_versions)
        
        if use_original:
            # Use original names directly
            baseline_label = str(baseline_version)
            version_labels = {v: str(v) for v in comparison_versions}
        else:
            # Use letter labels with legend
            baseline_label = "A"
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
        baseline_header = baseline_label
        baseline_width = max(baseline_width, len(baseline_header))
        
        # Calculate widths and formatted values for comparison versions
        version_widths = {}
        version_formatted_values = {}  # Store pre-calculated formatted values
        
        for version in comparison_versions:
            formatted_values = []
            
            for metric in sorted(metric_data.keys()):
                metric_values = metric_data[metric]
                baseline_val = metric_values.get(baseline_version, 0)
                comp_val = metric_values.get(version, 0)
                
                # Format based on display mode
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
                    comp_str = f"{comp_val:.6g}" if isinstance(comp_val, (int, float)) else str(comp_val)
                    
                    if mode == DisplayMode.VALUE:
                        formatted = comp_str
                    elif mode == DisplayMode.DIFF:
                        formatted = f"{diff:+.6g}"
                    elif mode == DisplayMode.PERCENT or mode == DisplayMode.COMPACT:
                        if baseline_num == 0 and diff != 0:
                            formatted = "inf%"
                        else:
                            formatted = f"{pct_diff:+.1f}%"
                    elif mode == DisplayMode.VALUE_DIFF:
                        formatted = f"{comp_str} ({diff:+.6g})"
                    elif mode == DisplayMode.VALUE_PERCENT:
                        if baseline_num == 0 and diff != 0:
                            formatted = f"{comp_str} (inf%)"
                        else:
                            formatted = f"{comp_str} ({pct_diff:+.1f}%)"
                    else:  # FULL
                        formatted = f"{comp_str} {diff:+.6g} ({pct_diff:+.1f}%)" if baseline_num != 0 or diff == 0 else f"{comp_str} {diff:+.6g} (inf%)"
                except (ValueError, TypeError):
                    formatted = "N/A"
                
                formatted_values.append(formatted)
            
            # Calculate column width based on formatted values
            width = max(len(val) for val in formatted_values) if formatted_values else 8
            version_header = version_labels[version]
            width = max(width, len(version_header))
            version_widths[version] = (width, version_header)
            version_formatted_values[version] = formatted_values
        
        # Build header
        header_parts = [" " * metric_width, baseline_header.ljust(baseline_width)]
        
        for version in comparison_versions:
            width, letter_label = version_widths[version]
            header_parts.append(letter_label.ljust(width))
        
        header = " | ".join(header_parts)
        lines.append(header)
        
        # Add separator
        sep_parts = ["-" * metric_width, "-" * baseline_width]
        for version in comparison_versions:
            width, _ = version_widths[version]
            sep_parts.append("-" * width)
        
        separator = "-+-".join(sep_parts)
        lines.append(separator)
        
        # Add data rows
        for i, metric in enumerate(sorted(metric_data.keys())):
            metric_values = metric_data[metric]
            
            # Get baseline value
            baseline_val = metric_values.get(baseline_version, 0)
            baseline_str = f"{baseline_val:.6g}" if isinstance(baseline_val, (int, float)) else str(baseline_val)
            
            # Start building row
            row_parts = [str(metric).ljust(metric_width), baseline_str.ljust(baseline_width)]
            
            # Add comparison values
            for version in comparison_versions:
                # Get pre-calculated formatted value
                formatted_value = version_formatted_values[version][i]
                width, _ = version_widths[version]
                row_parts.append(formatted_value.ljust(width))
            
            row = " | ".join(row_parts)
            lines.append(row)
        
        return "\n".join(lines)
        
    except Exception as e:
        if verbose:
            print(f"Error creating multi-comparison: {e}", file=sys.stderr)
        return None
