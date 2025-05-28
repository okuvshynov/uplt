"""Display mode configuration for comparison charts."""
from enum import Enum, auto
from typing import Optional, Tuple


class DisplayMode(Enum):
    """Display modes for comparison charts."""
    FULL = auto()      # Show value, absolute diff, and percentage (default)
    COMPACT = auto()   # Show only percentage diff
    VALUE = auto()     # Show only raw values
    DIFF = auto()      # Show only absolute diff
    PERCENT = auto()   # Show only percentage diff
    VALUE_DIFF = auto()    # Show value and absolute diff
    VALUE_PERCENT = auto() # Show value and percentage diff

    @classmethod
    def from_string(cls, mode_str: str) -> 'DisplayMode':
        """Create DisplayMode from string representation."""
        mode_map = {
            'full': cls.FULL,
            'compact': cls.COMPACT,
            'value': cls.VALUE,
            'diff': cls.DIFF,
            'percent': cls.PERCENT,
            'value-diff': cls.VALUE_DIFF,
            'value-percent': cls.VALUE_PERCENT,
        }
        mode_lower = mode_str.lower()
        if mode_lower not in mode_map:
            valid_modes = ', '.join(sorted(mode_map.keys()))
            raise ValueError(f"Invalid display mode: {mode_str}. Valid modes: {valid_modes}")
        return mode_map[mode_lower]

    def format_diff_cell(self, diff: float, pct_diff: float, baseline: float) -> str:
        """Format a difference cell based on the display mode."""
        if baseline == 0:
            if diff == 0:
                return "0"
            else:
                # Handle infinity case
                if self == DisplayMode.PERCENT or self == DisplayMode.COMPACT:
                    return "inf%"
                elif self == DisplayMode.DIFF:
                    return f"{diff:+.6g}"
                elif self == DisplayMode.VALUE_PERCENT:
                    return "inf%"
                elif self == DisplayMode.VALUE_DIFF:
                    return f"{diff:+.6g}"
                else:  # FULL
                    return f"{diff:+.6g} (inf%)"
        
        # Normal case with non-zero baseline
        if self == DisplayMode.PERCENT or self == DisplayMode.COMPACT:
            return f"{pct_diff:+.1f}%"
        elif self == DisplayMode.DIFF:
            return f"{diff:+.6g}"
        elif self == DisplayMode.VALUE_PERCENT:
            return f"{pct_diff:+.1f}%"
        elif self == DisplayMode.VALUE_DIFF:
            return f"{diff:+.6g}"
        else:  # FULL
            return f"{diff:+.6g} ({pct_diff:+.1f}%)"

    def should_show_value_in_diff_column(self) -> bool:
        """Check if the mode includes raw values in difference columns."""
        return self in (DisplayMode.VALUE, DisplayMode.VALUE_DIFF, DisplayMode.VALUE_PERCENT)

    def get_diff_column_width(self) -> int:
        """Get recommended column width for difference columns."""
        width_map = {
            DisplayMode.FULL: 20,      # e.g., "+123.456 (+12.3%)"
            DisplayMode.COMPACT: 8,    # e.g., "+12.3%"
            DisplayMode.VALUE: 12,     # e.g., "123.456"
            DisplayMode.DIFF: 12,      # e.g., "+123.456"
            DisplayMode.PERCENT: 8,    # e.g., "+12.3%"
            DisplayMode.VALUE_DIFF: 12,    # e.g., "+123.456"
            DisplayMode.VALUE_PERCENT: 8,  # e.g., "+12.3%"
        }
        return width_map.get(self, 20)

    def describe(self) -> str:
        """Get a human-readable description of the display mode."""
        descriptions = {
            DisplayMode.FULL: "Show value, absolute difference, and percentage",
            DisplayMode.COMPACT: "Show only percentage difference",
            DisplayMode.VALUE: "Show only raw values",
            DisplayMode.DIFF: "Show only absolute difference",
            DisplayMode.PERCENT: "Show only percentage difference",
            DisplayMode.VALUE_DIFF: "Show value and absolute difference",
            DisplayMode.VALUE_PERCENT: "Show value and percentage difference",
        }
        return descriptions.get(self, "Unknown display mode")