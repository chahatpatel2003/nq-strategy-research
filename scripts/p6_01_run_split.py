"""Run Phase-6 causal contexts + the six entry mechanics over one period.

    python scripts/p6_01_run_split.py --split train2021
    ... select2022 | itest2023 | contam2024 | contam2025h2
    python scripts/p6_01_run_split.py --split val2026q1 --confirm <phrase>

The direction model is the FROZEN Phase-5 `r4p0:A_logit:top2`, loaded read-only.
Phase 6 changes only WHEN and AT WHAT PRICE the position is opened.
"""
import argparse, json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import cache4
from nqr.p4 import features4 as F4
from nqr.p5 import dataset5, model5
from nqr.p6 import backtest6 as BT
from nqr.p6 import context6 as C6
from nqr.p6 import holdout6 as H6

MODELS = ROOT / "strategies" / "larger_r" / "models"
OUT = ROOT / "strategies" / "context_entry" / "results"
DATASET_OF = {"train2021": "dev", "select2022": "dev", "itest2023": "dev",
              "contam2024": "contam2024", "contam2025h2": "contam2025h2",
              "val2026q1": "val2026q1"}
SEED = 20260821

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(DATASET_OF), required=True)
ap.add_argument("--confirm", default="")
ap.add_argument("--model", default=str(MODELS / "production_model.pkl"))
a = ap.parse_args()
if a.split == "val2026q1":
    H6.unlock_phase6_validation(a.confirm)
    print("*** FRESH VALIDATION - 2026-Q1 - ONE SHOT ***")
else:
    print(f"*** {a.split}: PHASE-6 DEVELOPMENT (post-hoc hypothesis -> all pre-2026 "
          f"periods are development) ***")

start, end = H6.SPLITS[a.split]
H6.assert_range_allowed(start, end, f"--split {a.split}")

with open(a.model, "rb") as f:
    P = pickle.load(f)
pre, est, tau, base = P["pre"], P["est"], P["tau"], P["baseline"]
TAG = P["r_tag"]
assert TAG == "r4p0", "Phase 6 must use the Phase-5 selected r4p0 architecture"
print(f"context model: {P['config_name']}  R={dataset5.R_MULTS[TAG]}xATR1m  tau={tau:.6f}")

t0 = time.time()
df = dataset5.load_split(DATASET_OF[a.split])
df = df.filter((pl.col("trading_date") >= start) & (pl.col("trading_date") <= end))
assert df.height
for d in (df["trading_date"].min(), df["trading_date"].max()):
    H6.assert_date_allowed(d, "split row")
ok = dataset5.usable_mask(df, TAG)
X = dataset5.feature_matrix(df)
sec = df["sec_since_open"].to_numpy()
p = np.full(df.height, np.nan)
p[ok] = est.predict_proba(pre.transform(X[ok]))[:, 1]
bl, bs = model5.baseline_vectors(base, sec)
score, direction = model5.edge_and_direction(p, bl, bs)
score = np.where(np.isfinite(p), score, -np.inf)
print(f"rows={df.height:,} usable={int(ok.sum()):,} days={df['trading_date'].n_unique()} "
      f"qualifying={int((score >= tau).sum()):,}  [{time.time()-t0:.0f}s]", flush=True)

df = df.with_columns(pl.Series("_score", score), pl.Series("_dir", direction),
                     pl.Series("_ok", ok))

# ---- pass 1: activation direction pool (dataset only, no ticks) -----------
dir_pool = []
for d, g in df.group_by("trading_date", maintain_order=True):
    s = g["_score"].to_numpy(); dd = g["_dir"].to_numpy()
    o = g["_ok"].to_numpy(); sc = g["sec_since_open"].to_numpy()
    for b in range(C6.N_BUCKETS):
        m = (sc >= b * C6.BUCKET_S) & (sc < (b + 1) * C6.BUCKET_S)
        idx = np.flatnonzero(m & o & (s >= tau))
        if idx.size:
            dir_pool.append(int(dd[idx[0]]))
dir_pool = np.array(dir_pool, dtype=np.int64)
print(f"candidate contexts (dataset pass): {dir_pool.size:,}  "
      f"long={int((dir_pool > 0).sum()):,} short={int((dir_pool < 0).sum()):,}")

# ---- pass 2: ticks + entry mechanics --------------------------------------
rng = np.random.default_rng(SEED)
books = {m: [] for m in list(C6.ENTRY_METHODS) + [f"CONTROL_{c}" for c in C6.CONTROLS]}
ctx_rows, n_days = [], 0
months = sorted({f"{d.year:04d}-{d.month:02d}" for d in df["trading_date"].unique()})
for ym in months:
    mo = cache4.load_month(ym)
    if mo.height == 0:
        continue
    sub = df.filter(pl.col("trading_date").dt.strftime("%Y-%m") == ym)
    for d, g in sub.group_by("trading_date", maintain_order=True):
        day = d[0] if isinstance(d, tuple) else d
        tk = mo.filter(pl.col("trading_date") == day)
        if tk.height < 500:
            continue
        ts = tk["ts_ns"].to_numpy(); px = tk["px_ticks"].to_numpy().astype(np.int64)
        ctxs = C6.build_contexts(
            day, g["symbol"][0], g["decision_ts_ns"].to_numpy(),
            g["sec_since_open"].to_numpy(), g["_score"].to_numpy(),
            g["_dir"].to_numpy(), g[f"{TAG}_R"].to_numpy().astype(float),
            g["_ok"].to_numpy(), tau, ts, px)
        n_days += 1
        if not ctxs:
            continue
        used = {c.bucket for c in ctxs}
        free = [b for b in range(C6.N_BUCKETS) if b not in used]
        r = BT.run_day(day, ctxs, ts, px, rng, free, dir_pool)
        ctx_rows.extend(r["contexts"])
        for k, v in r["books"].items():
            books[k].extend(v)
    print(f"  {ym}: days={n_days} contexts={len(ctx_rows):,}  [{time.time()-t0:.0f}s]",
          flush=True)

d_out = OUT / f"run_{a.split}"; d_out.mkdir(parents=True, exist_ok=True)
BT.frame(ctx_rows).write_parquet(d_out / "contexts.parquet")
meta = {"split": a.split, "start": str(start), "end": str(end),
        "role": H6.role_of(start), "context_model": P["config_name"], "tau": tau,
        "r_tag": TAG, "seed": SEED, "n_days": n_days, "n_contexts": len(ctx_rows),
        "n_rows": df.height, "runtime_s": round(time.time() - t0, 1), "books": {}}
for k, v in books.items():
    fr = BT.frame(v)
    if fr.height:
        fr.write_parquet(d_out / f"book_{k}.parquet")
    acc = BT.accepted(fr)
    meta["books"][k] = {"rows": fr.height, "accepted": acc.height,
                        "fill_rate": acc.height / max(1, len(ctx_rows))}
(d_out / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str))
print(f"\ncontexts={len(ctx_rows):,} over {n_days} days "
      f"({len(ctx_rows)/max(1,n_days):.2f}/day of a possible 4)")
for k in list(C6.ENTRY_METHODS) + [f"CONTROL_{c}" for c in C6.CONTROLS]:
    b = meta["books"][k]
    print(f"  {k:20s} accepted={b['accepted']:6d}  fill/context={b['fill_rate']:.2f}")
print(f"done in {time.time()-t0:.0f}s")
