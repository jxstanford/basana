import pytest

from basana.core import pair, bar
from basana.external.common.csv.bars import OHLCVTzRowParser, period_to_timedelta

bars_to_sanitize = [
    # Open < low
    {
        "datetime": "2000-12-29 00:01:00+00:00",
        "open": "1.87",
        "high": "31.31",
        "low": "28.69",
        "close": "29.06",
        "volume": "31655500",
    },
    # Open > high
    {
        "datetime": "2000-12-29 00:01:00+00:00",
        "open": "40.87",
        "high": "31.31",
        "low": "28.69",
        "close": "29.06",
        "volume": "31655500",
    },
    # high < low
    {
        "datetime": "2000-12-29 00:01:00+00:00",
        "open": "10",
        "high": "1",
        "low": "20",
        "close": "10",
        "volume": "31655500",
    },
    # high < Close
    {
        "datetime": "2000-12-29 00:01:00+00:00",
        "open": "30.87",
        "high": "31.31",
        "low": "28.69",
        "close": "60.06",
        "volume": "31655500",
    },
    # low > close
    {
        "datetime": "2000-12-29 00:01:00+00:00",
        "open": "30.87",
        "high": "31.31",
        "low": "28.69",
        "close": "27.06",
        "volume": "31655500",
    },
]


@pytest.mark.parametrize("row_dict", bars_to_sanitize)
def test_bars_need_sanitization(row_dict):
    row_parser = OHLCVTzRowParser(
        pair.Contract("ORCL", "USD", 0, 1), timedelta=period_to_timedelta["1d"]
    )
    with pytest.raises(bar.InvalidBar):
        row_parser.parse_row(row_dict)


@pytest.mark.parametrize("row_dict", bars_to_sanitize)
def test_row_parser_sanitization(row_dict):
    row_parser = OHLCVTzRowParser(
        pair.Contract("ORCL", "USD", 0, 1), timedelta=period_to_timedelta["1d"]
    )
    row_parser.sanitize = True
    row_parser.parse_row(row_dict)
