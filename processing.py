from __future__ import annotations

import pandas as pd


OUTPUT_COLUMNS = ["Date", "Appliance", "STH/BOX", "Revisits"]


def summarize_routes(frame: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    excluded = pd.to_numeric(frame["LocationKey"], errors="coerce").eq(5894)
    routes = frame.loc[~excluded].copy()

    route_dates = pd.to_datetime(routes["RouteStart"], errors="coerce", format="mixed")
    valid_dates = route_dates.notna()
    invalid_date_count = int((~valid_dates).sum())
    routes = routes.loc[valid_dates].copy()

    if routes.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS), int(excluded.sum()), invalid_date_count

    requirements_column = next(
        column
        for column in routes.columns
        if str(column).strip().casefold() == "requirements"
    )
    requirements = routes[requirements_column].astype("string").str.strip()
    scopes = routes["SCOP"].astype("string").str.strip()

    routes["Date"] = route_dates.loc[valid_dates].dt.normalize()
    routes["_Appliance"] = requirements.eq("BXAPPLIANCE").fillna(False).astype(int)
    routes["_Package"] = requirements.isin(["STH", "BOX"]).astype(int)
    routes["_Revisits"] = scopes.isin(
        ["MO Return", "MO Other", "MO Replacement"]
    ).astype(int)

    summary = (
        routes.groupby("Date", as_index=False)
        .agg({"_Appliance": "sum", "_Package": "sum", "_Revisits": "sum"})
        .rename(
            columns={
                "_Appliance": "Appliance",
                "_Package": "STH/BOX",
                "_Revisits": "Revisits",
            }
        )
    )
    summary["Date"] = summary["Date"].dt.strftime("%m-%d-%Y")
    return summary[OUTPUT_COLUMNS], int(excluded.sum()), invalid_date_count