"""SQL query builder for chart commands."""
import re
from typing import List, Optional, Tuple


def parse_aggregation(field: str) -> Tuple[Optional[str], str]:
    """
    Parse aggregation function from field specification.
    
    Returns tuple of (aggregation_function, field_name)
    Examples:
        "avg(price)" -> ("avg", "price")
        "sum(total)" -> ("sum", "total")
        "price" -> (None, "price")
    """
    # Match patterns like avg(field), sum(field), etc.
    match = re.match(r'^(\w+)\((.+)\)$', field.strip())
    if match:
        func, field_name = match.groups()
        # Validate known aggregation functions
        valid_funcs = ['avg', 'sum', 'min', 'max', 'count']
        if func.lower() in valid_funcs:
            return func.lower(), field_name.strip()
    
    # No aggregation function found
    return None, field.strip()


def parse_chart_command(args: List[str]) -> Tuple[str, dict]:
    """
    Parse chart command arguments.
    
    Args:
        args: List of arguments after the chart type
    
    Returns:
        Tuple of (chart_type, options_dict)
    """
    if not args:
        raise ValueError("No chart type specified")
    
    chart_type = args[0]
    
    # Map short versions to full chart types
    chart_aliases = {
        'hm': 'heatmap',
        'cmp': 'comparison',
        'mcmp': 'multi-comparison'
    }
    chart_type = chart_aliases.get(chart_type, chart_type)
    
    if chart_type == "heatmap":
        if len(args) < 3:
            raise ValueError("Heatmap requires at least x_field and y_field")
        
        options = {
            "x_field": args[1],
            "y_field": args[2],
            "value_field": args[3] if len(args) > 3 else None
        }
        return chart_type, options
    
    elif chart_type == "comparison":
        if len(args) < 3:
            raise ValueError("Comparison requires at least versions_field and metrics_field")
        
        options = {
            "versions_field": args[1],
            "metrics_field": args[2],
            "value_field": args[3] if len(args) > 3 else None
        }
        return chart_type, options
    
    elif chart_type == "multi-comparison":
        if len(args) < 3:
            raise ValueError("Multi-comparison requires at least versions_field and metrics_field")
        
        options = {
            "versions_field": args[1],
            "metrics_field": args[2],
            "value_field": args[3] if len(args) > 3 else None
        }
        return chart_type, options
    
    # Add more chart types here in the future
    raise ValueError(f"Unknown chart type: {chart_type}")
