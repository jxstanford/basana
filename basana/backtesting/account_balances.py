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
        assert (
            order.id in self._holds_by_order
        ), "The order was not accepted or it was already removed"

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
            self._holds_by_order[order.id] = add_amounts(
                self._holds_by_order[order.id], hold_updates
            )
        else:
            # Release everything that was on hold.
            hold_updates = {
                symbol: -amount
                for symbol, amount in self._holds_by_order.pop(order.id).items()
            }

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
        self._margins_by_symbol: Dict[str, Decimal] = {}
        self._margins_by_order: Dict[str, Dict[str, Decimal]] = {}
        super().__init__(initial_balances)

    def _get_hold_symbol(self, order: orders.Order):
        return order.pair.quote_symbol

    def _get_margin_symbol(self, order: orders.FuturesOrder):
        return order.contract.quote_symbol

    def get_balance_on_margin(self, symbol: str) -> Decimal:
        return self._margins_by_symbol.get(symbol, Decimal(0))

    def get_balance_on_margin_for_order(self, order_id: str, symbol: str) -> Decimal:
        return self._margins_by_order.get(order_id, {}).get(symbol, Decimal(0))

    # TODO: refactor margin handling into order_accepted method
    def order_margin_accepted(
        self, order: orders.Order, required_margin_balance: Dict[str, Decimal]
    ):
        assert isinstance(order, orders.FuturesOrder)
        assert order.is_open, "The order is not open"
        assert order.id not in self._margins_by_order, "The order was already accepted"

        # When an order gets accepted we need to hold any required balance that will be debited as the order gets
        # filled.
        symbol = self._get_margin_symbol(order)
        margin_amount = required_margin_balance.get(symbol, Decimal(0))

        margins = {symbol: margin_amount}
        self._margins_by_symbol = add_amounts(self._margins_by_symbol, margins)
        self._margins_by_order[order.id] = margins

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
        assert isinstance(order, orders.FuturesOrder)
        assert (
            order.id in self._holds_by_order
        ), "The order was not accepted or it was already removed"

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
            self._holds_by_order[order.id] = add_amounts(
                self._holds_by_order[order.id], hold_updates
            )
        else:
            # Release everything that was on hold.
            hold_updates = {
                symbol: -amount
                for symbol, amount in self._holds_by_order.pop(order.id).items()
            }

        # Update holds for the symbol.
        self._holds_by_symbol = add_amounts(self._holds_by_symbol, hold_updates)

        # Update margins for the order.
        symbol = self._get_margin_symbol(order)
        if order.is_open:
            if order.opening_quantity == 0:
                # If the order is not opening any quantity, we don't need to update the margins.
                return
            amount_on_margin = self._margins_by_order[order.id][symbol]
            new_amount_on_margin = order.opening_quantity * Decimal(
                order.contract.margin_requirement
            )
            margin_updates = {symbol: new_amount_on_margin - amount_on_margin}

            self._margins_by_order[order.id] = add_amounts(
                self._margins_by_order[order.id], margin_updates
            )
            self._margins_by_symbol = add_amounts(
                self._margins_by_symbol, margin_updates
            )
        else:
            # Release everything that wasn't filled
            quantity = min(order.opening_quantity, order.quantity_filled)
            amount_on_margin = self._margins_by_order.get(order.id, {}).get(
                symbol, Decimal(0)
            )
            new_amount_on_margin = quantity * Decimal(order.contract.margin_requirement)
            margin_updates = {symbol: new_amount_on_margin - amount_on_margin}

            self._margins_by_order[order.id] = add_amounts(
                self._margins_by_order.get(order.id, {}), margin_updates
            )
            self._margins_by_symbol = add_amounts(
                self._margins_by_symbol, margin_updates
            )
