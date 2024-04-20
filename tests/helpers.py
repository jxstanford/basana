# Basana
#
# Copyright 2022-2023 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import contextlib
import json
import os
import tempfile
import time
import pytest
from decimal import Decimal

from basana.core import helpers


def abs_data_path(filename):
    return os.path.join(os.path.split(__file__)[0], "data", filename)


def load_json(filename):
    return json.load(open(abs_data_path(filename)))


def safe_round(v, precision):
    if v is not None:
        v = helpers.round_decimal(v, precision)
    return v


async def wait_until(condition, timeout=10, retry_after=0.25):
    begin = time.time()
    ret = condition()
    while not ret and (time.time() - begin) < timeout:
        await asyncio.sleep(retry_after)
        ret = condition()
    return ret


async def wait_caplog(text, caplog, timeout=10, retry_after=0.25):
    return await wait_until(
        lambda: text in caplog.text, timeout=timeout, retry_after=retry_after
    )


def assert_expected_attrs(object, expected):
    for key, expected_value in expected.items():
        actual_value = getattr(object, key)
        assert actual_value == expected_value, "Mismatch in {}. {} != {}".format(
            key, actual_value, expected_value
        )


def is_sorted(seq):
    return all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))


@contextlib.contextmanager
def temp_file_name(suffix: str = None, delete: bool = True) -> str:
    # On Windows the name can't used to open the file a second time. That is why we're using this only to generate
    # the file name.
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        pass
    try:
        yield tmp_file.name
    finally:
        if delete:
            os.remove(tmp_file.name)


@pytest.mark.parametrize(
    "value, increment, precision, expected",
    [
        (Decimal("1.5"), Decimal("1"), 0, Decimal("2")),
        (Decimal("1.4"), Decimal("1"), 0, Decimal("1")),
        (Decimal("1.6"), Decimal("0.5"), 1, Decimal("1.5")),
        (Decimal("1.75"), Decimal("0.5"), 1, Decimal("2.0")),
        (Decimal("1.12345"), Decimal("0.00001"), 5, Decimal("1.12345")),
        (Decimal("1.12345"), Decimal("0.00001"), 4, Decimal("1.1234")),
        (Decimal("1.770"), Decimal("0.25"), 2, Decimal("1.75")),
        (Decimal("1.950"), Decimal("0.25"), 2, Decimal("2.00")),
    ],
)
def test_round_decimal_to_increment(value, increment, precision, expected):
    assert helpers.round_decimal_to_increment(value, increment, precision) == expected


@pytest.mark.parametrize(
    "value, increment, precision",
    [
        (Decimal("1.5"), Decimal("0"), 0),
        (Decimal("1.4"), Decimal("-1"), 0),
        (Decimal("1.6"), Decimal("0.5"), -1),
    ],
)
def test_round_decimal_to_increment_invalid_parameters(value, increment, precision):
    with pytest.raises(ValueError):
        helpers.round_decimal_to_increment(value, increment, precision)
