import json
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

_EUROSTAT_JSON = json.dumps({
    "id": ["freq", "coicop18", "unit", "geo", "time"],
    "size": [1, 1, 1, 2, 2],
    "dimension": {
        "freq": {"category": {"index": {"M": 0}}},
        "coicop18": {"category": {"index": {"TOTAL": 0}}},
        "unit": {"category": {"index": {"PCH_M12": 0}}},
        "geo": {"category": {"index": {"PT": 0, "EA20": 1}}},
        "time": {"category": {"index": {"2024-02": 0, "2024-03": 1}}},
    },
    "value": {
        "0": 2.2,  # PT 2024-02 (overrides ECB)
        "1": 2.5,  # PT 2024-03 (fresher than ECB)
        "2": 2.7,  # EA20 -> U2 2024-02
        "3": 2.4,  # EA20 -> U2 2024-03
    },
}).encode()

_EUROSTAT_EMPTY_JSON = json.dumps({
    "id": [],
    "size": [],
    "dimension": {},
    "value": {},
}).encode()

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
    # PRT maps to PT (same as ECB) — should be dropped in favour of ECB/Eurostat
    "DATAFLOW,X,Y,I,PRT,Portugal,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-01,Jan 2024,9.9,9.9,A,Normal\n"
).encode()

_OECD_CSV_WITH_PT_NEWER = (
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
    # Overlapping month with ECB (should be dropped)
    "DATAFLOW,X,Y,I,PRT,Portugal,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-02,Feb 2024,8.8,8.8,A,Normal\n"
    # Newer month than ECB/Eurostat max (should be kept as fallback)
    "DATAFLOW,X,Y,I,PRT,Portugal,M,Monthly,N,National,CPI,CPI,PA,Pct,_T,Total,N,NotAdj,GY,YoY,2024-04,Apr 2024,1.9,1.9,A,Normal\n"
).encode()


def _mock_urlopen_sequence(*responses: bytes) -> MagicMock:
    """Return a mock urlopen that yields each response bytes in order."""
    mock_responses = []
    for resp_bytes in responses:
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_bytes
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_responses.append(mock_resp)
    return MagicMock(side_effect=mock_responses)


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_output_schema(mock_urlopen, tmp_path):
    """fetch() must return a DataFrame with the documented columns and correct dtypes."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_JSON, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert set(df.columns) == {"Date", "country_code", "country_name", "inflation_rate", "source", "identifier"}
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert pd.api.types.is_float_dtype(df["inflation_rate"])
    assert df["inflation_rate"].isna().sum() == 0


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_eurostat_overrides_ecb_on_overlap(mock_urlopen, tmp_path):
    """Eurostat recent data must override ECB on overlapping dates and add new months."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_JSON, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    pt_rows = df[df["country_code"] == "PT"].sort_values("Date")
    # 2024-01 from ECB, 2024-02 overridden by Eurostat (2.2), 2024-03 from Eurostat (2.5)
    assert len(pt_rows) == 3
    assert pt_rows.iloc[0]["source"] == "ECB"
    assert pt_rows.iloc[0]["inflation_rate"] == 2.3
    assert pt_rows.iloc[1]["source"] == "Eurostat"
    assert pt_rows.iloc[1]["inflation_rate"] == 2.2
    assert pt_rows.iloc[2]["source"] == "Eurostat"
    assert pt_rows.iloc[2]["inflation_rate"] == 2.5


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_ecb_takes_priority_over_oecd(mock_urlopen, tmp_path):
    """Countries present in ECB data must not appear with OECD as source for overlapping months."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_EMPTY_JSON, _OECD_CSV_WITH_PT)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    pt_rows = df[df["country_code"] == "PT"]
    assert (pt_rows["source"] == "ECB").all(), "ECB data must override OECD for PT"
    assert (pt_rows["inflation_rate"] != 9.9).all()


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_keeps_newer_oecd_rows_when_ecb_lags(mock_urlopen, tmp_path):
    """For overlapping countries, OECD rows newer than EU max date must be retained."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_EMPTY_JSON, _OECD_CSV_WITH_PT_NEWER)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    pt_rows = df[df["country_code"] == "PT"].sort_values("Date")

    # ECB provides up to 2024-02; OECD 2024-02 should be dropped; OECD 2024-04 kept.
    assert len(pt_rows) == 3
    assert pt_rows.iloc[0]["source"] == "ECB"
    assert pt_rows.iloc[1]["source"] == "ECB"
    assert pt_rows.iloc[2]["source"] == "OECD"
    assert pt_rows.iloc[2]["Date"] == pd.Timestamp("2024-04-01")
    assert pt_rows.iloc[2]["inflation_rate"] == 1.9


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_merges_all_sources(mock_urlopen, tmp_path):
    """Merged result must contain countries from all sources."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_JSON, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    codes = set(df["country_code"].unique())
    assert "PT" in codes   # ECB + Eurostat
    assert "U2" in codes   # ECB + Eurostat
    assert "US" in codes   # OECD
    assert "GB" in codes   # OECD


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_identifier_format(mock_urlopen, tmp_path):
    """identifier column must follow the INFLATION_{country_code} convention."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_JSON, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    expected = "INFLATION_" + df["country_code"]
    pd.testing.assert_series_equal(df["identifier"], expected, check_names=False)


@patch("stock_alert.fetchers.inflation.urllib.request.urlopen")
def test_inflation_fetcher_writes_parquet(mock_urlopen, tmp_path):
    """fetch() must persist the merged DataFrame as a parquet file."""
    mock_urlopen.side_effect = _mock_urlopen_sequence(_ECB_CSV, _EUROSTAT_JSON, _OECD_CSV)

    fetcher = InflationFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    parquet_path = tmp_path / "inflation" / "data.parquet"
    assert parquet_path.exists()
    saved = pd.read_parquet(parquet_path)
    assert len(saved) == len(df)
