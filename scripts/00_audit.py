import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nqr.data.audit import run_audit
t0 = time.time()
rep = run_audit()
print(f"done in {time.time()-t0:.0f}s; halves audited: {rep['audited_halves']}")
