"""Fase 1: auditoria de dados antes de qualquer análise.

Pergunta: os números do RavenStack são confiáveis o bastante para sustentar
um diagnóstico de churn? Cada checagem imprime o que encontrou; nada é corrigido aqui.

Uso:
    python solution/01_audit.py
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"


def load() -> dict[str, pd.DataFrame]:
    acc = pd.read_csv(DATA / "ravenstack_accounts.csv", parse_dates=["signup_date"])
    sub = pd.read_csv(DATA / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"])
    use = pd.read_csv(DATA / "ravenstack_feature_usage.csv", parse_dates=["usage_date"])
    tix = pd.read_csv(DATA / "ravenstack_support_tickets.csv", parse_dates=["submitted_at", "closed_at"])
    chn = pd.read_csv(DATA / "ravenstack_churn_events.csv", parse_dates=["churn_date"])
    return {"accounts": acc, "subscriptions": sub, "feature_usage": use, "support_tickets": tix, "churn_events": chn}


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    d = load()
    acc, sub, use, tix, chn = d.values()

    section("Chaves primárias e integridade referencial")
    for name, df, pk in [("accounts", acc, "account_id"), ("subscriptions", sub, "subscription_id"),
                         ("feature_usage", use, "usage_id"), ("support_tickets", tix, "ticket_id"),
                         ("churn_events", chn, "churn_event_id")]:
        print(f"{name:16s} linhas={len(df):6d} pk_duplicada={df[pk].duplicated().sum()}")
    print("subs sem conta:", (~sub.account_id.isin(acc.account_id)).sum())
    print("usage sem sub:", (~use.subscription_id.isin(sub.subscription_id)).sum())
    print("tickets sem conta:", (~tix.account_id.isin(acc.account_id)).sum())
    print("churn sem conta:", (~chn.account_id.isin(acc.account_id)).sum())
    print("linhas de usage duplicadas (ignorando usage_id):",
          use.drop(columns="usage_id").duplicated().sum())

    section("Nulos por coluna (só colunas com nulo)")
    for name, df in d.items():
        nulls = df.isna().sum()
        nulls = nulls[nulls > 0]
        if len(nulls):
            print(name, dict((k, f"{v} ({v / len(df):.0%})") for k, v in nulls.items()))

    section("Janela temporal de cada tabela")
    for name, col in [("accounts", "signup_date"), ("subscriptions", "start_date"), ("subscriptions", "end_date"),
                      ("feature_usage", "usage_date"), ("support_tickets", "submitted_at"),
                      ("churn_events", "churn_date")]:
        s = d[name][col]
        print(f"{name}.{col:14s} {s.min().date()} a {s.max().date()}")

    section("Churn: três fontes, uma verdade?")
    acc_flag = set(acc.loc[acc.churn_flag, "account_id"])
    evt_acc = set(chn.account_id)
    sub_flag = set(sub.loc[sub.churn_flag, "account_id"])
    print(f"contas com accounts.churn_flag=True: {len(acc_flag)}")
    print(f"contas com >=1 churn_event:          {len(evt_acc)}")
    print(f"contas com >=1 sub churn_flag=True:   {len(sub_flag)}")
    print(f"flag=True sem evento:  {len(acc_flag - evt_acc)}")
    print(f"evento sem flag=True:  {len(evt_acc - acc_flag)}")
    ev_per_acc = chn.groupby("account_id").size()
    print("eventos por conta:", ev_per_acc.value_counts().sort_index().to_dict())
    print("is_reactivation=True:", chn.is_reactivation.sum())
    multi = ev_per_acc[ev_per_acc > 1].index
    print("contas com >1 evento cujo 1º evento já é reativação:",
          chn[chn.account_id.isin(multi)].sort_values("churn_date").groupby("account_id").head(1)
          .is_reactivation.sum())

    section("Assinaturas")
    print("subs por conta: min/mediana/max =",
          sub.groupby("account_id").size().agg(["min", "median", "max"]).to_dict())
    print("ARR != 12*MRR:", (sub.arr_amount != sub.mrr_amount * 12).sum())
    print("end_date preenchida vs churn_flag:")
    print(pd.crosstab(sub.end_date.notna(), sub.churn_flag, rownames=["tem_end_date"], colnames=["churn_flag"]))
    print("end_date < start_date:", (sub.end_date < sub.start_date).sum())
    print("upgrade e downgrade juntos:", (sub.upgrade_flag & sub.downgrade_flag).sum())
    # Contas com assinaturas sobrepostas: 10 subs/conta pode significar 10 contratos simultâneos.
    s = sub.sort_values(["account_id", "start_date"]).copy()
    s["end_fill"] = s.end_date.fillna(pd.Timestamp("2099-01-01"))
    s["prev_end"] = s.groupby("account_id").end_fill.shift().where(lambda x: x.notna())
    print("subs que começam antes da anterior terminar (sobreposição):", (s.start_date < s.prev_end).sum())
    print("plano da conta == plano da sub mais recente:",
          f"{(acc.set_index('account_id').plan_tier.sort_index() == s.groupby('account_id').plan_tier.last().sort_index()).mean():.0%}")
    print("MRR por plano (mediana):", sub.groupby("plan_tier").mrr_amount.median().to_dict())
    print("MRR/seat por plano (mediana):",
          (sub.mrr_amount / sub.seats).groupby(sub.plan_tier).median().round(1).to_dict())

    section("Consistência temporal entre tabelas")
    first_sub = sub.groupby("account_id").start_date.min()
    a = acc.set_index("account_id")
    print("sub começa antes do signup da conta:", (first_sub < a.signup_date.reindex(first_sub.index)).sum())
    c = chn.merge(acc[["account_id", "signup_date"]], on="account_id")
    print("churn antes do signup:", (c.churn_date < c.signup_date).sum())
    u = use.merge(sub[["subscription_id", "start_date", "end_date"]], on="subscription_id")
    print("uso antes do início da sub:", (u.usage_date < u.start_date).sum())
    print("uso depois do fim da sub:", (u.usage_date > u.end_date).sum())
    last_evt = chn.groupby("account_id").churn_date.max()
    last_use = u.merge(sub[["subscription_id", "account_id"]], on="subscription_id").groupby("account_id").usage_date.max()
    both = pd.concat([last_evt, last_use], axis=1, keys=["churn", "uso"]).dropna()
    print(f"contas com uso DEPOIS do último churn: {(both.uso > both.churn).sum()} de {len(both)}")
    print("ticket fechado antes de aberto:", (tix.closed_at < tix.submitted_at).sum())
    calc_h = (tix.closed_at - tix.submitted_at).dt.total_seconds() / 3600
    print("resolution_time_hours diverge de closed-submitted (>1h):", ((calc_h - tix.resolution_time_hours).abs() > 1).sum())

    section("Distribuições suspeitas (dado sintético uniforme?)")
    print("churn reason_code:", chn.reason_code.value_counts().to_dict())
    print("feedback_text distintos:", chn.feedback_text.nunique(), chn.feedback_text.value_counts().head(8).to_dict())
    print("satisfaction_score:", tix.satisfaction_score.value_counts(dropna=False).sort_index().to_dict())
    print("priority:", tix.priority.value_counts().to_dict())
    print("features distintas:", use.feature_name.nunique(), "| beta:", use.is_beta_feature.mean().round(3))
    print("contas com uso registrado:",
          use.merge(sub[["subscription_id", "account_id"]]).account_id.nunique(), "de", len(acc))
    print("contas com ticket:", tix.account_id.nunique(), "de", len(acc))


if __name__ == "__main__":
    main()
