from app.chart_tools import build_chart


def test_build_bar_chart():
    chart = build_chart("bar chart: Apples=30, Oranges=20, Bananas=25")
    assert chart["chartType"] == "bar"
    assert [row["value"] for row in chart["data"]] == [30.0, 20.0, 25.0]


def test_build_line_chart():
    chart = build_chart("line chart for monthly sales: Jan=10, Feb=15, Mar=12")
    assert chart["chartType"] == "line"
    assert chart["data"][1]["category"] == "Feb"


def test_build_pie_chart():
    chart = build_chart("pie chart: CSE=40, ECE=30, EEE=30")
    assert chart["chartType"] == "pie"
    assert sum(row["value"] for row in chart["data"]) == 100


def test_build_scatter_chart():
    chart = build_chart("scatter plot: 1,2; 2,4; 3,5")
    assert chart["chartType"] == "scatter"
    assert chart["data"][-1] == {"x": 3.0, "y": 5.0}


def test_chart_requires_two_points():
    assert build_chart("bar chart: Apples=30") is None
