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

from decimal import Decimal
from typing import Dict
import itertools

from basana.core.enums import OrderOperation


ZERO = Decimal(0)


def add_amounts(lhs: Dict[str, Decimal], rhs: Dict[str, Decimal]) -> Dict[str, Decimal]:
    keys = set(itertools.chain(lhs.keys(), rhs.keys()))
    ret = {key: lhs.get(key, ZERO) + rhs.get(key, ZERO) for key in keys}
    return ret


def remove_empty_amounts(amounts: Dict[str, Decimal]) -> Dict[str, Decimal]:
    return {key: value for key, value in amounts.items() if value}


def copy_sign(x: Decimal, y: Decimal) -> Decimal:
    assert isinstance(x, Decimal)
    assert isinstance(y, Decimal)

    ret = x
    if x > ZERO and y < ZERO or x < ZERO and y > ZERO:
        ret = -x
    return ret


def get_sign(value: Decimal) -> Decimal:
    return copy_sign(Decimal(1), value)


def get_base_sign_for_operation(operation: OrderOperation) -> Decimal:
    if operation == OrderOperation.BUY:
        base_sign = Decimal(1)
    else:
        assert operation == OrderOperation.SELL
        base_sign = Decimal(-1)
    return base_sign


def get_trade_side_quantities(
    current_position, operation, quantity
) -> Dict[str, Decimal]:
    # Determine the sign of the operation
    operation_sign = get_base_sign_for_operation(operation)

    # If the current position and operation are of the same sign, or the current position is zero
    if current_position * operation_sign >= 0:
        return {"opening_quantity": quantity, "closing_quantity": Decimal("0")}

    # If the current position and operation are of opposite signs
    else:
        # If the absolute value of the current position is greater than or equal to the quantity
        if abs(current_position) >= quantity:
            return {"opening_quantity": Decimal("0"), "closing_quantity": quantity}
        # If the absolute value of the current position is less than the quantity
        else:
            return {
                "opening_quantity": quantity - abs(current_position),
                "closing_quantity": abs(current_position),
            }
