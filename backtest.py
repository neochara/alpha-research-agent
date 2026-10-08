from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
import pandas as pd
from scipy import stats

from config import TRAIN_END, TRADING_DAYS, VALID_END


@dataclass(frozen=True)
class ExperimentSpec:
    lookback_days: int
    skip_days: int = 21
    rebalance_days: int = 21
    long_fraction: float = 0.33
    cost_bps: float = 5.0
    vol_scale: bool = False
    vol_lookback: int = 63

    def validate(self) -> None:
        if self.lookback_days <= self.skip_days:
            raise ValueError("lookback_days must be > skip_days.")
        if self.skip_days < 0:
            raise ValueError("skip_days must be >= 0.")
        if self.rebalance_days < 1:
            raise ValueError("rebalance_days must be >= 1.")
        if not (0 < self.long_fraction < 0.5):
            raise ValueError("long_fraction must be between 0 and 0.5.")
        if self.cost_bps < 0:
            raise ValueError("cost_bps must be >= 0.")
        if self.vol_lookback < 2:
            raise ValueError("vol_lookback must be >= 2.")


def momentum_signal(prices: pd.DataFrame, lookback: int, skip: int) -> pd.DataFrame:
    """Past return ending ``skip`` trading days ago.

    signal[t] = P[t-skip] / P[t-lookback] - 1.
    Example: lookback=252 and skip=21 approximates 12-1 momentum.
    """
    return prices.shift(skip) / prices.shift(lookback) - 1.0


def _cross_sectional_weights(
    signal: pd.DataFrame,
    long_fraction: float,
    vol: pd.DataFrame | None = None,
) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=signal.index, columns=signal.columns)

    for dt, row in signal.iterrows():
        valid = row.dropna()
        n = len(valid)
        if n < 4:
            continue

        k = max(1, int(math.floor(n * long_fraction)))
        ranked = valid.sort_values()
        shorts = list(ranked.index[:k])
        longs = list(ranked.index[-k:])

        if vol is None:
            long_scale = pd.Series(1.0, index=longs)
            short_scale = pd.Series(1.0, index=shorts)
        else:
            current_vol = vol.loc[dt]
            long_scale = 1.0 / current_vol.reindex(longs).replace(0, np.nan)
            short_scale = 1.0 / current_vol.reindex(shorts).replace(0, np.nan)
            long_scale = long_scale.replace([np.inf, -np.inf], np.nan).dropna()
            short_scale = short_scale.replace([np.inf, -np.inf], np.nan).dropna()
            if long_scale.empty or short_scale.empty:
                continue

        # Dollar neutral, gross exposure = 1: +0.5 long and -0.5 short.
        long_weights = 0.5 * long_scale / long_scale.sum()
        short_weights = -0.5 * short_scale / short_scale.sum()
        weights.loc[dt, long_weights.index] = long_weights
        weights.loc[dt, short_weights.index] = short_weights

    return weights


def build_weights(prices: pd.DataFrame, spec: ExperimentSpec) -> pd.DataFrame:
    spec.validate()
    signal = momentum_signal(prices, spec.lookback_days, spec.skip_days)
    returns = prices.pct_change(fill_method=None)

    vol = None
    if spec.vol_scale:
        vol = returns.rolling(spec.vol_lookback).std()

    candidate_weights = _cross_sectional_weights(signal, spec.long_fraction, vol)

    eligible = signal.notna().sum(axis=1) >= 4
    eligible_dates = signal.index[eligible]
    rebalance_dates = eligible_dates[::spec.rebalance_days]

    weights = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    weights.loc[rebalance_dates] = candidate_weights.loc[rebalance_dates]
    return weights.ffill().fillna(0.0)


def strategy_returns(
    prices: pd.DataFrame, spec: ExperimentSpec
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Return gross/net strategy returns, turnover, and target weights.

    Weights formed at close t are shifted one day so they can earn only t->t+1 returns.
    This is the core look-ahead-bias safeguard in the backtest.
    """
    asset_returns = prices.pct_change(fill_method=None).fillna(0.0)
    weights = build_weights(prices, spec)

    held_weights = weights.shift(1).fillna(0.0)
    gross = (held_weights * asset_returns).sum(axis=1)

    turnover_at_trade = weights.diff().abs().sum(axis=1).fillna(0.0)
    transaction_cost = (
        turnover_at_trade.shift(1).fillna(0.0) * (spec.cost_bps / 10_000.0)
    )
    net = gross - transaction_cost

    returns = pd.DataFrame(
        {
            "gross_return": gross,
            "transaction_cost": transaction_cost,
            "net_return": net,
        }
    )
    return returns, turnover_at_trade.rename("turnover"), weights


def _max_drawdown(r: pd.Series) -> float:
    wealth = (1.0 + r.fillna(0.0)).cumprod()
    peak = wealth.cummax()
    return float((wealth / peak - 1.0).min())


def _newey_west_t_stat(r: pd.Series, lags: int | None = None) -> tuple[float | None, int]:
    """Approximate HAC/Newey-West t-statistic for the sample mean.

    Uses Bartlett weights and a common automatic lag rule when lags is not supplied.
    """
    x = np.asarray(r.dropna(), dtype=float)
    n = len(x)
    if n < 3:
        return None, 0

    if lags is None:
        lags = int(math.floor(4 * (n / 100) ** (2 / 9)))
    lags = max(0, min(lags, n - 1))

    u = x - x.mean()
    gamma0 = float(np.dot(u, u) / n)
    long_run_var = gamma0
    for lag in range(1, lags + 1):
        gamma = float(np.dot(u[lag:], u[:-lag]) / n)
        weight = 1.0 - lag / (lags + 1.0)
        long_run_var += 2.0 * weight * gamma

    if long_run_var <= 0:
        return None, lags
    se_mean = math.sqrt(long_run_var / n)
    return float(x.mean() / se_mean), lags


def metrics(r: pd.Series, turnover: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {"n_days": int(len(r))}

    mean = float(r.mean())
    sd = float(r.std(ddof=1))
    ann_mean_return = mean * TRADING_DAYS
    ann_vol = sd * math.sqrt(TRADING_DAYS)
    sharpe = ann_mean_return / ann_vol if ann_vol > 0 else np.nan

    iid_t = mean / (sd / math.sqrt(len(r))) if sd > 0 else np.nan
    iid_p = (
        2 * stats.t.sf(abs(iid_t), df=len(r) - 1)
        if np.isfinite(iid_t)
        else np.nan
    )
    hac_t, hac_lags = _newey_west_t_stat(r)
    hac_p = 2 * stats.norm.sf(abs(hac_t)) if hac_t is not None else None

    out = {
        "n_days": int(len(r)),
        "annualized_mean_return": ann_mean_return,
        "annualized_vol": ann_vol,
        "sharpe": float(sharpe) if np.isfinite(sharpe) else None,
        "t_stat_iid": float(iid_t) if np.isfinite(iid_t) else None,
        "p_value_iid": float(iid_p) if np.isfinite(iid_p) else None,
        "t_stat_hac": hac_t,
        "p_value_hac_approx": float(hac_p) if hac_p is not None else None,
        "hac_lags": hac_lags,
        "max_drawdown": _max_drawdown(r),
        "hit_rate": float((r > 0).mean()),
    }

    if turnover is not None:
        aligned = turnover.reindex(r.index).fillna(0.0)
        out["avg_daily_turnover"] = float(aligned.mean())
        out["annual_turnover"] = float(aligned.mean() * TRADING_DAYS)

    return out


def _period_metrics(
    returns: pd.DataFrame,
    turnover: pd.Series,
    mask: pd.Series | np.ndarray,
) -> dict:
    gross = returns.loc[mask, "gross_return"]
    net = returns.loc[mask, "net_return"]
    period_turnover = turnover.loc[mask]
    gross_metrics = metrics(gross, period_turnover)
    net_metrics = metrics(net, period_turnover)

    annual_cost_drag = float((gross.mean() - net.mean()) * TRADING_DAYS)
    return {
        "net": net_metrics,
        "gross": gross_metrics,
        "annualized_cost_drag": annual_cost_drag,
    }


def evaluate(prices: pd.DataFrame, spec: ExperimentSpec, include_test: bool = False) -> dict:
    returns, turnover, _ = strategy_returns(prices, spec)

    train_end = pd.Timestamp(TRAIN_END)
    valid_end = pd.Timestamp(VALID_END)
    train_mask = returns.index <= train_end
    valid_mask = (returns.index > train_end) & (returns.index <= valid_end)
    test_mask = returns.index > valid_end

    result = {
        "spec": asdict(spec),
        "train": _period_metrics(returns, turnover, train_mask),
        "validation": _period_metrics(returns, turnover, valid_mask),
    }
    if include_test:
        result["test"] = _period_metrics(returns, turnover, test_mask)
    return result
