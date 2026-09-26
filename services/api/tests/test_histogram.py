from app.chart_tools import build_chart


def test_histogram_builds_frequency_distribution():
    chart = build_chart("histogram: 1, 1, 2, 2, 2, 3, 4")
    assert chart["chartType"] == "histogram"
    assert len(chart["data"]) >= 1
    assert sum(row["value"] for row in chart["data"]) == 7
