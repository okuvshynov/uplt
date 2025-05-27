"""Terminal chart plotting using Unicode characters."""
import math
import sqlite3
import sys
from typing import List, Tuple, Optional, Union, Dict


def is_numeric_axis(values: List) -> bool:
    """Check if all values in a list can be converted to numbers."""
    if not values:
        return False
    
    for val in values:
        try:
            float(val)
        except (ValueError, TypeError):
            return False
    return True


def create_numeric_scale(min_val: float, max_val: float, target_steps: int = 10) -> List[float]:
    """Create a nice numeric scale for an axis."""
    if min_val == max_val:
        # Single value, create scale around it
        if min_val == 0:
            return [0]
        return [min_val * 0.9, min_val, min_val * 1.1]
    
    range_val = max_val - min_val
    
    # Find a nice step size
    raw_step = range_val / target_steps
    magnitude = 10 ** math.floor(math.log10(raw_step))
    
    # Round to nice numbers (1, 2, 2.5, 5, 10)
    normalized_step = raw_step / magnitude
    if normalized_step <= 1:
        nice_step = 1
    elif normalized_step <= 2:
        nice_step = 2
    elif normalized_step <= 2.5:
        nice_step = 2.5
    elif normalized_step <= 5:
        nice_step = 5
    else:
        nice_step = 10
    
    step = nice_step * magnitude
    
    # Create scale
    start = math.floor(min_val / step) * step
    end = math.ceil(max_val / step) * step
    
    scale = []
    current = start
    while current <= end + step * 0.01:  # Small epsilon for floating point
        scale.append(current)
        current += step
    
    return scale


def find_bin_index(value: float, scale: List[float]) -> int:
    """Find which bin a value belongs to in a scale."""
    for i in range(len(scale) - 1):
        if scale[i] <= value < scale[i + 1]:
            return i
    # Handle edge case for maximum value
    if value == scale[-1]:
        return len(scale) - 2
    return -1


def build_axis_query(
    field: str,
    min_val: Union[float, str, None],
    max_val: Union[float, str, None],
    target_bins: int,
    alias: str
) -> Tuple[str, Optional[List[float]], bool]:
    """
    Build query piece for an axis (either numeric with binning or categorical).
    
    Returns:
        - SQL expression for the axis
        - Scale (if numeric) or None (if categorical)
        - Whether the axis is numeric
    """
    # Check if axis is numeric
    is_numeric = False
    min_num = None
    max_num = None
    
    try:
        min_num = float(min_val) if min_val is not None else None
        max_num = float(max_val) if max_val is not None else None
        if min_num is not None and max_num is not None:
            is_numeric = True
    except (ValueError, TypeError):
        pass
    
    if is_numeric:
        # Create scale and build CASE statement for binning
        scale = create_numeric_scale(min_num, max_num, target_bins)
        
        case_parts = []
        for i in range(len(scale) - 1):
            case_parts.append(
                f"WHEN {field} >= {scale[i]} AND {field} < {scale[i+1]} THEN {i}"
            )
        # Handle the last bin edge case
        case_parts.append(f"WHEN {field} = {scale[-1]} THEN {len(scale)-2}")
        
        sql_expr = f"CASE {' '.join(case_parts)} END as {alias}"
        return sql_expr, scale, True
    else:
        # Categorical - just use the field directly
        sql_expr = f"{field} as {alias}"
        return sql_expr, None, False


def create_heatmap(
    cursor: sqlite3.Cursor,
    x_field: str,
    y_field: str, 
    value_field: Optional[str],
    table_name: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    verbose: bool = False
) -> Optional[str]:
    """
    Create a heatmap with proper SQL-based aggregation for binned data.
    
    This avoids double aggregation by determining bins first, then running
    a SQL query that groups by those bins with the correct aggregation function.
    """
    from .query_builder import parse_aggregation
    from .core import execute_query
    
    # First, get the range of values to determine if axes are numeric
    range_query = f"""
    SELECT 
        MIN({x_field}) as x_min, MAX({x_field}) as x_max,
        MIN({y_field}) as y_min, MAX({y_field}) as y_max
    FROM {table_name}
    """
    
    try:
        range_results = execute_query(cursor, range_query)
        if not range_results or not range_results[0]:
            return None
        
        x_min, x_max, y_min, y_max = range_results[0]
        
        # Build query pieces for each axis
        x_expr, x_scale, x_is_numeric = build_axis_query(
            x_field, x_min, x_max, width or 20, "x"
        )
        y_expr, y_scale, y_is_numeric = build_axis_query(
            y_field, y_min, y_max, height or 15, "y"
        )
        
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
        
        # Build the SELECT and GROUP BY clauses based on axis types
        select_parts = []
        group_by_parts = []
        having_parts = []
        
        # Handle X axis
        if x_is_numeric:
            x_expr_only = x_expr.replace(" as x", "")
            select_parts.append(f"{x_expr_only} as x_bin")
            group_by_parts.append("x_bin")
            having_parts.append("x_bin IS NOT NULL")
        else:
            select_parts.append(x_expr)
            group_by_parts.append(x_field)
        
        # Handle Y axis
        if y_is_numeric:
            y_expr_only = y_expr.replace(" as y", "")
            select_parts.append(f"{y_expr_only} as y_bin")
            group_by_parts.append("y_bin")
            having_parts.append("y_bin IS NOT NULL")
        else:
            select_parts.append(y_expr)
            group_by_parts.append(y_field)
        
        # Add value expression
        select_parts.append(f"{value_expr} as value")
        
        # Build the complete query
        query = f"""
        SELECT 
            {', '.join(select_parts)}
        FROM {table_name}
        WHERE ({x_field} IS NOT NULL) AND ({y_field} IS NOT NULL)
        GROUP BY {', '.join(group_by_parts)}
        """
        
        if having_parts:
            query += f"\nHAVING {' AND '.join(having_parts)}"
        
        if verbose:
            print(f"Generated query: {query}", file=sys.stderr)
        
        results = execute_query(cursor, query)
        
        if not results:
            return None
        
        # Transform the results for the heatmap
        transformed_data = []
        
        for row in results:
            if x_is_numeric and y_is_numeric:
                x_bin, y_bin, value = row
                if x_bin is not None and y_bin is not None:
                    x_val = x_scale[x_bin]
                    y_val = y_scale[y_bin]
                    transformed_data.append((x_val, y_val, value))
            elif x_is_numeric:
                x_bin, y_val, value = row
                if x_bin is not None:
                    x_val = x_scale[x_bin]
                    transformed_data.append((x_val, y_val, value))
            elif y_is_numeric:
                x_val, y_bin, value = row
                if y_bin is not None:
                    y_val = y_scale[y_bin]
                    transformed_data.append((x_val, y_val, value))
            else:
                transformed_data.append(row)
        
        # Print aggregated data points in verbose mode
        if verbose and transformed_data:
            print("\nAggregated data points:", file=sys.stderr)
            for x_val, y_val, value in sorted(transformed_data):
                # Format the values nicely
                x_str = f"{x_val:.6g}" if isinstance(x_val, (int, float)) else str(x_val)
                y_str = f"{y_val:.6g}" if isinstance(y_val, (int, float)) else str(y_val)
                value_str = f"{value:.6g}" if isinstance(value, (int, float)) else str(value)
                print(f"  ({x_str}, {y_str}) -> {value_str}", file=sys.stderr)
            print(file=sys.stderr)  # Empty line for better readability
        
        # Now create the heatmap without any additional aggregation
        return create_heatmap_without_aggregation(
            transformed_data,
            x_scale if x_is_numeric else None,
            y_scale if y_is_numeric else None,
            width=width,
            height=height
        )
        
    except Exception as e:
        if verbose:
            print(f"Error creating heatmap: {e}", file=sys.stderr)
        return None


def create_heatmap_without_aggregation(
    data: List[Tuple],
    x_scale: Optional[List[float]] = None,
    y_scale: Optional[List[float]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    chars: str = " ░▒▓█"
) -> str:
    """
    Create a heatmap from pre-aggregated data without any additional aggregation.
    
    This is used when SQL has already done the aggregation for us.
    """
    if not data:
        return "No data to plot"
    
    # Extract values and determine axes
    x_values_raw = [row[0] for row in data]
    y_values_raw = [row[1] for row in data]
    
    # Use provided scales or create from data
    if x_scale is not None:
        x_is_numeric = True
        x_labels = [f"{x:.6g}" for x in x_scale]
        x_bins = len(x_scale) - 1
    else:
        x_is_numeric = False
        x_labels = sorted(list(set(str(x) for x in x_values_raw)))
        x_bins = len(x_labels)
    
    if y_scale is not None:
        y_is_numeric = True
        y_labels = [f"{y:.6g}" for y in y_scale]
        y_bins = len(y_scale) - 1
        # Reverse for display
        y_labels = list(reversed(y_labels))
        y_scale = list(reversed(y_scale))
    else:
        y_is_numeric = False
        y_labels = sorted(list(set(str(y) for y in y_values_raw)), reverse=True)
        y_bins = len(y_labels)
    
    # Create grid - no aggregation needed as SQL already did it
    grid = {}
    all_values = []
    
    for x_raw, y_raw, value in data:
        if value is None:
            continue
            
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            continue
        
        # Find grid position
        if x_is_numeric:
            x_idx = find_bin_index(float(x_raw), x_scale)
            if x_idx < 0:
                continue
        else:
            try:
                x_idx = x_labels.index(str(x_raw))
            except ValueError:
                continue
        
        if y_is_numeric:
            # y_scale is already reversed
            original_scale = list(reversed(y_scale))
            bin_idx = find_bin_index(float(y_raw), original_scale)
            if bin_idx < 0:
                continue
            y_idx = y_bins - 1 - bin_idx
            if y_idx < 0 or y_idx >= y_bins:
                continue
        else:
            try:
                y_idx = y_labels.index(str(y_raw))
            except ValueError:
                continue
        
        # Direct assignment - no aggregation
        grid[(x_idx, y_idx)] = numeric_value
        all_values.append(numeric_value)
    
    if not all_values:
        return "No numeric values to plot"
    
    # Find min and max for color scaling
    min_val = min(all_values)
    max_val = max(all_values)
    
    # For non-negative data, ensure scale starts at 0
    if min_val >= 0:
        min_val = 0
    
    # Build the rest of the heatmap as before
    if min_val == max_val:
        char_idx = len(chars) // 2
    else:
        char_idx = None
    
    # Calculate label widths
    x_label_width = max(len(label) for label in x_labels) if x_labels else 0
    y_label_width = max(len(label) for label in y_labels) if y_labels else 0
    
    # Build the heatmap
    lines = []
    
    # Add header with x labels
    if x_is_numeric:
        header = " " * (y_label_width + 1)
        for i, label in enumerate(x_labels[:-1]):
            header += label.rjust(x_label_width + 1)
        lines.append(header)
    else:
        header = " " * (y_label_width + 1)
        for label in x_labels:
            header += label.rjust(x_label_width + 1)
        lines.append(header)
    
    # Add separator
    separator = " " * (y_label_width + 1) + "-" * (x_bins * (x_label_width + 1))
    lines.append(separator)
    
    # Add data rows
    for y_idx in range(y_bins):
        row_label = y_labels[y_idx]
        row = row_label.rjust(y_label_width) + "|"
        
        for x_idx in range(x_bins):
            key = (x_idx, y_idx)
            if key in grid:
                value = grid[key]
                if char_idx is not None:
                    idx = char_idx
                else:
                    normalized = (value - min_val) / (max_val - min_val)
                    idx = int(normalized * (len(chars) - 1))
                    idx = max(0, min(idx, len(chars) - 1))
                char = chars[idx]
            else:
                char = " "
            
            row += (char * x_label_width) + " "
        
        lines.append(row)
    
    # Add scale info
    lines.append("")
    
    if x_is_numeric:
        x_min = min(float(x) for x in x_values_raw)
        x_max = max(float(x) for x in x_values_raw)
        lines.append(f"X-axis: {x_min:.6g} to {x_max:.6g}")
    if y_is_numeric:
        y_min = min(float(y) for y in y_values_raw)
        y_max = max(float(y) for y in y_values_raw)
        lines.append(f"Y-axis: {y_min:.6g} to {y_max:.6g}")
    
    # Create legend showing range for each character
    if min_val == max_val:
        lines.append(f"Value scale: All values = {min_val:.6g}")
    else:
        value_range = max_val - min_val
        step = value_range / len(chars)
        legend_parts = []
        for i, char in enumerate(chars):
            lower = min_val + i * step
            upper = min_val + (i + 1) * step
            if i == len(chars) - 1:
                # Last character includes the maximum value
                legend_parts.append(f"'{char}': [{lower:.6g}, {upper:.6g}]")
            else:
                legend_parts.append(f"'{char}': [{lower:.6g}, {upper:.6g})")
        lines.append("Value scale: " + "  ".join(legend_parts))
    
    return "\n".join(lines)


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
    from .query_builder import parse_aggregation
    from .core import execute_query
    
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


def create_multi_comparison(
    cursor: sqlite3.Cursor,
    versions_field: str,
    metrics_field: str, 
    value_field: Optional[str],
    table_name: str,
    verbose: bool = False
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
    from .query_builder import parse_aggregation
    from .core import execute_query
    
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
        
        # Add baseline label at the top
        lines.append(f"Baseline: {baseline_version}")
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
        baseline_header = "Baseline"
        baseline_width = max(baseline_width, len(baseline_header))
        
        # Calculate widths for comparison versions
        version_widths = {}
        for version in comparison_versions:
            version_values = []
            for metric in metric_data.values():
                if version in metric:
                    version_values.append(metric[version])
            
            val_width = max(len(f"{val:.6g}" if isinstance(val, (int, float)) else str(val)) for val in version_values) if version_values else 8
            # Truncate long version names for column headers
            version_header = version if len(version) <= 12 else version[:9] + "..."
            val_width = max(val_width, len(version_header))
            version_widths[version] = (val_width, version_header)
        
        diff_width = 15  # For diff columns
        
        # Build header
        header_parts = [" " * metric_width, baseline_header.ljust(baseline_width)]
        
        for version in comparison_versions:
            width, short_name = version_widths[version]
            header_parts.extend([short_name.ljust(width), "diff".ljust(diff_width)])
        
        header = " | ".join(header_parts)
        lines.append(header)
        
        # Add separator
        sep_parts = ["-" * metric_width, "-" * baseline_width]
        for version in comparison_versions:
            width, _ = version_widths[version]
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
                
                # Calculate difference
                try:
                    baseline_num = float(baseline_val)
                    comp_num = float(comp_val)
                    diff = comp_num - baseline_num
                    
                    # Calculate percentage difference
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
                
                width, _ = version_widths[version]
                row_parts.extend([comp_str.ljust(width), diff_str.ljust(diff_width)])
            
            row = " | ".join(row_parts)
            lines.append(row)
        
        # Add legend for truncated version names if any
        truncated = [(v, version_widths[v][1]) for v in comparison_versions if len(v) > 12]
        if truncated:
            lines.append("")
            lines.append("Version names:")
            for full_name, short_name in truncated:
                lines.append(f"  {short_name} = {full_name}")
        
        return "\n".join(lines)
        
    except Exception as e:
        if verbose:
            print(f"Error creating multi-comparison: {e}", file=sys.stderr)
        return None
