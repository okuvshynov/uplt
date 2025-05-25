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
