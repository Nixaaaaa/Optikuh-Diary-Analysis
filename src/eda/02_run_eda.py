"""
Fast exploratory data analysis (EDA) for the OptiKuh dairy cow health dataset.


"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.size": 20,
    "axes.titlesize": 24,
    "axes.labelsize": 22,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "legend.fontsize": 18,
    "figure.titlesize": 26,
})

EXCEL_ORIGIN = "1899-12-30"
DATE_COLUMNS = ["gebdat", "datum", "kaldat", "trodat", "abgdat"]
DISEASE_COLUMNS = ["eu", "kl", "fr", "st", "at", "vo", "pa", "so"]
DISEASE_LABELS = {
    "eu": "Udder (eu)",
    "kl": "Claw/hoof (kl)",
    "fr": "Reproduction (fr)",
    "st": "Metabolic (st)",
    "at": "Respiratory (at)",
    "vo": "Digestive (vo)",
    "pa": "Parasitic (pa)",
    "so": "Other (so)",
}
HEALTH_LABELS = {
    "Gesund": "Healthy",
    "Produktionserkrankung": "Production disease",
    "SonstigeErkrankung": "Other disease",
    "Produktionserkrankung/SonstigeErkrankung": "Production + other disease",
}
HEALTH_ORDER = ["Healthy", "Production disease", "Other disease", "Production + other disease"]
BIOMARKERS = ["bhb", "glukose", "nefa", "insulin", "igf1", "adiponektin", "ca", "nsba"]
NUMERIC_SUMMARY_COLS = [
    "alter", "ltg", "apltg", "tratag", "trltg", "fts", "ftsnel", "eb_nel", "h2o",
    "gew", "bcs", "rfd", "mkg", "fpro", "epro", "feq", "lakt",
    "bhb", "glukose", "nefa", "insulin", "igf1", "ca", "nsba",
]
CORR_COLS = ["fts", "h2o", "gew", "bcs", "rfd", "mkg", "fpro", "epro", "feq", "bhb", "glukose", "nefa", "insulin", "igf1", "ca"]

def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    root = root_dir()
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=root / "data/interim/optikuh.csv")
    parser.add_argument("--meta", type=Path, default=root / "data/raw/optikuh_meta_variables.xlsx")
    parser.add_argument("--out", type=Path, default=root / "outputs/eda")
    parser.add_argument("--presentation", type=Path, default=root / "presentation")
    return parser.parse_args()


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8")


def save_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()

def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV cache not found: {csv_path}. Run src/01_convert_xlsx_to_csv.py first.")
    df = pd.read_csv(csv_path, low_memory=False)
    for col in DATE_COLUMNS:
        df[f"{col}_date"] = pd.to_datetime(pd.to_numeric(df[col], errors="coerce"), unit="D", origin=EXCEL_ORIGIN, errors="coerce")
    for col in NUMERIC_SUMMARY_COLS + ["zeile", "farm", "rasse", "lnr"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["health_status"] = df["gesundheit"].map(HEALTH_LABELS).fillna(df["gesundheit"])
    df["health_status"] = pd.Categorical(df["health_status"], categories=HEALTH_ORDER, ordered=True)
    df["episode_id"] = df["lom"].astype(str) + "_LN" + df["lnr"].astype(str) + "_CALV" + df["kaldat"].astype(str)
    return df


def load_meta(meta_path: Path) -> pd.DataFrame:
    meta = pd.read_excel(meta_path)
    meta.columns = ["variable", "meaning_de", "meaning_en"]
    if "feq" not in set(meta["variable"]):
        meta = pd.concat([
            meta,
            pd.DataFrame([{"variable": "feq", "meaning_de": "Fett-Eiweiss-Quotient", "meaning_en": "fat-to-protein ratio"}]),
        ], ignore_index=True)
    return meta


def make_tables(df: pd.DataFrame, meta: pd.DataFrame, tables_dir: Path) -> dict:
    total_rows = len(df)
    episodes = df[["episode_id", "lom", "farm", "rasse", "lnr", "health_status"]].drop_duplicates("episode_id")
    any_disease = df[DISEASE_COLUMNS].notna().any(axis=1)

    overview = pd.DataFrame([
        ("rows_daily_records", total_rows),
        ("columns_original", 49),
        ("columns_after_derived_dates", df.shape[1]),
        ("animals_unique_lom", df["lom"].nunique()),
        ("farms_unique", df["farm"].nunique()),
        ("breed_codes_unique", df["rasse"].nunique()),
        ("lactation_episodes_approx", episodes["episode_id"].nunique()),
        ("observation_start", df["datum_date"].min().date().isoformat()),
        ("observation_end", df["datum_date"].max().date().isoformat()),
        ("daily_diagnosis_rows_any_disease", int(any_disease.sum())),
        ("daily_records_with_blood_values_bhb", int(df["bhb"].notna().sum())),
        ("daily_records_with_milk_yield", int(df["mkg"].notna().sum())),
    ], columns=["metric", "value"])
    save_csv(overview, tables_dir / "dataset_overview.csv")

    missingness = pd.DataFrame({
        "variable": df.columns,
        "missing_count": df.isna().sum().astype(int).values,
        "missing_percent": (df.isna().mean() * 100).round(2).values,
        "non_missing_count": df.notna().sum().astype(int).values,
    }).sort_values("missing_percent", ascending=False)
    save_csv(missingness, tables_dir / "missingness.csv")

    stats = pd.DataFrame({
        "variable": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "non_missing": [int(df[c].notna().sum()) for c in df.columns],
        "missing_percent": [round(100 * df[c].isna().mean(), 2) for c in df.columns],
        "unique_values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    variable_dictionary = stats.merge(meta.drop_duplicates("variable"), on="variable", how="left")
    save_csv(variable_dictionary, tables_dir / "variable_dictionary.csv")

    numeric_cols = [c for c in NUMERIC_SUMMARY_COLS if c in df.columns]
    numeric_summary = df[numeric_cols].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).T.reset_index(names="variable").round(3)
    numeric_summary = numeric_summary.rename(columns={"50%": "median"})
    save_csv(numeric_summary, tables_dir / "numeric_summary.csv")

    health_rows = df["health_status"].value_counts(dropna=False).reindex(HEALTH_ORDER).rename_axis("health_status").reset_index(name="count")
    health_rows["percent"] = (100 * health_rows["count"] / total_rows).round(2)
    save_csv(health_rows, tables_dir / "health_status_daily_records.csv")
    health_episodes = episodes["health_status"].value_counts(dropna=False).reindex(HEALTH_ORDER).rename_axis("health_status").reset_index(name="count")
    health_episodes["percent"] = (100 * health_episodes["count"] / len(episodes)).round(2)
    save_csv(health_episodes, tables_dir / "health_status_lactation_episodes.csv")

    farm_summary = df.groupby("farm").agg(
        rows=("zeile", "count"),
        animals=("lom", "nunique"),
        episodes=("episode_id", "nunique"),
        breed_codes=("rasse", "nunique"),
        milk_records=("mkg", lambda s: int(s.notna().sum())),
        bhb_records=("bhb", lambda s: int(s.notna().sum())),
    ).reset_index()
    farm_summary["rows_per_animal"] = (farm_summary["rows"] / farm_summary["animals"]).round(1)
    save_csv(farm_summary, tables_dir / "farm_summary.csv")

    breed_summary = df.groupby("rasse").agg(rows=("zeile", "count"), animals=("lom", "nunique"), episodes=("episode_id", "nunique"), farms=("farm", "nunique")).reset_index()
    breed_summary["row_percent"] = (100 * breed_summary["rows"] / total_rows).round(2)
    save_csv(breed_summary, tables_dir / "breed_summary.csv")

    disease_rows = []
    diagnosis_rows = []
    for col in DISEASE_COLUMNS:
        mask = df[col].notna()
        disease_rows.append({
            "disease_column": col,
            "category": DISEASE_LABELS[col],
            "daily_event_rows": int(mask.sum()),
            "unique_animals": int(df.loc[mask, "lom"].nunique()),
            "unique_episodes": int(df.loc[mask, "episode_id"].nunique()),
            "row_percent": round(100 * mask.mean(), 3),
        })
        vc = df.loc[mask, col].value_counts()
        for diagnosis, count in vc.items():
            dmask = df[col].astype(str).eq(str(diagnosis))
            diagnosis_rows.append({
                "disease_column": col,
                "category": DISEASE_LABELS[col],
                "diagnosis": diagnosis,
                "daily_event_rows": int(count),
                "unique_animals": int(df.loc[dmask, "lom"].nunique()),
                "unique_episodes": int(df.loc[dmask, "episode_id"].nunique()),
            })
    disease_category = pd.DataFrame(disease_rows).sort_values("daily_event_rows", ascending=False)
    disease_diagnosis = pd.DataFrame(diagnosis_rows).sort_values("daily_event_rows", ascending=False)
    save_csv(disease_category, tables_dir / "disease_category_counts.csv")
    save_csv(disease_diagnosis, tables_dir / "disease_diagnosis_counts.csv")
    co_occ = df[DISEASE_COLUMNS].notna().T.dot(df[DISEASE_COLUMNS].notna()).astype(int)
    co_occ.index = [DISEASE_LABELS[c] for c in DISEASE_COLUMNS]
    co_occ.columns = [DISEASE_LABELS[c] for c in DISEASE_COLUMNS]
    save_csv(co_occ.reset_index().rename(columns={"index": "category"}), tables_dir / "disease_category_co_occurrence.csv")

    biomarker_summary = []
    for var in BIOMARKERS:
        tmp = df.groupby("health_status", observed=False)[var].agg(["count", "mean", "median", "std", "min", "max"]).reset_index()
        tmp.insert(0, "variable", var)
        biomarker_summary.append(tmp)
    biomarker_summary = pd.concat(biomarker_summary, ignore_index=True).round(3)
    save_csv(biomarker_summary, tables_dir / "biomarker_summary_by_health.csv")

    data_quality = pd.DataFrame([
        ("duplicate_zeile", int(df["zeile"].duplicated().sum()), "should be 0"),
        ("negative_day_in_milk_ltg", int((df["ltg"] < 0).sum()), "ltg < 0"),
        ("milk_yield_zero_or_negative", int((df["mkg"] <= 0).sum()), "mkg <= 0"),
        ("body_weight_below_300kg", int((df["gew"] < 300).sum()), "gew < 300 kg"),
        ("body_weight_above_1100kg", int((df["gew"] > 1100).sum()), "gew > 1100 kg"),
        ("bcs_outside_1_to_5", int(((df["bcs"] < 1) | (df["bcs"] > 5)).sum()), "BCS outside 1-5"),
        ("date_missing", int(df["datum_date"].isna().sum()), "missing observation date"),
        ("health_status_missing", int(df["health_status"].isna().sum()), "missing health status"),
    ], columns=["check", "count", "rule"])
    save_csv(data_quality, tables_dir / "data_quality_checks.csv")

    outlier_rows = []
    for var in numeric_cols:
        s = df[var].dropna()
        if len(s) == 0:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = int(((s < lower) | (s > upper)).sum())
        outlier_rows.append({"variable": var, "q1": q1, "q3": q3, "iqr": iqr, "lower_fence": lower, "upper_fence": upper, "outlier_count_iqr": outliers, "outlier_percent_non_missing": round(100 * outliers / len(s), 2)})
    save_csv(pd.DataFrame(outlier_rows).sort_values("outlier_percent_non_missing", ascending=False).round(3), tables_dir / "iqr_outlier_screen.csv")

    monthly = pd.DataFrame({
        "rows": df.groupby(df["datum_date"].dt.to_period("M")).size(),
        "animals": df.groupby(df["datum_date"].dt.to_period("M"))["lom"].nunique(),
        "farms": df.groupby(df["datum_date"].dt.to_period("M"))["farm"].nunique(),
        "milk_records": df.groupby(df["datum_date"].dt.to_period("M"))["mkg"].apply(lambda s: int(s.notna().sum())),
        "bhb_records": df.groupby(df["datum_date"].dt.to_period("M"))["bhb"].apply(lambda s: int(s.notna().sum())),
        "any_disease_records": any_disease.groupby(df["datum_date"].dt.to_period("M")).sum().astype(int),
    }).reset_index().rename(columns={"datum_date": "month"})
    monthly["month"] = monthly["datum_date"].astype(str) if "datum_date" in monthly.columns else monthly.iloc[:, 0].astype(str)
    monthly = monthly.drop(columns=[c for c in ["datum_date"] if c in monthly.columns])
    save_csv(monthly, tables_dir / "monthly_coverage.csv")
    save_csv(df.head(100), tables_dir / "sample_first_100_rows.csv")

    summary = {row["metric"]: row["value"] for _, row in overview.iterrows()}
    (tables_dir / "eda_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "overview": overview,
        "missingness": missingness,
        "health_rows": health_rows,
        "health_episodes": health_episodes,
        "farm_summary": farm_summary,
        "breed_summary": breed_summary,
        "disease_category": disease_category,
        "disease_diagnosis": disease_diagnosis,
        "biomarker_summary": biomarker_summary,
        "monthly": monthly,
    }


def bar(series: pd.Series, title: str, ylabel: str, path: Path, rot: int = 0) -> None:
    plt.figure(figsize=(8, 4.5))

    x_values = [str(x) for x in series.index.tolist()]
    y_values = [float(y) for y in series.to_numpy()]

    plt.bar(x_values, y_values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rot, ha="right" if rot else "center")
    save_plot(path)

def barh(series: pd.Series, title: str, xlabel: str, path: Path) -> None:
    plt.figure(figsize=(8.5, 5))

    ordered = series.sort_values()
    x_values = [float(x) for x in ordered.to_numpy()]
    y_values = [str(y) for y in ordered.index.tolist()]

    plt.barh(y_values, x_values)
    plt.title(title)
    plt.xlabel(xlabel)
    save_plot(path)

def hist(series: pd.Series, title: str, xlabel: str, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.hist(series.dropna(), bins=50)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Daily records")
    save_plot(path)

DEFAULT_HEALTH_ORDER = [
    "Healthy",
    "Production disease",
    "Other disease",
    "Production disease + other disease",
]

def boxplot_sample(
    df: pd.DataFrame,
    value_col: str,
    path: Path,
    title: str,
    ylabel: str,
    max_points: int = 50000,
) -> None:
    if value_col not in df.columns or "health_status" not in df.columns:
        return

    tmp = df[["health_status", value_col]].copy()
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce")
    tmp["health_status"] = tmp["health_status"].astype(str)
    tmp = tmp.dropna(subset=["health_status", value_col])

    if tmp.empty:
        return

    if len(tmp) > max_points:
        tmp = tmp.sample(max_points, random_state=42)

    present_statuses = tmp["health_status"].dropna().unique().tolist()

    labels = [label for label in DEFAULT_HEALTH_ORDER if label in present_statuses]
    labels += [label for label in present_statuses if label not in labels]

    data = [
        tmp.loc[tmp["health_status"].eq(label), value_col].to_numpy(dtype=float)
        for label in labels
    ]

    plt.figure(figsize=(10, 5.8))
    plt.boxplot(data, tick_labels=labels, showfliers=False)
    plt.xticks(rotation=25, ha="right")
    plt.title(title)
    plt.ylabel(ylabel)
    save_plot(path)

def as_str_list(values) -> list[str]:
    return [str(v) for v in list(values)]


def as_float_list(values) -> list[float]:
    return [float(v) for v in list(values)]


def make_episode_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates an approximate lactation-episode-level table.
    This avoids counting the same cow-lactation many times because of daily records.
    """
    id_cols = ["lom"]

    for candidate in ["ln", "laktation", "lactation", "lactation_number"]:
        if candidate in df.columns:
            id_cols.append(candidate)
            break

    keep_cols = [c for c in id_cols + ["farm", "rasse", "health_status"] if c in df.columns]
    episode_df = df[keep_cols].drop_duplicates()

    return episode_df


def stacked_percent_plot(
    data: pd.DataFrame,
    group_col: str,
    title: str,
    path: Path,
    min_count: int = 1,
) -> None:
    """
    Stacked percentage bar plot of health status within a grouping variable.
    Useful for farm, breed and lactation number comparisons.
    """
    if group_col not in data.columns or "health_status" not in data.columns:
        return

    tmp = data[[group_col, "health_status"]].dropna().copy()
    tmp[group_col] = tmp[group_col].astype(str)
    tmp["health_status"] = tmp["health_status"].astype(str)

    counts = pd.crosstab(tmp[group_col], tmp["health_status"])

    group_sizes = counts.sum(axis=1)
    counts = counts.loc[group_sizes[group_sizes >= min_count].index]

    if counts.empty:
        return

    ordered_cols = [c for c in HEALTH_ORDER if c in counts.columns]
    ordered_cols += [c for c in counts.columns if c not in ordered_cols]
    counts = counts[ordered_cols]

    pct = counts.div(counts.sum(axis=1), axis=0) * 100
    pct = pct.loc[counts.sum(axis=1).sort_values(ascending=False).index]

    plt.figure(figsize=(11, 6))
    x = np.arange(len(pct.index))
    bottom = np.zeros(len(pct.index))

    for status in pct.columns:
        values = pct[status].to_numpy(dtype=float)
        plt.bar(x, values, bottom=bottom, label=str(status))
        bottom += values

    plt.xticks(x, as_str_list(pct.index), rotation=45, ha="right")
    plt.ylabel("Share of lactation episodes (%)")
    plt.title(title)
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    save_plot(path)


def rate_by_group_plot(
    data: pd.DataFrame,
    group_col: str,
    title: str,
    path: Path,
    min_count: int = 5,
) -> None:
    """
    Plots the percentage of episodes with any production disease by group.
    """
    if group_col not in data.columns or "health_status" not in data.columns:
        return

    tmp = data[[group_col, "health_status"]].dropna().copy()
    tmp[group_col] = tmp[group_col].astype(str)
    tmp["has_production_disease"] = tmp["health_status"].astype(str).str.contains(
        "Production disease", case=False, na=False
    )

    summary = (
        tmp.groupby(group_col)
        .agg(
            episodes=("has_production_disease", "size"),
            production_disease_rate=("has_production_disease", "mean"),
        )
        .reset_index()
    )

    summary = summary[summary["episodes"] >= min_count]
    if summary.empty:
        return

    summary["production_disease_percent"] = summary["production_disease_rate"] * 100
    summary = summary.sort_values("production_disease_percent", ascending=True)

    plt.figure(figsize=(9.5, 5.5))
    plt.barh(
        summary[group_col].astype(str).tolist(),
        summary["production_disease_percent"].astype(float).tolist(),
    )
    plt.xlabel("Episodes with production disease (%)")
    plt.ylabel(group_col)
    plt.title(title)
    save_plot(path)


def line_trend_by_health_status(
    df: pd.DataFrame,
    value_col: str,
    ylabel: str,
    title: str,
    path: Path,
) -> None:
    """
    Median trajectory over days in milk by health status.
    Uses DIM bins to avoid very noisy daily lines.
    """
    if "ltg" not in df.columns or "health_status" not in df.columns or value_col not in df.columns:
        return

    tmp = df[["ltg", "health_status", value_col]].copy()
    tmp["ltg"] = pd.to_numeric(tmp["ltg"], errors="coerce")
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce")
    tmp = tmp.dropna(subset=["ltg", "health_status", value_col])

    if tmp.empty:
        return

    bins = [-80, -50, -30, -14, 0, 14, 28, 60, 100, 150, 200, 305, 500]
    labels = [
        "-80 to -50", "-50 to -30", "-30 to -14", "-14 to 0",
        "0 to 14", "14 to 28", "28 to 60", "60 to 100",
        "100 to 150", "150 to 200", "200 to 305", "305+"
    ]

    tmp["dim_bin"] = pd.cut(tmp["ltg"], bins=bins, labels=labels, include_lowest=True)

    trend = (
        tmp.groupby(["dim_bin", "health_status"], observed=True)[value_col]
        .median()
        .unstack()
    )

    if trend.empty:
        return

    ordered_cols = [c for c in HEALTH_ORDER if c in trend.columns]
    ordered_cols += [c for c in trend.columns if c not in ordered_cols]
    trend = trend[ordered_cols]

    plt.figure(figsize=(11, 5.8))
    x = np.arange(len(trend.index))

    for status in trend.columns:
        y = trend[status].to_numpy(dtype=float)
        if np.isfinite(y).sum() >= 2:
            plt.plot(x, y, marker="o", linewidth=2.2, label=str(status))

    plt.xticks(x, as_str_list(trend.index), rotation=45, ha="right")
    plt.xlabel("Day in milk / transition-period bin")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    save_plot(path)


def biomarker_availability_by_health(df: pd.DataFrame, figures_dir: Path) -> None:
    """
    Heatmap-style plot showing biomarker availability by health status.
    """
    available_biomarkers = [c for c in BIOMARKERS if c in df.columns]
    if not available_biomarkers or "health_status" not in df.columns:
        return

    tmp = df[["health_status"] + available_biomarkers].copy()
    for col in available_biomarkers:
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce")

    availability = (
        tmp.groupby("health_status")[available_biomarkers]
        .apply(lambda x: x.notna().mean() * 100)
    )

    ordered_rows = [r for r in HEALTH_ORDER if r in availability.index]
    ordered_rows += [r for r in availability.index if r not in ordered_rows]
    availability = availability.loc[ordered_rows]

    plt.figure(figsize=(10.5, 5.5))
    im = plt.imshow(availability.to_numpy(dtype=float), aspect="auto", vmin=0, vmax=100)
    plt.colorbar(im, label="Non-missing records (%)")
    plt.xticks(
        range(len(availability.columns)),
        as_str_list(availability.columns),
        rotation=45,
        ha="right",
    )
    plt.yticks(range(len(availability.index)), as_str_list(availability.index))
    plt.title("Biomarker availability by health status")
    save_plot(figures_dir / "fig27_biomarker_availability_by_health_status.png")


def biomarker_median_by_health(df: pd.DataFrame, figures_dir: Path) -> None:
    """
    Heatmap-style standardized median biomarker comparison by health status.
    This is descriptive only and helps identify visible group-level patterns.
    """
    available_biomarkers = [c for c in BIOMARKERS if c in df.columns and df[c].notna().sum() > 50]
    if not available_biomarkers or "health_status" not in df.columns:
        return

    tmp = df[["health_status"] + available_biomarkers].copy()
    for col in available_biomarkers:
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce")

    med = tmp.groupby("health_status")[available_biomarkers].median()

    ordered_rows = [r for r in HEALTH_ORDER if r in med.index]
    ordered_rows += [r for r in med.index if r not in ordered_rows]
    med = med.loc[ordered_rows]

    # Column-wise standardization so variables with different units can be compared visually.
    standardized = med.copy()
    for col in standardized.columns:
        col_values = standardized[col]
        spread = col_values.max() - col_values.min()
        if pd.notna(spread) and spread > 0:
            standardized[col] = (col_values - col_values.mean()) / col_values.std(ddof=0)
        else:
            standardized[col] = 0

    plt.figure(figsize=(10.5, 5.5))
    im = plt.imshow(standardized.to_numpy(dtype=float), aspect="auto")
    plt.colorbar(im, label="Standardized median")
    plt.xticks(
        range(len(standardized.columns)),
        as_str_list(standardized.columns),
        rotation=45,
        ha="right",
    )
    plt.yticks(range(len(standardized.index)), as_str_list(standardized.index))
    plt.title("Standardized median biomarker profile by health status")
    save_plot(figures_dir / "fig28_standardized_biomarker_profile_by_health_status.png")


def monthly_health_coverage(df: pd.DataFrame, figures_dir: Path) -> None:
    """
    Monthly stacked health-status record coverage.
    """
    if "datum_date" not in df.columns or "health_status" not in df.columns:
        return

    tmp = df[["datum_date", "health_status"]].dropna().copy()
    tmp["month"] = tmp["datum_date"].dt.to_period("M").astype(str)
    tmp["health_status"] = tmp["health_status"].astype(str)

    counts = pd.crosstab(tmp["month"], tmp["health_status"])

    ordered_cols = [c for c in HEALTH_ORDER if c in counts.columns]
    ordered_cols += [c for c in counts.columns if c not in ordered_cols]
    counts = counts[ordered_cols]

    plt.figure(figsize=(12, 5.8))
    x = np.arange(len(counts.index))
    bottom = np.zeros(len(counts.index))

    for status in counts.columns:
        values = counts[status].to_numpy(dtype=float)
        plt.bar(x, values, bottom=bottom, label=str(status))
        bottom += values

    plt.xticks(x, as_str_list(counts.index), rotation=60, ha="right")
    plt.ylabel("Daily records")
    plt.xlabel("Month")
    plt.title("Monthly observation coverage by health status")
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    save_plot(figures_dir / "fig22_monthly_health_status_coverage.png")


def missingness_by_variable_group(df: pd.DataFrame, figures_dir: Path) -> None:
    """
    Groups variables into broad measurement blocks for a more interpretable missingness plot.
    """
    groups = {
        "Milk / production": ["mkg", "fett", "eiweiss", "laktose", "harnstoff", "zellzahl"],
        "Body condition": ["bcs", "rfd", "kgw", "backfat"],
        "Metabolic biomarkers": ["bhb", "nefa", "insulin", "glucose", "igf", "ca"],
        "Time / animal info": ["ltg", "datum_date", "farm", "lom", "rasse"],
    }

    rows = []
    for group_name, cols in groups.items():
        present_cols = [c for c in cols if c in df.columns]
        if not present_cols:
            continue

        missing_pct = df[present_cols].isna().mean().mean() * 100
        rows.append({"group": group_name, "missing_percent": missing_pct})

    if not rows:
        return

    summary = pd.DataFrame(rows).sort_values("missing_percent", ascending=True)

    plt.figure(figsize=(9, 5))
    plt.barh(
        summary["group"].astype(str).tolist(),
        summary["missing_percent"].astype(float).tolist(),
    )
    plt.xlabel("Average missingness (%)")
    plt.title("Average missingness by measurement block")
    save_plot(figures_dir / "fig29_missingness_by_measurement_block.png")


def make_figures(df: pd.DataFrame, tables: dict, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)

    episode_df = make_episode_level(df)

    # ------------------------------------------------------------
    # 1. Core dataset and health-status structure
    # ------------------------------------------------------------
    health_rows = tables["health_rows"].set_index("health_status")["count"]
    health_episodes = tables["health_episodes"].set_index("health_status")["count"]

    barh(
        health_rows,
        "Health status distribution - daily records",
        "Daily records",
        figures_dir / "fig01_health_status_daily_records.png",
    )

    barh(
        health_episodes,
        "Health status distribution - lactation episodes",
        "Approx. lactation episodes",
        figures_dir / "fig02_health_status_lactation_episodes.png",
    )

    bar(
        df.groupby("farm").size().sort_index(),
        "Daily records by anonymized farm",
        "Daily records",
        figures_dir / "fig03_records_by_farm.png",
    )

    bar(
        df.groupby("farm")["lom"].nunique().sort_index(),
        "Unique animals by anonymized farm",
        "Unique animals",
        figures_dir / "fig04_animals_by_farm.png",
    )

    breed_animals = df.groupby("rasse")["lom"].nunique().sort_values(ascending=False)
    breed_animals.index = [
        f"Breed code {int(x)}" if pd.notna(x) else "Missing"
        for x in breed_animals.index
    ]

    bar(
        breed_animals,
        "Unique animals by breed code",
        "Unique animals",
        figures_dir / "fig05_animals_by_breed_code.png",
    )

    monthly = df.groupby(df["datum_date"].dt.to_period("M")).size()

    plt.figure(figsize=(11, 5.5))
    plt.plot(
        [str(x) for x in monthly.index.tolist()],
        [float(y) for y in monthly.to_numpy()],
        marker="o",
        linewidth=2,
    )
    plt.xticks(rotation=45, ha="right")
    plt.title("Observation coverage over time")
    plt.xlabel("Month")
    plt.ylabel("Daily records")
    save_plot(figures_dir / "fig06_records_over_time.png")

    # ------------------------------------------------------------
    # 2. Missingness and measurement availability
    # ------------------------------------------------------------
    top_missing = tables["missingness"].head(20).set_index("variable")["missing_percent"]

    barh(
        top_missing,
        "Top 20 variables by missingness",
        "Missing (%)",
        figures_dir / "fig07_missingness_top20.png",
    )

    missingness_by_variable_group(df, figures_dir)

    # ------------------------------------------------------------
    # 3. Time and production variable distributions
    # ------------------------------------------------------------
    hist(
        df["ltg"],
        "Distribution of day in milk",
        "Day in milk",
        figures_dir / "fig08_day_in_milk_distribution.png",
    )

    hist(
        df["mkg"],
        "Distribution of milk yield",
        "Milk yield (kg)",
        figures_dir / "fig09_milk_yield_distribution.png",
    )

    # ------------------------------------------------------------
    # 4. Disease labels and disease categories
    # ------------------------------------------------------------
    disease_series = tables["disease_category"].set_index("category")["daily_event_rows"]

    barh(
        disease_series,
        "Disease-category event rows",
        "Daily diagnosis/event rows",
        figures_dir / "fig10_disease_category_event_rows.png",
    )

    top_diag = tables["disease_diagnosis"].head(15).set_index("diagnosis")["daily_event_rows"]

    barh(
        top_diag,
        "Top diagnosis labels",
        "Daily diagnosis/event rows",
        figures_dir / "fig11_top_diagnoses.png",
    )

    # ------------------------------------------------------------
    # 5. Biomarker availability and biomarker profiles
    # ------------------------------------------------------------
    available_biomarkers = [c for c in BIOMARKERS if c in df.columns]

    if available_biomarkers:
        barh(
            df[available_biomarkers].notna().sum().sort_values(ascending=False),
            "Blood/urine biomarker availability",
            "Non-missing records",
            figures_dir / "fig12_biomarker_availability.png",
        )

        biomarker_availability_by_health(df, figures_dir)
        biomarker_median_by_health(df, figures_dir)

    # ------------------------------------------------------------
    # 6. Group comparisons by health status
    # ------------------------------------------------------------
    boxplot_sample(
        df,
        "mkg",
        figures_dir / "fig13_milk_yield_by_health_status.png",
        "Milk yield by health status",
        "Milk yield (kg)",
    )

    boxplot_sample(
        df,
        "bhb",
        figures_dir / "fig14_bhb_by_health_status.png",
        "BHB by health status",
        "BHB",
    )

    boxplot_sample(
        df,
        "nefa",
        figures_dir / "fig15_nefa_by_health_status.png",
        "NEFA by health status",
        "NEFA",
    )

    # ------------------------------------------------------------
    # 7. Correlation structure
    # ------------------------------------------------------------
    corr_cols = [
        c for c in CORR_COLS
        if c in df.columns and df[c].notna().sum() > 1000
    ]

    if len(corr_cols) >= 2:
        sample = df[corr_cols].sample(n=min(len(df), 50000), random_state=42)
        corr = sample.corr(method="spearman")

        plt.figure(figsize=(9.5, 8.5))
        im = plt.imshow(corr.values, aspect="auto", vmin=-1, vmax=1)
        plt.colorbar(im, label="Spearman correlation")
        plt.xticks(
            range(len(corr.columns)),
            [str(x) for x in corr.columns.tolist()],
            rotation=45,
            ha="right",
        )
        plt.yticks(
            range(len(corr.index)),
            [str(x) for x in corr.index.tolist()],
        )
        plt.title("Selected numeric variables - Spearman correlation")
        save_plot(figures_dir / "fig16_selected_numeric_correlation.png")

    # ------------------------------------------------------------
    # 8. New deeper EDA: health status by farm, breed and lactation
    # ------------------------------------------------------------
    stacked_percent_plot(
        episode_df,
        "farm",
        "Health-status composition by farm",
        figures_dir / "fig17_health_status_by_farm_percent.png",
        min_count=5,
    )

    if "rasse" in episode_df.columns:
        breed_episode_df = episode_df.copy()
        breed_episode_df["rasse"] = breed_episode_df["rasse"].apply(
            lambda x: f"Breed code {int(x)}" if pd.notna(x) else "Missing"
        )

        stacked_percent_plot(
            breed_episode_df,
            "rasse",
            "Health-status composition by breed",
            figures_dir / "fig18_health_status_by_breed_percent.png",
            min_count=5,
        )

    lactation_col = None
    for candidate in ["ln", "laktation", "lactation", "lactation_number"]:
        if candidate in episode_df.columns:
            lactation_col = candidate
            break

    if lactation_col is not None:
        stacked_percent_plot(
            episode_df,
            lactation_col,
            "Health-status composition by lactation number",
            figures_dir / "fig19_health_status_by_lactation_percent.png",
            min_count=5,
        )

    rate_by_group_plot(
        episode_df,
        "farm",
        "Production-disease episode rate by farm",
        figures_dir / "fig20_production_disease_rate_by_farm.png",
        min_count=5,
    )

    if "rasse" in episode_df.columns:
        rate_by_group_plot(
            breed_episode_df,
            "rasse",
            "Production-disease episode rate by breed",
            figures_dir / "fig21_production_disease_rate_by_breed.png",
            min_count=5,
        )

    # ------------------------------------------------------------
    # 9. New deeper EDA: monthly health-status coverage
    # ------------------------------------------------------------
    monthly_health_coverage(df, figures_dir)

    # ------------------------------------------------------------
    # 10. New deeper EDA: trajectories over day in milk
    # ------------------------------------------------------------
    line_trend_by_health_status(
        df,
        "mkg",
        "Median milk yield (kg)",
        "Median milk yield trajectory by health status",
        figures_dir / "fig23_milk_yield_dim_trend_by_health_status.png",
    )

    line_trend_by_health_status(
        df,
        "bhb",
        "Median BHB",
        "Median BHB trajectory by health status",
        figures_dir / "fig24_bhb_dim_trend_by_health_status.png",
    )

    line_trend_by_health_status(
        df,
        "nefa",
        "Median NEFA",
        "Median NEFA trajectory by health status",
        figures_dir / "fig25_nefa_dim_trend_by_health_status.png",
    )

    if "fett" in df.columns and "eiweiss" in df.columns:
        df_fe = df.copy()
        df_fe["fat_protein_ratio"] = (
            pd.to_numeric(df_fe["fett"], errors="coerce")
            / pd.to_numeric(df_fe["eiweiss"], errors="coerce")
        )

        line_trend_by_health_status(
            df_fe,
            "fat_protein_ratio",
            "Median fat/protein ratio",
            "Median fat/protein ratio trajectory by health status",
            figures_dir / "fig26_fat_protein_ratio_dim_trend_by_health_status.png",
        )


def write_auto_numbers(tables: dict, presentation_dir: Path) -> None:
    presentation_dir.mkdir(parents=True, exist_ok=True)
    overview = dict(zip(tables["overview"]["metric"], tables["overview"]["value"]))
    health = tables["health_rows"].set_index("health_status")
    episodes = tables["health_episodes"].set_index("health_status")
    farm_summary = tables["farm_summary"]
    missingness = tables["missingness"]
    disease_category = tables["disease_category"]
    macros = {
        "TotalRows": f"{int(overview['rows_daily_records']):,}",
        "TotalAnimals": f"{int(overview['animals_unique_lom']):,}",
        "TotalFarms": f"{int(overview['farms_unique']):,}",
        "TotalEpisodes": f"{int(overview['lactation_episodes_approx']):,}",
        "ObservationStart": str(overview["observation_start"]),
        "ObservationEnd": str(overview["observation_end"]),
        "HealthyRows": f"{int(health.loc['Healthy','count']):,}",
        "ProductionRows": f"{int(health.loc['Production disease','count']):,}",
        "OtherRows": f"{int(health.loc['Other disease','count']):,}",
        "MixedRows": f"{int(health.loc['Production + other disease','count']):,}",
        "HealthyEpisodes": f"{int(episodes.loc['Healthy','count']):,}",
        "ProductionEpisodes": f"{int(episodes.loc['Production disease','count']):,}",
        "HighestFarmRows": str(int(farm_summary.sort_values('rows', ascending=False).iloc[0]['farm'])),
        "TopMissingVariable": str(missingness.iloc[0]["variable"]).replace("_", r"\_"),
        "TopDiseaseCategory": str(disease_category.iloc[0]["category"]),
        "TopDiseaseEventRows": f"{int(disease_category.iloc[0]['daily_event_rows']):,}",
    }
    text = "% Auto-generated by src/02_run_eda.py. Do not edit by hand.\n"
    for key, value in macros.items():
        text += f"\\newcommand{{\\{key}}}{{{value}}}\n"
    (presentation_dir / "auto_numbers.tex").write_text(text, encoding="utf-8")


def write_markdown_summary(tables: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    overview = dict(zip(tables["overview"]["metric"], tables["overview"]["value"]))
    health = tables["health_episodes"]
    disease = tables["disease_category"]
    missing = tables["missingness"]
    lines = ["# OptiKuh EDA summary", "", "## Data structure"]
    lines += [
        f"- Daily records: {int(overview['rows_daily_records']):,}",
        f"- Variables: {int(overview['columns_original']):,}",
        f"- Animals: {int(overview['animals_unique_lom']):,}",
        f"- Farms: {int(overview['farms_unique']):,}",
        f"- Approx. lactation episodes: {int(overview['lactation_episodes_approx']):,}",
        f"- Observation window: {overview['observation_start']} to {overview['observation_end']}",
        "", "## Health status by lactation episode",
    ]
    for _, row in health.iterrows():
        lines.append(f"- {row['health_status']}: {int(row['count']):,} ({row['percent']:.2f}%)")
    lines += ["", "## Main disease categories by daily event rows"]
    for _, row in disease.iterrows():
        lines.append(f"- {row['category']}: {int(row['daily_event_rows']):,} rows, {int(row['unique_episodes']):,} episodes")
    lines += ["", "## Highest missingness"]
    for _, row in missing.head(10).iterrows():
        lines.append(f"- {row['variable']}: {row['missing_percent']:.2f}% missing")
    lines += ["", "## Speaking focus", "- This is a longitudinal daily dataset, but the outcome status is defined at lactation level.", "- Biomarker variables are sparse by design because blood/urine samples were collected on specific days.", "- No modelling is done here; all results are descriptive EDA."]
    (reports_dir / "eda_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    tables_dir = args.out / "tables"
    figures_dir = args.out / "figures"
    reports_dir = args.out / "reports"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    print("Loading data...", flush=True)
    df = load_data(args.csv)
    meta = load_meta(args.meta)
    print("Making tables...", flush=True)
    tables = make_tables(df, meta, tables_dir)
    print("Making figures...", flush=True)
    make_figures(df, tables, figures_dir)
    write_auto_numbers(tables, args.presentation)
    write_markdown_summary(tables, reports_dir)
    print(f"Done. Tables: {tables_dir}", flush=True)
    print(f"Done. Figures: {figures_dir}", flush=True)

if __name__ == "__main__":
    main()