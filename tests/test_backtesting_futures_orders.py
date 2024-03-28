from uuid import uuid4

import pytest
from decimal import Decimal
from basana.backtesting import exchange, liquidity
from basana.core import dt, bar
from basana.core.enums import OrderOperation
from basana.core.pair import Contract, ContractInfo
from basana.backtesting.orders import OrderState, MarketFuturesOrder, LimitFuturesOrder, StopFuturesOrder



@pytest.fixture
def order_data():
    id = "1"
    operation = OrderOperation.BUY
    contract = Contract("ES", "USD", 9500, 0.25, 50)
    quantity = Decimal("1")
    state = OrderState.OPEN
    stop_price = Decimal("5000")
    limit_price = Decimal("6000")
    return id, operation, contract, quantity, state, stop_price, limit_price


def test_market_futures_order_creation(order_data):
    id, operation, contract, quantity, state, _, _ = order_data
    order = MarketFuturesOrder(id, operation, contract, quantity, state)
    assert order.id == id
    assert order.operation == operation
    assert order.contract == contract
    assert order.quantity == quantity
    assert order.state == state


def test_limit_futures_order_creation(order_data):
    id, operation, contract, quantity, state, _, limit_price = order_data
    order = LimitFuturesOrder(id, operation, contract, quantity, limit_price, state)
    assert order.id == id
    assert order.operation == operation
    assert order.contract == contract
    assert order.quantity == quantity
    assert order.state == state


def test_stop_futures_order_creation(order_data):
    id, operation, contract, quantity, state, stop_price, _ = order_data
    order = StopFuturesOrder(id, operation, contract, quantity, stop_price, state)
    assert order.id == id
    assert order.operation == operation
    assert order.contract == contract
    assert order.quantity == quantity
    assert order.state == state


@pytest.mark.parametrize(
    "order, expected_balance_updates", [
        # Buy market
        (
            MarketFuturesOrder(uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                               OrderState.OPEN),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4000.00"),
            }
        ),
        # Buy limit
        (
            LimitFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"), Decimal("3999.50"),
                OrderState.OPEN
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-3999.50"),
            }
        ),
        # Buy limit uses open price which is better.
        (
            LimitFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("2"), Decimal("4001.00"),
                OrderState.OPEN
            ),
            {
                "ES": Decimal("2"),
                "USD": Decimal("-8000.00"),
            }
        ),
        # Buy limit price not hit.
        (
            LimitFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("2"), Decimal("3000.00"),
                OrderState.OPEN
            ),
            {}
        ),
        # Buy stop not hit.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("2"), Decimal("5000.00"),
                OrderState.OPEN
            ),
            {}
        ),
        # Buy stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                Decimal("4000.00"),
                OrderState.OPEN
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4000.00"),
            }
        ),
        # Buy stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                Decimal("3999.00"),
                OrderState.OPEN
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4000.00"),
            }
        ),
        # Buy stop hit after open.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.BUY, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"), Decimal("4001.00"),
                OrderState.OPEN
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4001.00"),
            }
        ),
        # Sell market
        (
            MarketFuturesOrder(uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                               OrderState.OPEN),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4000"),
            }
        ),
        # Sell limit
        (
            LimitFuturesOrder(
                uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                Decimal("4002.00"),
                OrderState.OPEN
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4002.00"),
            }
        ),
        # Sell limit uses open price which is better.
        (
                LimitFuturesOrder(
                    uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("2"),
                    Decimal("3999.00"),
                    OrderState.OPEN
                ),
            {
                "ES": Decimal("-2"),
                "USD": Decimal("8000.00"),
            }
        ),
        # Sell limit price not hit.
        (
            LimitFuturesOrder(
                uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                Decimal("5000.00"),
                OrderState.OPEN
            ),
            {}
        ),
        # Sell stop not hit.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("2"),
                Decimal("3000.00"),
                OrderState.OPEN
            ),
            {}
        ),
        # Sell stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                Decimal("4000.00"), OrderState.OPEN
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4000"),
            }
        ),
        # Sell stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex, OrderOperation.SELL, Contract("ES", "USD", 9500, 0.25, 50), Decimal("1"),
                Decimal("4001.00"), OrderState.OPEN
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4000.00"),
            }
        ),
        ]
)
def test_get_balance_updates_with_infinite_liquidity(order, expected_balance_updates, backtesting_dispatcher):
    e = exchange.Exchange(backtesting_dispatcher, {})  # Just for rounding purposes
    p = Contract("ES", "USD", 9500, 0.25, 50)
    e.set_pair_info(p, ContractInfo())

    ls = liquidity.InfiniteLiquidity()
    b = bar.Bar(
        dt.local_now(), p,
        Decimal("4000.00"), Decimal("4010.25"), Decimal("3980.75"), Decimal("4001.25"), Decimal("1000")
    )
    balance_updates = order.get_balance_updates(b, ls)
    # TODO: remove this line when we confirm that rounding isn't necessary
    # balance_updates = e._round_balance_updates(order.contract, balance_updates)
    assert balance_updates == expected_balance_updates