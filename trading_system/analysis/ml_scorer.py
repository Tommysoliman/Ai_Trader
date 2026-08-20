"""
ML scoring layer — Random Forest classifier per ticker.

Features: RSI, MACD histogram, volume ratio, ATR ratio,
          dist from 200/50 SMA, R:R ratio, sector RS.
Labels:   Buy (>+2%), Sell (<-2%), or Not worth taking the risk
          over the next 10 trading days.

Optimisations:
  - 24-hour local OHLCV cache (avoids redundant yfinance downloads)
  - Background retraining thread (stale model used while new one trains)
  - tqdm progress for batch training
  - Purged five-fold walk-forward validation (10-session gap)
  - Reliability gate based on balanced accuracy and macro F1
"""

import json
import pickle
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import TimeSeriesSplit

try:
    from tqdm import tqdm
except ImportError:
    # tqdm not installed — use a no-op wrapper
    def tqdm(iterable, **kwargs):
        return iterable

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
CACHE_DIR = MODEL_DIR / "cache"
CACHE_TTL_SECONDS = 86_400  # 24 hours
MODEL_SCHEMA_VERSION = 2
FORECAST_HORIZON = 10
RETURN_THRESHOLD = 0.02

BUY_CLASS = 1
RISK_CLASS = 0
SELL_CLASS = -1

SECTOR_ETFS = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}

FEATURE_COLS = [
    "rsi", "macd_hist", "volume_ratio", "atr_ratio",
    "dist_200sma", "dist_50sma", "rr_ratio", "sector_rs",
]


# ── Data cache ────────────────────────────────────────────────────────────────

class DataCache:
    """Pickle-based OHLCV cache with 24-hour TTL."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ticker: str, period: str) -> Path:
        safe = ticker.replace(".", "_").replace("/", "_")
        return self._dir / f"{safe}_{period}.pkl"

    def get(self, ticker: str, period: str) -> pd.DataFrame | None:
        p = self._path(ticker, period)
        if not p.exists():
            return None
        age = time.time() - p.stat().st_mtime
        if age > CACHE_TTL_SECONDS:
            return None
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def set(self, ticker: str, period: str, df: pd.DataFrame):
        try:
            with open(self._path(ticker, period), "wb") as f:
                pickle.dump(df, f)
        except Exception:
            pass


_data_cache = DataCache()


def fetch_ohlcv_cached(ticker: str, period: str = "1y") -> pd.DataFrame | None:
    """Download OHLCV data with 24-hour local cache."""
    df = _data_cache.get(ticker, period)
    if df is not None:
        return df
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df is not None and len(df) > 0:
            _data_cache.set(ticker, period, df)
        return df
    except Exception as e:
        print(f"[Cache] Download failed for {ticker}: {e}")
        return None


# ── Feature engineering ───────────────────────────────────────────────────────

def _compute_features(df: pd.DataFrame, sector_etf: str = None) -> pd.DataFrame:
    """
    Compute FEATURE_COLS from an OHLCV DataFrame.
    Returns a DataFrame with the same index as df.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)

    close = df["Close"].squeeze().astype(float)
    high  = df["High"].squeeze().astype(float)
    low   = df["Low"].squeeze().astype(float)
    vol   = df["Volume"].squeeze().astype(float)

    # RSI (14-period)
    delta    = close.diff()
    avg_gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rsi      = 100 - 100 / (1 + avg_gain / avg_loss.replace(0, np.nan))

    # MACD histogram (12/26/9)
    macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_hist = macd_line - macd_line.ewm(span=9, adjust=False).mean()

    # Volume ratio vs 20-day average
    volume_ratio = vol / vol.rolling(20).mean().replace(0, np.nan)

    # ATR ratio: current ATR relative to its own 20-day average
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    atr       = tr.ewm(span=14, adjust=False).mean()
    atr_ratio = atr / atr.rolling(20).mean().replace(0, np.nan)

    # % distance from 200-day and 50-day SMA
    sma200      = close.rolling(200).mean()
    sma50       = close.rolling(50).mean()
    dist_200sma = (close - sma200) / sma200.replace(0, np.nan)
    dist_50sma  = (close - sma50)  / sma50.replace(0, np.nan)

    # R:R ratio — upside to 52-week high vs 2×ATR downside
    high_252 = close.rolling(252, min_periods=20).max()
    rr_ratio = ((high_252 - close).clip(lower=0) / (2 * atr.replace(0, np.nan))).clip(-10, 10)

    # Sector RS — 20-day stock return minus 20-day sector ETF return
    sector_rs = pd.Series(0.0, index=df.index)
    if sector_etf:
        try:
            etf_df = fetch_ohlcv_cached(sector_etf, period="2y")
            if etf_df is not None and len(etf_df) >= 20:
                if isinstance(etf_df.columns, pd.MultiIndex):
                    etf_df = etf_df.droplevel(1, axis=1)
                etf_close = etf_df["Close"].squeeze().astype(float)
                stock_ret = close.pct_change(20)
                etf_ret   = etf_close.pct_change(20).reindex(df.index, method="ffill")
                sector_rs = (stock_ret - etf_ret).fillna(0.0)
        except Exception:
            pass

    return pd.DataFrame({
        "rsi":          rsi,
        "macd_hist":    macd_hist,
        "volume_ratio": volume_ratio,
        "atr_ratio":    atr_ratio,
        "dist_200sma":  dist_200sma,
        "dist_50sma":   dist_50sma,
        "rr_ratio":     rr_ratio,
        "sector_rs":    sector_rs,
    }, index=df.index)


# ── MLScorer ──────────────────────────────────────────────────────────────────

class MLScorer:
    """
    Per-ticker Random Forest with:
    - Auto 30-day retraining in background thread
    - 24h OHLCV cache via DataCache
    - Accuracy gate: unreliable if test accuracy < 55%
    """

    def __init__(self, model_dir: Path = None):
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._models: dict         = {}
        self._meta: dict           = self._load_meta()
        self._retrain_lock         = threading.Lock()
        self._retraining: set      = set()   # tickers currently training

    # ── persistence ──────────────────────────────────────────────────────────

    def _meta_path(self):
        return self.model_dir / "ml_meta.json"

    def _model_path(self, ticker: str) -> Path:
        return self.model_dir / f"rf_{ticker.replace('.', '_')}.pkl"

    def _load_meta(self) -> dict:
        p = self._meta_path()
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_meta(self):
        with open(self._meta_path(), "w") as f:
            json.dump(self._meta, f, indent=2, default=str)

    def _load_model(self, ticker: str) -> bool:
        if self._meta.get(ticker, {}).get("schema_version") != MODEL_SCHEMA_VERSION:
            return False
        p = self._model_path(ticker)
        if p.exists():
            try:
                with open(p, "rb") as f:
                    self._models[ticker] = pickle.load(f)
                return True
            except Exception:
                pass
        return False

    def _save_model(self, ticker: str, model):
        with open(self._model_path(ticker), "wb") as f:
            pickle.dump(model, f)
        self._models[ticker] = model

    # ── training ─────────────────────────────────────────────────────────────

    def _needs_retrain(self, ticker: str) -> bool:
        last = self._meta.get(ticker, {}).get("last_trained")
        if not last:
            return True
        return (datetime.now() - datetime.fromisoformat(last)).days >= 30

    def train(self, ticker: str, sector_etf: str = None) -> float | None:
        """
        Train a three-class model with purged walk-forward validation.
        Uses 24h data cache to avoid redundant downloads.
        Returns balanced accuracy or None on failure.
        """
        print(f"[ML] Training {ticker}...")
        df = fetch_ohlcv_cached(ticker, period="2y")
        if df is None or len(df) < 60:
            print(f"[ML] Insufficient data for {ticker}")
            return None

        feat = _compute_features(df, sector_etf)

        close = df["Close"].squeeze().astype(float)
        fwd_return = close.shift(-FORECAST_HORIZON) / close - 1
        label = pd.Series(
            np.select(
                [fwd_return > RETURN_THRESHOLD, fwd_return < -RETURN_THRESHOLD],
                [BUY_CLASS, SELL_CLASS],
                default=RISK_CLASS,
            ),
            index=close.index,
            name="label",
        )

        combined = feat.join(label).replace([np.inf, -np.inf], np.nan).dropna()
        combined = combined.iloc[:-FORECAST_HORIZON]
        if len(combined) < 120:
            print(f"[ML] Not enough clean rows for {ticker} ({len(combined)})")
            return None

        X     = combined[FEATURE_COLS]
        y     = combined["label"]
        model_params = dict(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        splitter = TimeSeriesSplit(n_splits=5, gap=FORECAST_HORIZON)
        observed, predicted = [], []
        for train_idx, test_idx in splitter.split(X):
            fold_model = RandomForestClassifier(**model_params)
            fold_model.fit(X.iloc[train_idx], y.iloc[train_idx])
            observed.extend(y.iloc[test_idx].tolist())
            predicted.extend(fold_model.predict(X.iloc[test_idx]).tolist())

        accuracy = float(accuracy_score(observed, predicted))
        balanced_accuracy = float(balanced_accuracy_score(observed, predicted))
        macro_f1 = float(f1_score(observed, predicted, average="macro", zero_division=0))
        precision, recall, _, support = precision_recall_fscore_support(
            observed, predicted, labels=[SELL_CLASS, RISK_CLASS, BUY_CLASS], zero_division=0
        )
        majority_baseline = float(pd.Series(observed).value_counts(normalize=True).max())
        reliable = balanced_accuracy >= 0.40 and macro_f1 >= 0.35

        model = RandomForestClassifier(**model_params)
        model.fit(X, y)

        self._save_model(ticker, model)
        self._meta[ticker] = {
            "last_trained": datetime.now().isoformat(),
            "accuracy":     round(accuracy, 4),
            "balanced_accuracy": round(balanced_accuracy, 4),
            "macro_f1": round(macro_f1, 4),
            "majority_baseline": round(majority_baseline, 4),
            "precision": dict(zip(["Sell", "Risk", "Buy"], np.round(precision, 4).tolist())),
            "recall": dict(zip(["Sell", "Risk", "Buy"], np.round(recall, 4).tolist())),
            "support": dict(zip(["Sell", "Risk", "Buy"], support.astype(int).tolist())),
            "reliable":     reliable,
            "n_samples":    len(X),
            "schema_version": MODEL_SCHEMA_VERSION,
        }
        self._save_meta()
        tag = "reliable" if accuracy >= 0.55 else "UNRELIABLE — below 55%"
        print(
            f"[ML] {ticker} balanced_accuracy={balanced_accuracy:.2%}, "
            f"macro_f1={macro_f1:.2%}, raw_accuracy={accuracy:.2%} "
            f"({'reliable' if reliable else 'UNRELIABLE'})"
        )
        return balanced_accuracy

    def train_batch(self, tickers: list, sector_etf_map: dict = None):
        """Train models for multiple tickers with tqdm progress bar."""
        sector_etf_map = sector_etf_map or {}
        for ticker in tqdm(tickers, desc="ML training", unit="ticker"):
            etf = sector_etf_map.get(ticker)
            self.train(ticker, etf)

    def _retrain_async(self, ticker: str, sector_etf: str = None):
        """Spawn background thread to retrain without blocking the request."""
        with self._retrain_lock:
            if ticker in self._retraining:
                return
            self._retraining.add(ticker)

        def _worker():
            try:
                self.train(ticker, sector_etf)
            finally:
                with self._retrain_lock:
                    self._retraining.discard(ticker)

        threading.Thread(target=_worker, daemon=True).start()

    # ── prediction ───────────────────────────────────────────────────────────

    def predict(self, ticker: str, df: pd.DataFrame, sector_etf: str = None) -> dict | None:
        """
        Compute features from df's last row and return ML probability + signal.

        If a model exists but is stale (>30 days): retrains in background
        and returns a result from the current (stale) model immediately.
        If no model exists at all: trains synchronously (first-time setup).

        Returns None if a model cannot be built.
        """
        model_exists = ticker in self._models or self._load_model(ticker)

        if not model_exists:
            # First time — block and train so we can return a result
            self._retrain_async(ticker, sector_etf)
            return None
        elif self._needs_retrain(ticker):
            # Stale — retrain in background, use existing model now
            self._retrain_async(ticker, sector_etf)

        meta = self._meta.get(ticker, {})

        if not meta.get("reliable", True):
            return {
                "ml_probability": None,
                "ml_probabilities": {},
                "ml_score":       0.0,
                "ml_signal":      "Not worth taking the risk",
                "model_accuracy": meta.get("accuracy"),
                "balanced_accuracy": meta.get("balanced_accuracy"),
                "macro_f1":       meta.get("macro_f1"),
                "model_reliable": False,
                "last_trained":   meta.get("last_trained"),
            }

        feat     = _compute_features(df, sector_etf)
        last_row = feat.iloc[-1][FEATURE_COLS].fillna(0.0).values.reshape(1, -1)
        model = self._models[ticker]
        raw_probabilities = model.predict_proba(last_row)[0]
        by_class = {
            int(class_id): float(probability)
            for class_id, probability in zip(model.classes_, raw_probabilities)
        }
        buy_probability = by_class.get(BUY_CLASS, 0.0)
        sell_probability = by_class.get(SELL_CLASS, 0.0)
        risk_probability = by_class.get(RISK_CLASS, 0.0)
        ml_score = buy_probability - sell_probability

        if buy_probability >= 0.45 and buy_probability > sell_probability + 0.05:
            ml_signal = "Buy"
            decision_probability = buy_probability
        elif sell_probability >= 0.45 and sell_probability > buy_probability + 0.05:
            ml_signal = "Sell"
            decision_probability = sell_probability
        else:
            ml_signal = "Not worth taking the risk"
            decision_probability = risk_probability

        return {
            "ml_probability": round(decision_probability, 3),
            "ml_probabilities": {
                "Buy": round(buy_probability, 3),
                "Sell": round(sell_probability, 3),
                "Not worth taking the risk": round(risk_probability, 3),
            },
            "ml_score":       round(ml_score, 3),
            "ml_signal":      ml_signal,
            "model_accuracy": meta.get("accuracy"),
            "balanced_accuracy": meta.get("balanced_accuracy"),
            "macro_f1":       meta.get("macro_f1"),
            "majority_baseline": meta.get("majority_baseline"),
            "model_reliable": True,
            "last_trained":   meta.get("last_trained"),
        }


# Module-level singleton — one instance per gunicorn worker process
_scorer: MLScorer | None = None


def get_ml_scorer() -> MLScorer:
    global _scorer
    if _scorer is None:
        _scorer = MLScorer()
    return _scorer
