# Quantitative Finance & Algorithmic Trading Portfolio
> Robust Automated Execution Systems and Statistical Arbitrage Engines

This repository serves as a production-grade suite for algorithmic execution, focusing on low-latency connectivity, automated risk mitigation, and statistical edge.

---

#  Featured Production Engine: MT5 Automated Execution Framework

A professional-tier Python-to-MT5 execution engine designed for mean-reversion strategies, specifically optimized for the EUR/JPY pair.

###  Core Logic: Statistical Mean Reversion
The system monitors price relative to a 100-period lookback, calculating a **Rolling Z-Score**. Trades are triggered at statistical extremes ($Z > 2.2$), betting on a snap-back to the mean.



###  Safety & Risk Protocols
Built with a "Safety-First" architecture to handle real-world brokerage environment challenges:

* **State Recovery (Anti-Amnesia):** On startup, the engine scans the terminal using unique `MAGIC_NUMBER` identifiers. It can resume management of open positions even after a hardware crash or system reboot.
* **Volatility-Adjusted Position Sizing:** Dynamically calculates lot sizes based on **ATR (Average True Range)** to ensure a strict **1% Equity Risk** per trade, regardless of market volatility.
* **Neutral Zone Exits:** Automatically closes positions once price enters the "Fair Value" zone ($|Z| < 0.2$), maximizing capital turnover efficiency.
* **Weekend Gap Protection:** Hard-coded exit protocols for Friday 20:00 UTC to prevent exposure to weekend liquidity gaps and slippage.
* **Connectivity Heartbeat:** Integrated self-healing logic that detects MT5 terminal disconnection and attempts a graceful re-initialization.

###  Audit & Transparency
Every decision is recorded in `live_trade_audit.csv`, creating a high-fidelity data trail for:
* Trade Reconciliation
* Post-Trade Performance Attribution
* Slippage Analysis

---

##  Roadmap & Upcoming Features

### 1. AUD/CAD Statistical Arbitrage (Project 02)
* **Strategy:** Multi-leg spread trading based on Engle-Granger Cointegration.
* **Metrics:** Targeting a high-confidence entry trigger at $p < 0.001$.

### 2. Market Microstructure Analysis
* **Focus:** Order Book Imbalance (OBI) and High-Frequency spread dynamics.
# Quantitative Finance & Algorithmic Trading Portfolio
