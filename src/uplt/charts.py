"""Terminal chart plotting using Unicode characters."""
# Re-export all chart functions from the submodules
from .charts.heatmap import create_heatmap
from .charts.comparison import create_comparison
from .charts.multi_comparison import create_multi_comparison

__all__ = ['create_heatmap', 'create_comparison', 'create_multi_comparison']