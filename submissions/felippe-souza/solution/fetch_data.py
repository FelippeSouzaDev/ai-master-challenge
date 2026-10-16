"""Baixa o dataset RavenStack do Kaggle (download público, sem login) para ../data/.

Uso:
    python solution/fetch_data.py

Dataset: SaaS Subscription & Churn Analytics, de River @ Rivalytics (licença MIT-like).
Os CSVs não vão para o git; este script os recria.
"""
import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://www.kaggle.com/api/v1/datasets/download/rivalytics/saas-subscription-and-churn-analytics-dataset"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXPECTED = {
    "ravenstack_accounts.csv": 500,
    "ravenstack_subscriptions.csv": 5000,
    "ravenstack_feature_usage.csv": 25000,
    "ravenstack_support_tickets.csv": 2000,
    "ravenstack_churn_events.csv": 600,
}


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with urllib.request.urlopen(URL) as resp:
        payload = resp.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for member in zf.namelist():
            name = Path(member).name
            if name in EXPECTED:
                (DATA_DIR / name).write_bytes(zf.read(member))

    # Confere a contagem de linhas: download truncado gera número errado em silêncio.
    for name, rows in EXPECTED.items():
        path = DATA_DIR / name
        got = sum(1 for _ in path.open(encoding="utf-8")) - 1
        status = "ok" if got == rows else f"ESPERADO {rows}"
        print(f"{name:35s} {got:6d} linhas  {status}")


if __name__ == "__main__":
    main()
