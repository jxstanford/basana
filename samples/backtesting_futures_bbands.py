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

# Bars can be downloaded using this command:
# python -m basana.external.binance.tools.download_bars -c BTC/USDT -p 1d -s 2021-01-01 -e 2021-12-31 > \
# binance_btcusdt_day.csv

from decimal import Decimal
import asyncio
import logging

from basana.backtesting import charts
from basana.core.pair import Contract, ContractInfo
from basana.external.common.csv.bars import OHLCVTzBarSource
import basana as bs
import basana.backtesting.exchange as backtesting_exchange
import bbands


class PositionManager:
    def __init__(self, exchange: backtesting_exchange.FuturesExchange, target_trade_size: Decimal,
                 max_position_size: Decimal):
        assert target_trade_size > 0
        assert max_position_size >= target_trade_size
        self._exchange = exchange
        self._target_trade_size = target_trade_size
        self._max_position_size = max_position_size

    async def on_trading_signal(self, trading_signal: bs.TradingSignal):
        logging.info("Trading signal: operation=%s contract=%s", trading_signal.operation,
                     trading_signal.pair)
        try:
            # Calculate the order size.
            order_size = await self._adjusted_order_size(trading_signal)
            if not order_size:
                return
            logging.info(
                "Creating %s market order for %s: amount=%s", trading_signal.operation,
                trading_signal.pair,
                order_size)

            await self._exchange.create_market_order(trading_signal.operation, trading_signal.pair, order_size)
        except Exception as e:
            logging.error(e)

    async def _adjusted_order_size(self, trading_signal: bs.TradingSignal) -> Decimal:
        operation = trading_signal.operation
        symbol = trading_signal.pair.base_symbol
        balance = await self._exchange.get_balance(symbol)
        balance = balance.available
        target_position_size = self._target_trade_size
        max_position_size = self._max_position_size
        order_size = target_position_size

        if operation == bs.OrderOperation.SELL:
            balance *= -1

        if balance + target_position_size < target_position_size:
            order_size = target_position_size + abs(balance)
        elif balance + target_position_size > max_position_size:
            order_size = max_position_size - abs(balance)
        return order_size


async def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    event_dispatcher = bs.backtesting_dispatcher()
    contract = Contract("ES", "USD", 9500, 50)
    exchange = backtesting_exchange.FuturesExchange(
        event_dispatcher,
        initial_balances={"ES": Decimal(0), "USD": Decimal(100_000)}
    )
    exchange.set_contract_info(contract, ContractInfo(base_precision=0, quote_precision=2, price_increment=0.25))

    # Connect the strategy to the bar events from the exchange.
    strategy = bbands.Strategy(event_dispatcher, 10, 1.5)
    exchange.subscribe_to_bar_events(contract, strategy.on_bar_event)

    # Connect the position manager to the strategy signals.
    position_mgr = PositionManager(exchange, Decimal(1), Decimal(1))
    strategy.subscribe_to_trading_signals(position_mgr.on_trading_signal)

    # Load bars from CSV files.
    exchange.add_bar_source(OHLCVTzBarSource(contract, "data/ES_0102224_rth.csv", "1m"))

    # Setup chart.
    chart = charts.LineCharts(exchange)
    chart.add_pair(contract)
    chart.add_pair_indicator("Upper", contract, lambda _: strategy.bb[-1].ub if len(strategy.bb) else None)
    chart.add_pair_indicator("Central", contract, lambda _: strategy.bb[-1].cb if len(strategy.bb) else None)
    chart.add_pair_indicator("Lower", contract, lambda _: strategy.bb[-1].lb if len(strategy.bb) else None)
    chart.add_portfolio_value("USD")

    # Run the backtest.
    await event_dispatcher.run()

    # Log balances.
    balances = await exchange.get_balances()
    for currency, balance in balances.items():
        logging.info("%s balance: %s", currency, balance.available)

    chart.show()


if __name__ == "__main__":
    asyncio.run(main())
