"""
LLM-powered Economic Simulator Demo
Demonstrates agents using Claude to make trading decisions
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

from simulator import Agent, Market, OrderType


def run_llm_simulation(num_rounds: int = 5, debug: bool = False):
    """
    Run a simulation where agents use Claude to make trading decisions.

    Args:
        num_rounds: Number of trading rounds to simulate
        debug: If True, show prompts sent to Claude and full responses
    """

    # load anthropic client
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found")
        print("Please create a .env file with: ANTHROPIC_API_KEY=your-key-here")
        print("See .env.example for reference")
        return
    client = Anthropic(api_key=api_key)

    print("=== LLM-Powered Economic Simulator ===\n")
    print("Each agent will use Claude to make trading decisions based on:")
    print("- Their role (buyer/seller)")
    print("- Current inventory and money")
    print("- Market conditions and price history")
    print("- Their unique personality")
    if debug:
        print("\n[DEBUG MODE ENABLED - Will show all prompts and Claude responses]")
    print()

    # create agents with distinct personalities
    agents = {
        "alice": Agent(
            agent_id="alice",
            role="seller",
            money=100.0,
            inventory=50,
            personality="Conservative seller who values steady profits over quick sales. Prefers to wait for good prices.",
        ),
        "bob": Agent(
            agent_id="bob",
            role="buyer",
            money=500.0,
            inventory=0,
            personality="Strategic buyer looking for good deals. Will hold if prices seem too high.",
        ),
        "charlie": Agent(
            agent_id="charlie",
            role="seller",
            money=150.0,
            inventory=40,
            personality="Aggressive seller who wants to move inventory quickly, even at lower prices.",
        ),
        "diana": Agent(
            agent_id="diana",
            role="buyer",
            money=400.0,
            inventory=0,
            personality="Eager buyer with strong demand. Willing to pay premium prices to secure inventory.",
        ),
    }

    # create market
    market = Market(commodity_name="wheat")

    # run simulation for N rounds
    for round_num in range(1, num_rounds + 1):
        print(f"\n{'=' * 60}")
        print(f"ROUND {round_num}")
        print(f"{'=' * 60}\n")

        market.current_round = round_num
        market_summary = market.get_market_summary()

        print("Market Conditions:")
        if market_summary["last_price"]:
            print(f"  Last price: ${market_summary['last_price']:.2f}")
            print(f"  Avg recent price: ${market_summary['avg_recent_price']:.2f}")
        else:
            print("  No trades yet")
        print()

        # each agent makes a decision
        print("Agent Decisions:")
        for agent_id, agent in agents.items():
            print(f"\n  {agent_id} ({agent.role}):")
            print(f"    State: ${agent.money:.2f}, {agent.inventory} units")

            order = agent.make_decision(market_summary, client, debug=debug)

            if order:
                market.submit_order(order)
                print(f"    Decision: {order}")
            else:
                print(f"    Decision: HOLD")

        # match orders and execute trades
        print("\n" + "-" * 60)
        print("Executing Trades...")
        trades = market.match_orders(agents)

        if trades:
            print(f"\nExecuted {len(trades)} trade(s):")
            for trade in trades:
                print(f"  {trade}")
        else:
            print("\nNo trades executed (no matching orders)")

        # clear unfilled orders
        market.clear_orders()

    # final summary
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60 + "\n")

    print("Final Agent States:")
    for agent_id, agent in agents.items():
        print(f"\n{agent}")
        total_value = agent.money + (
            agent.inventory * market_summary["avg_recent_price"]
            if market_summary["avg_recent_price"]
            else 0
        )
        print(f"  Estimated total value: ${total_value:.2f}")
        print(f"  Trade history: {len(agent.transaction_history)} trades")

    print("\n" + "=" * 60)
    print(f"Market Summary: {len(market.trade_history)} total trades")
    if market.trade_history:
        all_prices = [t.price for t in market.trade_history]
        print(f"Price range: ${min(all_prices):.2f} - ${max(all_prices):.2f}")
        print(f"Average price: ${sum(all_prices) / len(all_prices):.2f}")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    # show help
    if "--help" in sys.argv or "-h" in sys.argv:
        print("LLM Economic Simulator")
        print("\nUsage: python llm_demo.py [rounds] [--debug]")
        print("\nOptions:")
        print("  rounds      Number of rounds to simulate (default: 5)")
        print("  --debug, -d Show all prompts sent to Claude and full responses")
        print("  --help, -h  Show this help message")
        print("\nExamples:")
        print("  python llm_demo.py              # Run 5 rounds")
        print("  python llm_demo.py 10           # Run 10 rounds")
        print("  python llm_demo.py --debug      # Run 5 rounds with debug output")
        print("  python llm_demo.py 3 --debug    # Run 3 rounds with debug output")
        sys.exit(0)

    # parse command-line arguments
    debug = "--debug" in sys.argv or "-d" in sys.argv

    # get number of rounds from arguments (default: 5)
    num_rounds = 5
    for arg in sys.argv[1:]:
        if arg.isdigit():
            num_rounds = int(arg)

    # run it!
    run_llm_simulation(num_rounds=num_rounds, debug=debug)
