# Economic Simulator

An LLM-powered economic simulation where AI agents autonomously trade goods in a marketplace using Claude for intelligent decision-making.

## Overview

This project implements a simple economic marketplace where agents buy and sell commodities (wheat by default). Each agent uses Claude AI to make trading decisions based on their role, personality, current resources, and market conditions. The simulation demonstrates emergent economic behavior as agents interact through a price-discovery mechanism.

## Features

- **AI-Powered Decision Making**: Agents use Claude (Haiku) to analyze market conditions and make buy/sell/hold decisions
- **Distinct Agent Personalities**: Each agent has a unique personality that influences their trading strategy
- **Order Matching System**: Automatic matching of buy and sell orders with price discovery
- **Trade History Tracking**: Complete transaction history for market analysis
- **Market Roles**: Agents can be buyers, sellers, or market makers
- **Configurable Simulation**: Customize number of rounds, enable debug mode to see AI reasoning

## Requirements

- Python 3.10+
- Anthropic API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd econsim
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API key:
```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Get your API key from: https://console.anthropic.com/settings/keys

## Usage

### Basic Simulation

Run a 5-round simulation:
```bash
python llm_demo.py
```

### Custom Number of Rounds

Run a 10-round simulation:
```bash
python llm_demo.py 10
```

### Debug Mode

See the prompts sent to Claude and full AI responses:
```bash
python llm_demo.py --debug
```

Or combine with custom rounds:
```bash
python llm_demo.py 3 --debug
```

### Core Classes Demo

Run the basic simulator without LLM (manual orders):
```bash
python simulator.py
```

## How It Works

### Agent Decision Process

1. Each round, agents receive a market summary containing:
   - Current round number
   - Last traded price and average recent prices
   - Number of pending buy/sell orders
   - Their own state (money, inventory, recent trades)

2. Claude analyzes this information along with the agent's:
   - Role (buyer/seller/market maker)
   - Personality traits
   - Transaction history

3. Claude returns a decision in JSON format:
   - `buy`: Submit a buy order with quantity and price
   - `sell`: Submit a sell order with quantity and price
   - `hold`: Wait for better market conditions

### Order Matching

The market uses a simple order matching algorithm:
- Buy orders are sorted by price (highest first)
- Sell orders are sorted by price (lowest first)
- Orders are matched when buy price >= sell price
- Trade price is the average of bid and ask prices
- Partial fills are supported

## Key Concepts

- **Agent**: Economic agent with money, inventory, personality, and LLM decision-making
- **Market**: Marketplace that manages orders and executes trades
- **Order**: Buy or sell order with price and quantity
- **Trade**: Executed trade between two agents

### Project Structure

```
econsim/
├── simulator.py      # Core classes (Agent, Market, Order, Trade)
├── llm_demo.py       # LLM-powered simulation runner
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── README.md         # This file
```

## Example Output

```
=== LLM-Powered Economic Simulator ===

============================================================
ROUND 1
============================================================

Market Conditions:
  No trades yet

Agent Decisions:

  alice (seller):
    State: $100.00, 50 units
    Decision: SELL 10 @ $12.50

  bob (buyer):
    State: $500.00, 0 units
    Decision: BUY 15 @ $11.00

------------------------------------------------------------
Executing Trades...

Executed 1 trade(s):
  Round 1: bob bought 10 from alice @ $11.75
```

## Configuration

### Model Settings

In `simulator.py`, you can adjust:
- `MODEL`: Claude model to use (default: `claude-3-5-haiku-20241022`)
- `MAX_TOKENS`: Maximum response length (default: 200)
- `TEMPERATURE`: Randomness in decisions (default: 0.7)

### Agent Configuration

Create agents with custom:
- Starting money
- Initial inventory
- Role (buyer/seller/market_maker)
- Personality description

