from uuid import uuid4

import pytest
from decimal import Decimal
from basana.backtesting import exchange, liquidity
from basana.core import dt, bar
from basana.core.enums import OrderOperation
from basana.core.pair import Contract, ContractInfo
from basana.backtesting.orders import (
    OrderState,
    MarketFuturesOrder,
    LimitFuturesOrder,
    StopFuturesOrder,
)
from basana.backtesting.helpers import (
    get_trade_side_quantities,
    get_base_sign_for_operation,
)


@pytest.fixture
def order_data():
    id = "1"
    operation = OrderOperation.BUY
    contract = Contract("ES", "USD", 9500, 50)
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


def test_get_trade_side_quantities():

    quantity = Decimal("10")

    # Test from zero position, should be all opening
    current_position = Decimal("0")
    for operation in [OrderOperation.BUY, OrderOperation.SELL]:
        trade_side_quantities = get_trade_side_quantities(
            current_position, operation, quantity
        )
        assert trade_side_quantities == {
            "opening_quantity": quantity,
            "closing_quantity": Decimal("0"),
        }

    # Test from same-signed position, should be all opening
    for operation in [OrderOperation.BUY, OrderOperation.SELL]:
        current_position = Decimal("10") * get_base_sign_for_operation(operation)
        trade_side_quantities = get_trade_side_quantities(
            current_position, operation, quantity
        )
        assert trade_side_quantities == {
            "opening_quantity": quantity,
            "closing_quantity": Decimal("0"),
        }

    # Test from opposite-signed position >= quantity, should be all closing
    for operation in [OrderOperation.BUY, OrderOperation.SELL]:
        current_position = Decimal("10") * -get_base_sign_for_operation(operation)
        trade_side_quantities = get_trade_side_quantities(
            current_position, operation, quantity
        )
        assert trade_side_quantities == {
            "opening_quantity": Decimal("0"),
            "closing_quantity": quantity,
        }

    # Test from opposite-signed position < quantity, should be both opening and closing
    for operation in [OrderOperation.BUY, OrderOperation.SELL]:
        current_position = Decimal("8") * -get_base_sign_for_operation(operation)
        trade_side_quantities = get_trade_side_quantities(
            current_position, operation, quantity
        )
        assert trade_side_quantities == {
            "opening_quantity": Decimal("2"),
            "closing_quantity": Decimal("8"),
        }


@pytest.mark.parametrize(
    "order, expected_balance_updates",
    [
        # Buy market
        (
            MarketFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4000.00"),
            },
        ),
        # Buy limit
        (
            LimitFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("3999.50"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-3999.50"),
            },
        ),
        # Buy limit uses open price which is better.
        (
            LimitFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                Decimal("4001.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("2"),
                "USD": Decimal("-8000.00"),
            },
        ),
        # Buy limit price not hit.
        (
            LimitFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                Decimal("3000.00"),
                OrderState.OPEN,
            ),
            {},
        ),
        # Buy stop not hit.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                Decimal("5000.00"),
                OrderState.OPEN,
            ),
            {},
        ),
        # Buy stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("4000.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4000.00"),
            },
        ),
        # Buy stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("3999.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4000.00"),
            },
        ),
        # Buy stop hit after open.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("4001.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("1"),
                "USD": Decimal("-4001.00"),
            },
        ),
        # Sell market
        (
            MarketFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4000"),
            },
        ),
        # Sell limit
        (
            LimitFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("4002.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4002.00"),
            },
        ),
        # Sell limit uses open price which is better.
        (
            LimitFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                Decimal("3999.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("-2"),
                "USD": Decimal("8000.00"),
            },
        ),
        # Sell limit price not hit.
        (
            LimitFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("5000.00"),
                OrderState.OPEN,
            ),
            {},
        ),
        # Sell stop not hit.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                Decimal("3000.00"),
                OrderState.OPEN,
            ),
            {},
        ),
        # Sell stop hit on open.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("4000.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("4000"),
            },
        ),
        # Sell stop hit after open.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("1"),
                Decimal("3999.00"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("-1"),
                "USD": Decimal("3999.00"),
            },
        ),
    ],
)
def test_get_balance_updates_with_infinite_liquidity(
    order, expected_balance_updates, backtesting_dispatcher
):
    e = exchange.Exchange(backtesting_dispatcher, {})  # Just for rounding purposes
    p = Contract("ES", "USD", 9500, 50)
    e.set_pair_info(p, ContractInfo(2, 2, 0.25))

    ls = liquidity.InfiniteLiquidity()
    b = bar.Bar(
        dt.local_now(),
        p,
        Decimal("4000.00"),
        Decimal("4010.25"),
        Decimal("3980.75"),
        Decimal("4001.25"),
        Decimal("1000"),
    )
    balance_updates = order.get_balance_updates(b, ls)
    # TODO: need to engage futures style rounding after adapting exchange to futures
    balance_updates = e._round_balance_updates(order.contract, balance_updates)
    assert balance_updates == expected_balance_updates


@pytest.mark.parametrize(
    "order, expected_balance_updates",
    [
        # Buy market but there is not enough balance.
        (
            MarketFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("2000"),
                OrderState.OPEN,
            ),
            {},
        ),
        # Buy market. Rounding takes place. 250 should be available
        (
            MarketFuturesOrder(
                uuid4().hex,
                OrderOperation.BUY,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("2"),
                "USD": Decimal("-8000.05"),
            },
        ),
        # Sell market. Rounding takes place. 250 should be available
        (
            MarketFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("2"),
                OrderState.OPEN,
            ),
            {
                "ES": Decimal("-2"),
                "USD": Decimal("7999.95"),
            },
        ),
        # Sell stop but there is not enough balance.
        (
            StopFuturesOrder(
                uuid4().hex,
                OrderOperation.SELL,
                Contract("ES", "USD", 9500, 50),
                Decimal("1004"),
                Decimal("4001.00"),
                OrderState.OPEN,
            ),
            {},
        ),
    ],
)
def test_get_balance_updates_with_finite_liquidity(
    order, expected_balance_updates, backtesting_dispatcher
):
    e = exchange.Exchange(backtesting_dispatcher, {})  # Just for rounding purposes
    p = Contract("ES", "USD", 9500, 50)
    e.set_pair_info(p, ContractInfo(2, 2, 0.25))

    ls = liquidity.VolumeShareImpact()
    b = bar.Bar(
        dt.local_now(),
        p,
        Decimal("4000.00"),
        Decimal("4100.25"),
        Decimal("3900.75"),
        Decimal("3999.50"),
        Decimal("1000"),
    )
    ls.on_bar(b)

    balance_updates = order.get_balance_updates(b, ls)
    # TODO: need to engage futures style rounding after adapting exchange to futures
    balance_updates = e._round_balance_updates(order.pair, balance_updates)
    assert balance_updates == expected_balance_updates
