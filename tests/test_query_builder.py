import pytest
from uplt.query_builder import parse_aggregation, parse_chart_command


class TestParseAggregation:
    def test_avg_function(self):
        func, field = parse_aggregation("avg(price)")
        assert func == "avg"
        assert field == "price"
    
    def test_sum_function(self):
        func, field = parse_aggregation("sum(total)")
        assert func == "sum"
        assert field == "total"
    
    def test_min_function(self):
        func, field = parse_aggregation("min(value)")
        assert func == "min"
        assert field == "value"
    
    def test_max_function(self):
        func, field = parse_aggregation("max(score)")
        assert func == "max"
        assert field == "score"
    
    def test_count_function(self):
        func, field = parse_aggregation("count(id)")
        assert func == "count"
        assert field == "id"
    
    def test_no_aggregation(self):
        func, field = parse_aggregation("price")
        assert func is None
        assert field == "price"
    
    def test_invalid_function(self):
        func, field = parse_aggregation("invalid(price)")
        assert func is None
        assert field == "invalid(price)"
    
    def test_with_spaces(self):
        func, field = parse_aggregation("avg( price )")
        assert func == "avg"
        assert field == "price"
    
    def test_nested_parentheses(self):
        # Should not parse nested functions
        func, field = parse_aggregation("avg(sum(price))")
        assert func == "avg"
        assert field == "sum(price)"


class TestParseChartCommand:
    def test_heatmap_minimal(self):
        chart_type, options = parse_chart_command(["heatmap", "field1", "field2"])
        assert chart_type == "heatmap"
        assert options == {
            "x_field": "field1",
            "y_field": "field2",
            "value_field": None
        }
    
    def test_heatmap_with_value(self):
        chart_type, options = parse_chart_command(["heatmap", "dept", "age", "avg(salary)"])
        assert chart_type == "heatmap"
        assert options == {
            "x_field": "dept",
            "y_field": "age",
            "value_field": "avg(salary)"
        }
    
    def test_no_chart_type(self):
        with pytest.raises(ValueError, match="No chart type specified"):
            parse_chart_command([])
    
    def test_heatmap_missing_fields(self):
        with pytest.raises(ValueError, match="Heatmap requires at least x_field and y_field"):
            parse_chart_command(["heatmap"])
        
        with pytest.raises(ValueError, match="Heatmap requires at least x_field and y_field"):
            parse_chart_command(["heatmap", "field1"])
    
    def test_unknown_chart_type(self):
        with pytest.raises(ValueError, match="Unknown chart type: barchart"):
            parse_chart_command(["barchart", "field1", "field2"])
    
    def test_comparison_minimal(self):
        chart_type, options = parse_chart_command(["comparison", "versions", "metrics"])
        assert chart_type == "comparison"
        assert options == {
            "versions_field": "versions",
            "metrics_field": "metrics",
            "value_field": None
        }
    
    def test_comparison_with_value(self):
        chart_type, options = parse_chart_command(["comparison", "model_id", "input_size", "score"])
        assert chart_type == "comparison"
        assert options == {
            "versions_field": "model_id",
            "metrics_field": "input_size",
            "value_field": "score"
        }
    
    def test_comparison_with_aggregation(self):
        chart_type, options = parse_chart_command(["comparison", "model", "size", "avg(latency)"])
        assert chart_type == "comparison"
        assert options == {
            "versions_field": "model",
            "metrics_field": "size",
            "value_field": "avg(latency)"
        }
    
    def test_comparison_missing_fields(self):
        with pytest.raises(ValueError, match="Comparison requires at least versions_field and metrics_field"):
            parse_chart_command(["comparison"])
        
        with pytest.raises(ValueError, match="Comparison requires at least versions_field and metrics_field"):
            parse_chart_command(["comparison", "versions"])
    
    def test_heatmap_short_alias(self):
        chart_type, options = parse_chart_command(["hm", "field1", "field2"])
        assert chart_type == "heatmap"
        assert options == {
            "x_field": "field1",
            "y_field": "field2",
            "value_field": None
        }
    
    def test_comparison_short_alias(self):
        chart_type, options = parse_chart_command(["cmp", "versions", "metrics", "value"])
        assert chart_type == "comparison"
        assert options == {
            "versions_field": "versions",
            "metrics_field": "metrics",
            "value_field": "value"
        }
