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
