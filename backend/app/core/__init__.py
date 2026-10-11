"""Deterministic Smart-Money-Concepts strategy engine.

Every module in this package is pure and side-effect free: it takes candle
series and configuration and returns structured results. No network, no broker,
no database. This is what makes the strategy testable and identical between the
live, paper and backtest execution paths.
"""
