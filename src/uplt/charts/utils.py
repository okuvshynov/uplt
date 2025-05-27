"""Shared utilities for chart plotting."""
import math
from typing import List, Union


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