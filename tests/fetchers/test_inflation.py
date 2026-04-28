import pandas as pd
from unittest.mock import patch, MagicMock
from stock_alert.fetchers import InflationFetcher


_ECB_CSV = (
    "KEY,FREQ,REF_AREA,ADJUSTMENT,ICP_ITEM,STS_INSTITUTION,ICP_SUFFIX,"
    "TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
    "ICP.M.PT.N.000000.4.ANR,M,PT,N,0,4,ANR,2024-01,2.3,A\n"
    "ICP.M.PT.N.000000.4.ANR,M,PT,N,0,4,ANR,2024-02,2.1,A\n"
    "ICP.M.U2.N.000000.4.ANR,M,U2,N,0,4,ANR,2024-01,2.8,A\n"
    "ICP.M.U2.N.000000.4.ANR,M,U2,N,0,4,ANR,2024-02,2.6,A\n"
).encode()

# 26-column OECD csvfilewithlabels format (code col + label col for each dimension)
_OECD_CSV = (
    "STRUCTURE,STRUCTURE_ID,STRUCTURE_NAME,ACTION,"
    "REF_AREA,Reference area,"
    "FREQ,Frequency of observation,"
    "METHODOLOGY,Methodology,"
    "MEASURE,Measure,"
    "UNIT_MEASURE,Unit of measure,"
    "EXPENDITURE,Expenditure,"
    "ADJUSTMENT,Adjustment,"
    "TRANSFORMATION,Transformation,"
    "TIME_PERIOD,Time period,"
    "OBS_VALUE,Observation value,"
    "OBS_STATUS,Observation status\n"
    "DATAFLOW,X,Y,I,USA,United States,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-01,Jan 2024,3.1,3.1,A,Normal\n"
    "DATAFLOW,X,Y,I,USA,United States,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-02,Feb 2024,3.2,3.2,A,Normal\n"
    "DATAFLOW,X,Y,I,GBR,United Kingdom,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-01,Jan 2024,4.0,4.0,A,Normal\n"
).encode()

_OECD_CSV_WITH_PT = (
    "STRUCTURE,STRUCTURE_ID,STRUCTURE_NAME,ACTION,"
    "REF_AREA,Reference area,"
    "FREQ,Frequency of observation,"
    "METHODOLOGY,Methodology,"
    "MEASURE,Measure,"
    "UNIT_MEASURE,Unit of measure,"
    "EXPENDITURE,Expenditure,"
    "ADJUSTMENT,Adjustment,"
    "TRANSFORMATION,Transformation,"
    "TIME_PERIOD,Time period,"
    "OBS_VALUE,Observation value,"
    "OBS_STATUS,Observation status\n"
    # PRT maps to PT (same as ECB) — should be dropped in favour of ECB
    "DATAFLOW,X,Y,I,PRT,Portugal,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-01,Jan 2024,9.9,9.9,A,Normal\n"
).encode()


def _mock_urlopen_sequence(*csv_responses: bytes) -> MagicMock:
    """Return a mock urlopen that yields each CSV bytes in order."""
    responses = []
    for csv in csv_responses:
        mock_resp = MagicMock()
        mock_resp.read.return_value = csv
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        responses.append(mock_resp)
    return MagicMock(side_effect=responses)


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_output_schema(mock_urlopen, tmp_path):
    """fetch() must return a DataFrame with the documented columns and correct dtypes."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert set(df.columns) == {"Date", "country_code", "country_name", "inflation_rate", "source", "identifier"}
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert pd.api.types.is_float_dtype(df["inflation_rate"])
    assert df["inflation_rate"].isna().sum() == 0


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_ecb_takes_priority(mock_urlopen, tmp_path):
    """Countries present in ECB data must not appear with OECD as source."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _OECD_CSV_WITH_PT)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    pt_rows = df[df["country_code"] == "PT"]
    assert (pt_rows["source"] == "ECB").all(), "ECB data must override OECD for PT"
    assert (pt_rows["inflation_rate"] != 9.9).all()


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_merges_ecb_and_oecd_countries(mock_urlopen, tmp_path):
    """Merged result must contain countries from both sources without duplicates per country."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    codes = set(df["country_code"].unique())
    assert "PT" in codes   # ECB source
    assert "U2" in codes   # ECB aggregate
    assert "US" in codes   # OECD source
    assert "GB" in codes   # OECD source

    for code in codes:
        sources = df[df["country_code"] == code]["source"].unique()
        assert len(sources) == 1, f"{code} has rows from multiple sources: {sources}"


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_identifier_format(mock_urlopen, tmp_path):
    """identifier column must follow the INFLATION_{country_code} convention."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    expected = "INFLATION_" + df["country_code"]
    pd.testing.assert_series_equal(df["identifier"], expected, check_names=False)


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_writes_parquet(mock_urlopen, tmp_path):
    """fetch() must persist the merged DataFrame as a parquet file."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    parquet_path = tmp_path / "inflation" / "data.parquet"
    assert parquet_path.exists()
    saved = pd.read_parquet(parquet_path)
    assert len(saved) == len(df)
