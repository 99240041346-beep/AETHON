from app.data_tool import DataAnalysisTool


def test_data_analysis_csv():
    result = DataAnalysisTool().execute("name,value\na,10\nb,20\nc,30\n", "csv")
    assert result.ok
    assert result.verified
    assert result.output["rows"] == 3
    assert result.output["statistics"]["value"]["mean"] == 20.0


def test_data_analysis_json():
    result = DataAnalysisTool().execute('[{"x":1},{"x":3}]', "json")
    assert result.ok
    assert result.output["statistics"]["x"]["max"] == 3.0
