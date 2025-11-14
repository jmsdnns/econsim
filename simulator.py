"""
Economic Simulator with LLM-powered agents
A simple marketplace where agents buy and sell goods using Claude for decision-making
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

from anthropic import Anthropic

MODEL = "claude-3-5-haiku-20241022"  # fast and cheap
MAX_TOKENS = 200
TEMPERATURE = 0.7  # some randomness


class OrderType(Enum):
    """Type of market order"""

    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """A buy or sell order"""

    agent_id: str
    order_type: OrderType
    quantity: int
    price: float

    def __repr__(self):
        return f"{self.order_type.value.upper()} {self.quantity} @ ${self.price:.2f} (agent: {self.agent_id})"


@dataclass
class Trade:
    """Represents an executed trade between two agents"""

    buyer_id: str
    seller_id: str
    quantity: int
    price: float
    round_number: int

    def __repr__(self):
        return f"Round {self.round_number}: {self.buyer_id} bought {self.quantity} from {self.seller_id} @ ${self.price:.2f}"


@dataclass
class Agent:
    """
    An economic agent that can buy and sell goods in the marketplace.
    """

    agent_id: str
    role: Literal["buyer", "seller", "market_maker"]
    money: float
    inventory: int
    personality: str
    transaction_history: list[Trade] = field(default_factory=list)

    def can_buy(self, quantity: int, price: float) -> bool:
        """Check if agent has enough money to buy"""
        total_cost = quantity * price
        return self.money >= total_cost

    def can_sell(self, quantity: int) -> bool:
        """Check if agent has enough inventory to sell"""
        return self.inventory >= quantity

    def execute_buy(self, quantity: int, price: float, trade: Trade):
        """Execute a buy transaction"""
        total_cost = quantity * price
        if not self.can_buy(quantity, price):
            raise ValueError(
                f"{self.agent_id} cannot afford to buy {quantity} @ ${price}"
            )

        self.money -= total_cost
        self.inventory += quantity
        self.transaction_history.append(trade)

    def execute_sell(self, quantity: int, price: float, trade: Trade):
        """Execute a sell transaction"""
        if not self.can_sell(quantity):
            raise ValueError(f"{self.agent_id} doesn't have {quantity} to sell")

        total_revenue = quantity * price
        self.money += total_revenue
        self.inventory -= quantity
        self.transaction_history.append(trade)

    def get_state_summary(self) -> dict:
        """Get current state of the agent"""
        recent_trades = (
            self.transaction_history[-3:] if self.transaction_history else []
        )
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "money": round(self.money, 2),
            "inventory": self.inventory,
            "recent_trades": len(recent_trades),
            "avg_recent_price": round(
                sum(t.price for t in recent_trades) / len(recent_trades), 2
            )
            if recent_trades
            else None,
        }

    def make_decision(
        self, market_summary: dict, client: Anthropic, debug: bool = False
    ) -> Optional[Order]:
        """
        Use Claude to make a trading decision based on current market conditions.

        Args:
            market_summary: Current market state from Market.get_market_summary()
            client: Anthropic API client
            debug: If True, print the prompt and Claude's full response

        Returns:
            Order if agent wants to trade, None if agent wants to hold
        """
        prompt = self._build_decision_prompt(market_summary)

        if debug:
            print(f"\n{'=' * 70}")
            print(f"DEBUG: Prompt for {self.agent_id}")
            print(f"{'=' * 70}")
            print(prompt)
            print(f"{'=' * 70}\n")

        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text

            if debug:
                print(f"{'~' * 70}")
                print(f"DEBUG: Claude's response for {self.agent_id}")
                print(f"{'~' * 70}")
                print(response_text)
                print(f"{'~' * 70}\n")

            decision = self._parse_decision(response_text)

            return decision

        except Exception as e:
            print(f"Error getting decision for {self.agent_id}: {e}")
            return None

    def _build_decision_prompt(self, market_summary: dict) -> str:
        """Build the prompt for Claude to make a trading decision"""

        # format recent trades for context in prompt
        recent_trades_desc = "No recent trades yet."
        if self.transaction_history:
            recent = self.transaction_history[-3:]
            trade_desc = []
            for t in recent:
                if t.buyer_id == self.agent_id:
                    trade_desc.append(f"Bought {t.quantity} @ ${t.price:.2f}")
                else:
                    trade_desc.append(f"Sold {t.quantity} @ ${t.price:.2f}")
            recent_trades_desc = "; ".join(trade_desc)

        prompt = f"""You are an economic agent in a marketplace trading {market_summary["commodity"]}.

YOUR STATE:
- Role: {self.role}
- Money: ${self.money:.2f}
- Inventory: {self.inventory} units
- Personality: {self.personality}
- Recent trades: {recent_trades_desc}

MARKET CONDITIONS (Round {market_summary["round"]}):
- Last traded price: {f"${market_summary['last_price']:.2f}" if market_summary["last_price"] else "N/A"}
- Average recent price: {f"${market_summary['avg_recent_price']:.2f}" if market_summary["avg_recent_price"] else "N/A"}
- Pending buy orders: {market_summary["pending_buy_orders"]}
- Pending sell orders: {market_summary["pending_sell_orders"]}

TASK:
Decide whether to BUY, SELL, or HOLD this round. Consider your role, current inventory, available money, and market conditions.

Respond with ONLY a JSON object in this exact format:
{{"action": "buy", "quantity": 10, "price": 12.50, "reasoning": "brief explanation"}}
OR
{{"action": "sell", "quantity": 5, "price": 11.00, "reasoning": "brief explanation"}}
OR
{{"action": "hold", "reasoning": "brief explanation"}}

Ensure quantities and prices are realistic given your constraints."""

        return prompt

    def _parse_decision(self, response_text: str) -> Optional[Order]:
        """Parse Claude's response into an Order or None"""
        try:
            # a hack to extract json without any surrounding text
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                return None

            json_str = response_text[start:end]
            decision = json.loads(json_str)

            action = decision.get("action", "").lower()

            if action == "hold":
                return None

            if action == "buy":
                quantity = int(decision["quantity"])
                price = float(decision["price"])

                # can afford it
                if not self.can_buy(quantity, price):
                    print(
                        f"  {self.agent_id} tried to buy {quantity} @ ${price} but can't afford it (has ${self.money:.2f})"
                    )
                    return None

                return Order(self.agent_id, OrderType.BUY, quantity, price)

            elif action == "sell":
                quantity = int(decision["quantity"])
                price = float(decision["price"])

                # has enough to sell quantity
                if not self.can_sell(quantity):
                    print(
                        f"  {self.agent_id} tried to sell {quantity} but only has {self.inventory}"
                    )
                    return None

                return Order(self.agent_id, OrderType.SELL, quantity, price)

            return None

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"  Error parsing decision for {self.agent_id}: {e}")
            print(f"  Response was: {response_text}")
            return None

    def __repr__(self):
        return f"Agent({self.agent_id}, role={self.role}, money=${self.money:.2f}, inventory={self.inventory})"


class Market:
    """
    A simple marketplace that matches buy and sell orders.
    Uses a basic order matching algorithm: highest bid meets lowest ask.
    """

    def __init__(self, commodity_name: str = "wheat"):
        self.commodity_name = commodity_name
        self.buy_orders: list[Order] = []
        self.sell_orders: list[Order] = []
        self.trade_history: list[Trade] = []
        self.current_round: int = 0

    def submit_order(self, order: Order):
        """Submit a buy or sell order to the market"""
        if order.order_type == OrderType.BUY:
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)

    def clear_orders(self):
        """Clear all pending orders (called after matching)"""
        self.buy_orders = []
        self.sell_orders = []

    def match_orders(self, agents: dict[str, Agent]) -> list[Trade]:
        """
        Match buy and sell orders and execute trades.
        Algorithm: Sort buy orders (highest first) and sell orders (lowest first),
        then match compatible orders.

        Args:
            agents: Dictionary of agent_id -> Agent for executing trades

        Returns:
            List of executed trades
        """
        # sort orders by price: buy orders (descending), sell orders (ascending)
        buy_orders = sorted(self.buy_orders, key=lambda o: o.price, reverse=True)
        sell_orders = sorted(self.sell_orders, key=lambda o: o.price)

        executed_trades = []

        # match orders
        while buy_orders and sell_orders:
            buy_order = buy_orders[0]
            sell_order = sell_orders[0]

            # check if orders can be matched (buy price >= sell price)
            if buy_order.price < sell_order.price:
                break  # No more matches possible

            # get agents
            buyer = agents[buy_order.agent_id]
            seller = agents[sell_order.agent_id]

            # determine trade quantity (minimum of both orders)
            trade_quantity = min(buy_order.quantity, sell_order.quantity)

            # trade price is the average of bid and ask (basic price discovery)
            trade_price = (buy_order.price + sell_order.price) / 2

            # verify agents can execute trade
            if not buyer.can_buy(trade_quantity, trade_price):
                # buyer can't afford, remove buy order
                buy_orders.pop(0)
                continue
            if not seller.can_sell(trade_quantity):
                # seller doesn't have inventory, remove sell order
                sell_orders.pop(0)
                continue

            # DO IT!
            trade = Trade(
                buyer_id=buy_order.agent_id,
                seller_id=sell_order.agent_id,
                quantity=trade_quantity,
                price=trade_price,
                round_number=self.current_round,
            )

            buyer.execute_buy(trade_quantity, trade_price, trade)
            seller.execute_sell(trade_quantity, trade_price, trade)

            executed_trades.append(trade)
            self.trade_history.append(trade)

            # update or remove orders
            buy_order.quantity -= trade_quantity
            sell_order.quantity -= trade_quantity

            if buy_order.quantity == 0:
                buy_orders.pop(0)
            if sell_order.quantity == 0:
                sell_orders.pop(0)

        return executed_trades

    def get_market_summary(self) -> dict:
        """Get current market state summary"""
        recent_trades = self.trade_history[-5:] if self.trade_history else []

        return {
            "round": self.current_round,
            "commodity": self.commodity_name,
            "pending_buy_orders": len(self.buy_orders),
            "pending_sell_orders": len(self.sell_orders),
            "recent_trades": len(recent_trades),
            "last_price": recent_trades[-1].price if recent_trades else None,
            "avg_recent_price": round(
                sum(t.price for t in recent_trades) / len(recent_trades), 2
            )
            if recent_trades
            else None,
            "total_volume": sum(t.quantity for t in recent_trades),
        }

    def __repr__(self):
        return f"Market({self.commodity_name}, round={self.current_round}, trades={len(self.trade_history)})"


# example usage
if __name__ == "__main__":
    print("=== Economic Simulator - Core Classes Demo ===\n")

    # create agents with distinct personalities
    agents = {
        "alice": Agent(
            agent_id="alice",
            role="seller",
            money=100.0,
            inventory=50,
            personality="Conservative seller, prefers higher prices",
        ),
        "bob": Agent(
            agent_id="bob",
            role="buyer",
            money=500.0,
            inventory=0,
            personality="Eager buyer, willing to pay fair prices",
        ),
        "charlie": Agent(
            agent_id="charlie",
            role="seller",
            money=200.0,
            inventory=30,
            personality="Aggressive seller, wants to move inventory quickly",
        ),
    }

    # create market
    market = Market(commodity_name="wheat")

    # simulate a round with manual orders
    print("Round 1: Submitting orders...")
    market.current_round = 1

    # Alice wants to sell 10 units at $12
    market.submit_order(Order("alice", OrderType.SELL, 10, 12.0))
    print(f"  {agents['alice'].agent_id}: SELL 10 @ $12.00")

    # Charlie wants to sell 15 units at $10 (lower price, more competitive)
    market.submit_order(Order("charlie", OrderType.SELL, 15, 10.0))
    print(f"  {agents['charlie'].agent_id}: SELL 15 @ $10.00")

    # Bob wants to buy 20 units at $11
    market.submit_order(Order("bob", OrderType.BUY, 20, 11.0))
    print(f"  {agents['bob'].agent_id}: BUY 20 @ $11.00")

    print("\nMatching orders...")
    trades = market.match_orders(agents)

    print(f"\nExecuted {len(trades)} trade(s):")
    for trade in trades:
        print(f"  {trade}")

    print("\n=== Agent States After Trading ===")
    for agent_id, agent in agents.items():
        print(f"\n{agent}")
        state = agent.get_state_summary()
        print(f"  State: {state}")

    print("\n=== Market Summary ===")
    summary = market.get_market_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
