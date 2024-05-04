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
from unittest.mock import patch, PropertyMock

from basana.backtesting import account_balances, orders
from basana.core import dt, pair


def test_symbols():
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(8000)})
    assert balances.get_symbols() == ["USD"]

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 9500, 50),
        Decimal("2"),
        orders.OrderState.OPEN,
    )
    balances.order_accepted(order, {"USD": Decimal("8000")})
    assert balances.get_symbols() == ["USD"]

    order.add_fill(dt.utc_now(), {"ES": Decimal("1"), "USD": Decimal("-4000")}, {})
    balances.order_updated(order, {"ES": Decimal("1"), "USD": Decimal("-4000")})
    symbols = balances.get_symbols()
    symbols.sort()
    assert symbols == ["ES", "USD"]
    assert balances.get_available_balance("USD") == 0


def test_order_gets_completed():
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(100000)})

    assert balances.get_available_balance("USD") == Decimal(100000)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_margin("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order("1", "USD") == Decimal(0)

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 10000, 50),
        Decimal("4"),
        orders.OrderState.OPEN,
        opening_quantity=Decimal("4"),
    )
    balances.order_accepted(order, {"USD": Decimal("10")})
    balances.order_margin_accepted(
        order,
        {"USD": order.opening_quantity * Decimal(order.contract.margin_requirement)},
    )

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(10)
    assert balances.get_balance_on_margin("USD") == Decimal(40000)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(10)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(40000)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal("-5")})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(5)
    assert balances.get_balance_on_margin("USD") == Decimal(40000)
    assert balances.get_available_balance("ES") == Decimal("2")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(40000)

    balances.order_updated(order, {"ES": Decimal("1"), "USD": Decimal(-2.5)})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(2.5)
    assert balances.get_balance_on_margin("USD") == Decimal(40000)
    assert balances.get_available_balance("ES") == Decimal(3)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(2.5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(40000)

    balances.order_updated(order, {"ES": Decimal("1"), "USD": Decimal("-2.5")})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(40000)
    assert balances.get_available_balance("ES") == Decimal("4")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(40000)


def test_order_gets_canceled():
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(100_000)})

    assert balances.get_available_balance("USD") == Decimal(100_000)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order("1", "USD") == Decimal(0)

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 9500, 50),
        Decimal("2"),
        orders.OrderState.OPEN,
        opening_quantity=Decimal("2"),
    )
    balances.order_accepted(order, {"USD": Decimal("5")})
    balances.order_margin_accepted(
        order,
        {"USD": order.opening_quantity * Decimal(order.contract.margin_requirement)},
    )

    assert balances.get_available_balance("USD") == Decimal(99995)
    assert balances.get_balance_on_hold("USD") == Decimal(5)
    assert balances.get_balance_on_margin("USD") == Decimal(19000)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(19000)

    balances.order_updated(order, {"ES": Decimal("1"), "USD": Decimal("-2.50")})

    assert balances.get_available_balance("USD") == Decimal(99_995)
    assert balances.get_balance_on_hold("USD") == Decimal(2.50)
    assert balances.get_balance_on_margin("USD") == Decimal(19000)
    assert balances.get_available_balance("ES") == Decimal("1")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(2.50)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(19000)

    order.cancel()
    with patch(
        "basana.backtesting.orders.MarketFuturesOrder.quantity_filled",
        new_callable=PropertyMock,
    ) as mock_quantity_filled:
        mock_quantity_filled.return_value = Decimal("1")
        # Inside this block, order.quantity_filled will return Decimal('1')
        balances.order_updated(order, {})

        assert balances.get_available_balance("USD") == Decimal(99_997.50)
        assert balances.get_balance_on_hold("USD") == Decimal(0)
        assert balances.get_balance_on_margin("USD") == Decimal(9500)
        assert balances.get_available_balance("ES") == Decimal(1)
        assert balances.get_balance_on_hold("ES") == Decimal(0)
        assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(0)
        assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(
            9500
        )


def test_order_no_opening_quantity_completed():
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(100000)})

    assert balances.get_available_balance("USD") == Decimal(100000)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_margin("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order("1", "USD") == Decimal(0)

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 10000, 50),
        Decimal("4"),
        orders.OrderState.OPEN,
        opening_quantity=Decimal("0"),
        closing_quantity=Decimal("4"),
    )
    balances.order_accepted(order, {"USD": Decimal("10")})
    balances.order_margin_accepted(
        order,
        {"USD": order.opening_quantity * Decimal(order.contract.margin_requirement)},
    )

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(10)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(10)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(0)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal("-5")})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(5)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal("2")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(0)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal(-5)})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(4)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(0)


def test_order_no_opening_quantity_canceled():
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(100000)})

    assert balances.get_available_balance("USD") == Decimal(100000)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_margin("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order("1", "USD") == Decimal(0)

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 10000, 50),
        Decimal("4"),
        orders.OrderState.OPEN,
        opening_quantity=Decimal("0"),
        closing_quantity=Decimal("4"),
    )
    balances.order_accepted(order, {"USD": Decimal("10")})
    balances.order_margin_accepted(
        order,
        {"USD": order.opening_quantity * Decimal(order.contract.margin_requirement)},
    )

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(10)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(10)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(0)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal("-5")})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(5)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal("2")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(0)

    order.cancel()
    balances.order_updated(order, {})

    assert balances.get_available_balance("USD") == Decimal(99995)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(2)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(0)


def test_order_some_opening_quantity_completed():
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(100000)})

    assert balances.get_available_balance("USD") == Decimal(100000)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_margin("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 10000, 50),
        Decimal("4"),
        orders.OrderState.OPEN,
        opening_quantity=Decimal("3"),
        closing_quantity=Decimal("1"),
    )
    balances.order_accepted(order, {"USD": Decimal("10")})
    balances.order_margin_accepted(
        order,
        {"USD": order.opening_quantity * Decimal(order.contract.margin_requirement)},
    )

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(10)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(10)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(30000)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal("-5")})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(5)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)
    assert balances.get_available_balance("ES") == Decimal("2")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(30000)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal(-5)})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)
    assert balances.get_available_balance("ES") == Decimal(4)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(30000)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)


def test_order_some_opening_quantity_canceled(monkeypatch):
    balances = account_balances.FuturesAccountBalances({"USD": Decimal(100000)})

    assert balances.get_available_balance("USD") == Decimal(100000)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_margin("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order("1", "USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(0)

    monkeypatch.setattr(orders.MarketFuturesOrder, "quantity_filled", Decimal(2))

    order = orders.MarketFuturesOrder(
        "1",
        orders.OrderOperation.BUY,
        pair.Contract("ES", "USD", 10000, 50),
        Decimal("4"),
        orders.OrderState.OPEN,
        opening_quantity=Decimal("3"),
        closing_quantity=Decimal("1"),
    )

    balances.order_accepted(order, {"USD": Decimal("10")})
    balances.order_margin_accepted(
        order,
        {"USD": order.opening_quantity * Decimal(order.contract.margin_requirement)},
    )

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(10)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)
    assert balances.get_available_balance("ES") == Decimal(0)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(10)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(30000)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)

    balances.order_updated(order, {"ES": Decimal("2"), "USD": Decimal("-5")})

    assert balances.get_available_balance("USD") == Decimal(99990)
    assert balances.get_balance_on_hold("USD") == Decimal(5)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)
    assert balances.get_available_balance("ES") == Decimal("2")
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(5)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(30000)
    assert balances.get_balance_on_margin("USD") == Decimal(30000)

    order.cancel()
    balances.order_updated(order, {})

    assert balances.get_available_balance("USD") == Decimal(99995)
    assert balances.get_balance_on_hold("USD") == Decimal(0)
    assert balances.get_balance_on_margin("USD") == Decimal(20000)
    assert balances.get_available_balance("ES") == Decimal(2)
    assert balances.get_balance_on_hold("ES") == Decimal(0)
    assert balances.get_balance_on_hold_for_order(order.id, "USD") == Decimal(0)
    assert balances.get_balance_on_margin_for_order(order.id, "USD") == Decimal(20000)
    assert balances.get_balance_on_margin("USD") == Decimal(20000)
