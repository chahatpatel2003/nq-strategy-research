"""Phase-7 book-sequence audit and visual diagnostics.

Regenerates the REFERENCE configuration's 2022 book (no candidate was selected,
so this is a diagnostic artifact, not a production trade log), then:

  A. BOOK-SEQUENCE AUDIT -- raw MBP-1 events around random signals, event by
     event, specifically to catch sequencing bugs.
  B. Six seeded, non-cherry-picked galleries of 20.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p4.model4 import Preprocessor
from nqr.p2.cache2 import load_month_ticks
from nqr.p7 import backtest7 as BT
from nqr.p7 import cache7, dataset7, model7
from nqr.p7 import features7 as F7

SD = ROOT / "strategies" / "orderbook_state"
RES = SD / "results" / "reference_2022"; RES.mkdir(parents=True, exist_ok=True)
DIA = SD / "diagnostics"; DIA.mkdir(parents=True, exist_ok=True)
CH = DIA / "charts"; CH.mkdir(parents=True, exist_ok=True)
FR, SEED, N = 1.0, 20260822, 20
NS = F7.NS

sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
ref = sel.sort("net_ER", descending=True).row(0, named=True)
TAG, FAM, Q = ref["r_tag"], ref["family"], ref["selectivity"]
meta = json.loads((SD / "models" / "development_meta.json").read_text())
atr_e, spr_e = np.array(meta["atr_edges"]), np.array(meta["spread_edges"])
print(f"reference (NOT a candidate): {ref['config']}")

df = dataset7.load_split("dev")
yr = np.array([d.year for d in df["trading_date"].to_list()])
u = dataset7.usable_mask(df, TAG)
X = dataset7.feature_matrix(df)
tr = (yr == 2021) & u
pre = Preprocessor.fit(X[tr], fit_on="train2021")
est = model7.fit_model(FAM, pre.transform(X[tr]), df[f"{TAG}_y"].to_numpy().astype(int)[tr])
thr = model7.thresholds_from_train(est.predict_proba(pre.transform(X[tr]))[:, 1])[Q]
se = yr == 2022
d_se = df.filter(pl.Series(se)); u_se = u[se]
p = np.full(d_se.height, np.nan)
p[u_se] = est.predict_proba(pre.transform(X[se][u_se]))[:, 1]
conf = np.where(np.isfinite(p), model7.confidence(p), -np.inf)
dirn = model7.direction_of(np.nan_to_num(p, nan=0.5))
book = BT.run_strategy(d_se, TAG, conf, dirn, thr, u_se)
acc = BT.accepted(book)
feats = d_se.select(["decision_ts_ns"] + F7.FEATURE_NAMES)
acc_f = acc.join(feats, on="decision_ts_ns", how="left")
book.write_parquet(RES / "signals.parquet")
acc_f.write_parquet(RES / "trades.parquet"); acc_f.write_csv(RES / "trades.csv")
ctrl = BT.matched_controls(book, d_se, TAG, u_se, atr_e, spr_e, mode="cross_day")
ctrl.write_parquet(RES / "control_cross_day.parquet")
print(f"reference 2022 book: {acc.height} trades, {ctrl.height} controls")

# ------------------------------------------------------- A. sequence audit
print("\n=== A. BOOK-SEQUENCE AUDIT (raw MBP-1 events around random signals) ===")
import duckdb
from nqr.data.audit import connect
con = connect(memory_limit="4GB", threads=4)
# DuckDB parses a NAIVE TIMESTAMPTZ literal in the SESSION timezone and returns
# TIMESTAMPTZ converted to it.  Pin UTC so both the window and the output are
# unambiguous.  (cache7.BOOK_SQL is already safe: its literals carry +0000.)
con.execute("SET TimeZone='UTC'")
rng = np.random.default_rng(SEED)
pick = acc[sorted(rng.choice(acc.height, size=min(6, acc.height), replace=False).tolist())]
lines = []
for row in pick.iter_rows(named=True):
    d = row["trading_date"]; sig = int(row["decision_ts_ns"])
    src = cache7.mbp1_file_for(d.year, 1 if d.month <= 6 else 2)
    q = con.execute(f"""
      SELECT ts_event, sequence, file_row_number AS frn, action, side, price, size,
             bid_px_00 pb, bid_sz_00 qb, ask_px_00 pa, ask_sz_00 qa
      FROM read_parquet('{src}', file_row_number=true)
      WHERE ts_event >= TIMESTAMPTZ '{np.datetime64(sig-2*NS,"ns")}+0000'
        AND ts_event <  TIMESTAMPTZ '{np.datetime64(sig+1*NS,"ns")}+0000'
        AND symbol='{row['symbol']}'
      ORDER BY ts_event, sequence, frn LIMIT 14""").df()
    if q.empty:
        continue
    # bid_sz_00/ask_sz_00 are uint32: subtracting them in pandas UNDERFLOWS
    # (1 - 2 -> 4294967295).  The production SQL casts to BIGINT; this audit must
    # too, or it reports nonsense while looking for nonsense.
    q["qb"] = q.qb.astype("int64"); q["qa"] = q.qa.astype("int64")
    q["imb"] = (q.qb - q.qa) / (q.qb + q.qa)
    q["micro"] = (q.pa * q.qb + q.pb * q.qa) / (q.qb + q.qa)
    lp, lqb, lpa, lqa = q.pb.shift(), q.qb.shift(), q.pa.shift(), q.qa.shift()
    q["ofi"] = [0 if i == q.index[0] else
                F7.ofi_event(r.pb, r.qb, r.pa, r.qa, lp[i], lqb[i], lpa[i], lqa[i])
                for i, r in q.iterrows()]
    q["t_utc"] = q.ts_event.dt.strftime("%H:%M:%S.%f").str[:-3]
    # resolution-independent: DuckDB may hand back datetime64[us], and pandas 3
    # removed Series.view, so neither .view nor .astype("int64") is safe here.
    q["ts_event"] = q.ts_event.dt.tz_convert("UTC")
    _ep = (q.ts_event.dt.tz_localize(None).values
           .astype("datetime64[ns]").astype("int64"))
    q["dt_ms"] = ((_ep - sig) / 1e6).round(1)
    lines.append(f"\n--- {d} {row['side']} signal at {row['sec_since_open']}s since open, "
                 f"conf={row['score']:.4f}, entry={row['entry_price']:.2f}, "
                 f"{row['outcome']} {row['netR_1p0']:+.2f}R ---")
    lines.append(q[["t_utc", "dt_ms", "sequence", "frn", "action", "side", "price", "size",
                    "pb", "qb", "pa", "qa", "imb", "micro", "ofi"]]
                 .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
(DIA / "book_sequence_audit.txt").write_text("\n".join(lines))
print("\n".join(lines[:8]))
print(f"\nwrote {DIA}/book_sequence_audit.txt")

# ------------------------------------------------------------- B. charts
import os
if os.environ.get("P7_SKIP_CHARTS"):
    print("\n[charts already generated - skipping]"); sys.exit(0)
print("\n=== B. VISUAL DIAGNOSTICS ===")
months: dict = {}
bkm: dict = {}


def day_data(day):
    ym = f"{day.year:04d}-{day.month:02d}"
    if ym not in months:
        months[ym] = load_month_ticks(ym)
        bkm[ym] = cache7.load_month(ym)
    return (months[ym].filter(pl.col("trading_date") == day),
            bkm[ym].filter(pl.col("trading_date") == day))


def panel(axes, row):
    day = row["trading_date"]
    tk, bk = day_data(day)
    if tk.height == 0 or bk.height == 0:
        return False
    sig = int(row["decision_ts_ns"]); ex = int(row["exit_ns"])
    ts = tk["ts_ns"].to_numpy(); px = tk["px_ticks"].to_numpy() * F7.TICK
    lo = np.searchsorted(ts, sig - 120 * NS); hi = np.searchsorted(ts, ex + 60 * NS)
    if hi - lo < 5:
        return False
    ax = axes[0]
    ax.plot((ts[lo:hi] - sig) / 60 / NS, px[lo:hi], lw=0.6, color="#333")
    s0, s1 = sig // NS - 120, ex // NS + 60
    b = bk.filter((pl.col("sec") >= s0) & (pl.col("sec") <= s1))
    if b.height:
        x = (b["sec"].to_numpy() * NS - sig) / 60 / NS
        ax.plot(x, b["bid_px"].to_numpy(), lw=0.5, color="#2ca02c", alpha=.7)
        ax.plot(x, b["ask_px"].to_numpy(), lw=0.5, color="#d62728", alpha=.7)
    ax.axvline(0, color="#1f77b4", lw=1.0, ls="--")
    ax.axhline(row["entry_price"], color="#1f77b4", lw=0.8)
    ax.axhline(row["stop"], color="#d62728", lw=0.7, ls=":")
    ax.axhline(row["target"], color="#2ca02c", lw=0.7, ls=":")
    ax.plot((ex - sig) / 60 / NS, row["exit_price"], "o", ms=4,
            color="#2ca02c" if row["net_1p0"] > 0 else "#d62728")
    ax.set_title(f"{day} {row['side']} conf={row['score']:.3f} | {row['outcome']} "
                 f"{row['netR_1p0']:+.2f}R | imb={row.get('imb',float('nan')):+.2f} "
                 f"ofi5={row.get('ofi_5',float('nan')):+.1f} "
                 f"spr={row.get('spread_ticks',float('nan')):.0f}t", fontsize=5.0, loc="left")
    ax.tick_params(labelsize=4.5)
    if b.height:
        a2 = axes[1]
        a2.plot(x, b["imb_last"].to_numpy(), lw=0.6, color="#9467bd")
        a2.axhline(0, color="#999", lw=0.4)
        a2.axvline(0, color="#1f77b4", lw=0.8, ls="--")
        a2.set_ylim(-1.05, 1.05); a2.tick_params(labelsize=4.5)
        a2.set_ylabel("imb", fontsize=4.5)
        a3 = axes[2]
        a3.bar(x, b["ofi"].to_numpy(), width=0.02, color="#8c564b")
        a3.axhline(0, color="#999", lw=0.4)
        a3.axvline(0, color="#1f77b4", lw=0.8, ls="--")
        a3.tick_params(labelsize=4.5); a3.set_ylabel("OFI/s", fontsize=4.5)
        a3.set_xlabel("minutes from signal", fontsize=4.5)
    return True


hi_conf = float(np.quantile(acc_f["score"].to_numpy(), 0.75))
GAL = [("winners", acc_f.filter(pl.col("net_1p0") > 0)),
       ("losers", acc_f.filter(pl.col("net_1p0") < 0)),
       ("timeouts", acc_f.filter(pl.col("outcome") == "TIMEOUT")),
       ("highest_confidence", acc_f.sort("score", descending=True).head(60)),
       ("false_high_confidence", acc_f.filter((pl.col("score") >= hi_conf)
                                              & (pl.col("net_1p0") < 0))),
       ("matched_controls", ctrl)]
rng = np.random.default_rng(SEED)
for name, fr in GAL:
    if fr.height == 0:
        print(f"  {name}: empty"); continue
    take = rng.choice(fr.height, size=min(N, fr.height), replace=False)
    sample = fr[sorted(take.tolist())].sort("trading_date")
    fig, axes = plt.subplots(15, 4, figsize=(20, 24),
                             gridspec_kw={"height_ratios": [3, 1, 1] * 5})
    k = 0
    for row in sample.iter_rows(named=True):
        if k >= N:
            break
        c, r_ = k % 4, (k // 4) * 3
        if panel([axes[r_, c], axes[r_ + 1, c], axes[r_ + 2, c]], row):
            k += 1
    for j in range(k, N):
        c, r_ = j % 4, (j // 4) * 3
        for z in range(3):
            axes[r_ + z, c].axis("off")
    fig.suptitle(f"Phase 7 — {name.replace('_',' ')} — random sample of {k} from the 2022 "
                 f"reference book (seed {SEED}, not cherry-picked). "
                 f"rows: price+BBO / imbalance / OFI per second", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.975])
    fig.savefig(CH / f"{name}.png", dpi=100)
    plt.close(fig)
    print(f"  {name}: {k} panels from {fr.height}")
print(f"wrote {CH}")
