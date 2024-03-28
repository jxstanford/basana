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
from typing import Dict, List
import copy

from basana.backtesting import orders
from basana.backtesting.helpers import add_amounts


class AccountBalances:
    def __init__(self, initial_balances: Dict[str, Decimal]):
        self._balances: Dict[str, Decimal] = copy.copy(initial_balances)
        # Balances that are reserved to be used as the order gets filled.
        self._holds_by_symbol: Dict[str, Decimal] = {}
        self._holds_by_order: Dict[str, Dict[str, Decimal]] = {}

    def get_symbols(self) -> List[str]:
        symbols = set(self._balances.keys())
        symbols.update(self._holds_by_symbol.keys())
        return list(symbols)

    def get_available_balance(self, symbol: str) -> Decimal:
        return self._balances.get(symbol, Decimal(0)) - self.get_balance_on_hold(symbol)

    def get_balance_on_hold(self, symbol: str) -> Decimal:
        return self._holds_by_symbol.get(symbol, Decimal(0))

    def get_balance_on_hold_for_order(self, order_id: str, symbol: str) -> Decimal:
        return self._holds_by_order.get(order_id, {}).get(symbol, Decimal(0))

    def order_accepted(self, order: orders.Order, required_balance: Dict[str, Decimal]):
        assert order.is_open, "The order is not open"
        assert order.id not in self._holds_by_order, "The order was already accepted"

        # When an order gets accepted we need to hold any required balance that will be debited as the order gets
        # filled.
        symbol = self._get_hold_symbol(order)
        hold_amount = required_balance.get(symbol, Decimal(0))
        assert hold_amount >= Decimal(0), f"Invalid hold amount {hold_amount}"
        holds = {symbol: hold_amount}
        self._holds_by_symbol = add_amounts(self._holds_by_symbol, holds)
        self._holds_by_order[order.id] = holds

    def order_updated(self, order: orders.Order, balance_updates: Dict[str, Decimal]):
        assert order.id in self._holds_by_order, "The order was not accepted or it was already removed"

        # Update balances.
        self._balances = add_amounts(self._balances, balance_updates)

        # Update holds for the order.
        symbol = self._get_hold_symbol(order)
        if order.is_open:
            # Release whatever was spent, but no more than what was on hold for this order.
            amount_on_hold = self._holds_by_order[order.id][symbol]
            amount_spent = balance_updates.get(symbol, Decimal(0))
            assert amount_spent <= Decimal(0), f"Invalid amount spent {amount_spent}"
            hold_updates = {symbol: max(-amount_on_hold, amount_spent)}
            self._holds_by_order[order.id] = add_amounts(self._holds_by_order[order.id], hold_updates)
        else:
            # Release everything that was on hold.
            hold_updates = {symbol: -amount for symbol, amount in self._holds_by_order.pop(order.id).items()}

        # Update holds for the symbol.
        self._holds_by_symbol = add_amounts(self._holds_by_symbol, hold_updates)

    def _get_hold_symbol(self, order: orders.Order):
        if order.operation == orders.OrderOperation.BUY:
            symbol = order.pair.quote_symbol
        else:
            assert order.operation == orders.OrderOperation.SELL
            symbol = order.pair.base_symbol
        return symbol

class FuturesAccountBalances(AccountBalances):
    def __init__(self, initial_balances: Dict[str, Decimal]):
        super().__init__(initial_balances)



    def calculate_pnl(
        self,
        opening_order: orders.Order,
        closing_order: orders.Order,
        price: Decimal
    ) -> Decimal:
        assert opening_order.is_open, "The opening order is not open"
        assert closing_order.is_closed, "The closing order is not closed"
        assert opening_order.pair == closing_order.pair, "The opening and closing orders are for different pairs"
        assert opening_order.operation != closing_order.operation, "The opening and closing orders have the same operation"
        assert opening_order.operation == orders.OrderOperation.BUY, "The opening order is not a buy order"
        assert closing_order.operation == orders.OrderOperation.SELL, "The closing order is not a sell order"

        # Calculate the PnL.
        amount = min(opening_order.amount, closing_order.amount)
        opening_price = opening_order.price
        closing_price = closing_order.price
        pnl = (closing_price - opening_price) * amount
        return pnl

    def order_closed(self, order: orders.Order, pnl: Decimal):
        assert order.id in self._holds_by_order, "The order was not accepted or it was already removed"

        # Release everything that was on hold.
        hold_updates = {symbol: -amount for symbol, amount in self._holds_by_order.pop(order.id).items()}

        # Update holds for the symbol.
        self._holds_by_symbol = add_amounts(self._holds_by_symbol, hold_updates)

        # Update balances.
        balance_updates = {order.pair.quote_symbol: pnl}
        self._balances = add_amounts(self._balances, balance_updates)

        # Update the order state.
        order.closed(pnl)

    def order_rejected(self, order: orders.Order):
        assert order.id in self._holds_by_order, "The order was not accepted or it was already removed"

        # Release everything that was on hold.
        hold_updates = {symbol: -amount for symbol, amount in self._holds_by_order.pop(order.id).items()}

        # Update holds for the symbol.
        self._holds_by_symbol = add_amounts(self._holds_by_symbol, hold_updates)

        # Update the order state.
        order.rejected()

    def _get_hold_symbol(self, order: orders.Order):
        return order.pair.quote_symbol