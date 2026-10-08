import numpy as np
import pandas as pd

from backtest import ExperimentSpec, build_weights, momentum_signal, strategy_returns


def synthetic_prices(n_days=900, n_assets=9):
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2016-01-01", periods=n_days)
    shocks = rng.normal(0.0003, 0.01, size=(n_days, n_assets))
    prices = 100 * np.exp(np.cumsum(shocks, axis=0))
    cols = [f"A{i}" for i in range(n_assets)]
    return pd.DataFrame(prices, index=dates, columns=cols)


def test_momentum_signal_uses_only_past_prices():
    prices = synthetic_prices()
    signal = momentum_signal(prices, lookback=63, skip=5)
    t = 100
    expected = prices.iloc[t - 5] / prices.iloc[t - 63] - 1.0
    pd.testing.assert_series_equal(signal.iloc[t], expected, check_names=False)


def test_weights_are_dollar_neutral_when_invested():
    prices = synthetic_prices()
    spec = ExperimentSpec(lookback_days=63, skip_days=5, rebalance_days=21)
    weights = build_weights(prices, spec)
    invested = weights.abs().sum(axis=1) > 0
    assert np.allclose(weights.loc[invested].sum(axis=1), 0.0, atol=1e-12)
    assert np.allclose(weights.loc[invested].abs().sum(axis=1), 1.0, atol=1e-12)


def test_transaction_costs_cannot_improve_net_returns():
    prices = synthetic_prices()
    spec = ExperimentSpec(
        lookback_days=63,
        skip_days=5,
        rebalance_days=5,
        cost_bps=10.0,
    )
    returns, _, _ = strategy_returns(prices, spec)
    assert (returns["transaction_cost"] >= 0).all()
    assert np.allclose(
        returns["net_return"],
        returns["gross_return"] - returns["transaction_cost"],
    )


def test_no_same_day_signal_return_capture():
    prices = synthetic_prices()
    spec = ExperimentSpec(lookback_days=63, skip_days=5, rebalance_days=21)
    returns, _, weights = strategy_returns(prices, spec)
    first_trade = (weights.diff().abs().sum(axis=1) > 0)
    trade_dates = weights.index[first_trade]
    if len(trade_dates):
        first = trade_dates[0]
        # The initial target position is not allowed to earn the return ending on the
        # same close at which it was formed.
        assert returns.loc[first, "gross_return"] == 0.0
