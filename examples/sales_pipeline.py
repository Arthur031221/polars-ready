import pandas as pd

sales = pd.read_csv("sales.csv")
sales = sales.dropna(subset=["amount"])
sales = sales.assign(net=sales.amount * 0.9)
summary = sales.groupby("region").agg({"net": "sum"})
summary = summary.sort_values("net")
summary.to_csv("summary.csv")

# These paths need a closer migration review.
recent = sales.loc[sales["year"] == 2026]
monthly = sales.set_index("date").resample("M").sum()
for _, row in recent.iterrows():
    print(row["region"])
