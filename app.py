from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path(__file__).parent / "data" / "sec_firm_fundamentals_2026q2.csv"
ALL_INDUSTRIES = "All industries"

METRICS = {
    "Return on assets (ROA)": {
        "column": "roa_pct",
        "description": "Net income divided by total assets",
        "unit": "%",
    },
    "Current ratio": {
        "column": "current_ratio",
        "description": "Current assets divided by current liabilities",
        "unit": "x",
    },
    "Liabilities to assets": {
        "column": "liabilities_to_assets_pct",
        "description": "Total liabilities divided by total assets",
        "unit": "%",
    },
    "Net profit margin": {
        "column": "profit_margin_pct",
        "description": "Net income divided by reported revenue",
        "unit": "%",
    },
}


@st.cache_data
def load_firms() -> pd.DataFrame:
    firms = pd.read_csv(DATA_PATH, dtype={"ticker": "string", "sic": "string"})
    numeric_columns = [
        "revenue_usd_millions",
        "net_income_usd_millions",
        "assets_usd_millions",
        "current_assets_usd_millions",
        "current_liabilities_usd_millions",
        "liabilities_usd_millions",
        "fiscal_year",
    ]
    firms[numeric_columns] = firms[numeric_columns].apply(
        pd.to_numeric, errors="coerce"
    )
    firms["ticker"] = firms["ticker"].fillna("").str.strip()
    firms["industry"] = firms["industry"].fillna("Unclassified")
    firms["roa_pct"] = (
        firms["net_income_usd_millions"]
        .div(firms["assets_usd_millions"].where(firms["assets_usd_millions"] > 0))
        .mul(100)
    )
    firms["current_ratio"] = firms["current_assets_usd_millions"].div(
        firms["current_liabilities_usd_millions"].where(
            firms["current_liabilities_usd_millions"] > 0
        )
    )
    firms["liabilities_to_assets_pct"] = (
        firms["liabilities_usd_millions"]
        .div(firms["assets_usd_millions"].where(firms["assets_usd_millions"] > 0))
        .mul(100)
    )
    firms["profit_margin_pct"] = (
        firms["net_income_usd_millions"]
        .div(firms["revenue_usd_millions"].where(firms["revenue_usd_millions"] > 0))
        .mul(100)
    )
    return firms


def main() -> None:
    st.set_page_config(
        page_title="Financial Peer Analyzer",
        page_icon="📊",
        layout="wide",
    )
    st.title("Financial Peer Analyzer")
    st.write(
        "Explore audited annual filings from **565 U.S. public-company issuers**. "
        "Filter to an SEC industry and compare each firm with its peers."
    )

    firms = load_firms()
    st.sidebar.header("Peer filters")
    metric_name = st.sidebar.selectbox("Financial metric", list(METRICS))
    metric = METRICS[metric_name]
    metric_column = metric["column"]

    available = firms.dropna(subset=[metric_column]).copy()
    if available.empty:
        st.error(f"No companies have data for {metric_name}.")
        return

    industry_counts = available.groupby("industry").size().sort_values(ascending=False)
    industry_options = [ALL_INDUSTRIES, *industry_counts.index.tolist()]
    industry_choice = st.sidebar.selectbox(
        "SEC industry",
        industry_options,
        index=1 if len(industry_options) > 1 else 0,
        format_func=lambda industry: (
            ALL_INDUSTRIES
            if industry == ALL_INDUSTRIES
            else f"{industry} · {industry_counts[industry]} firms"
        ),
    )

    fiscal_years = sorted(
        int(year) for year in available["fiscal_year"].dropna().unique()
    )
    year_options = ["All fiscal years", *fiscal_years]
    fiscal_year = st.sidebar.selectbox("Fiscal year", year_options)
    search = st.sidebar.text_input("Find a firm or ticker")

    filtered = available
    if industry_choice != ALL_INDUSTRIES:
        filtered = filtered[filtered["industry"] == industry_choice]
    if fiscal_year != "All fiscal years":
        filtered = filtered[filtered["fiscal_year"] == fiscal_year]
    if search.strip():
        query = search.strip().casefold()
        matches = filtered["company"].str.casefold().str.contains(query, na=False)
        matches |= filtered["ticker"].str.casefold().str.contains(query, na=False)
        filtered = filtered[matches]

    if filtered.empty:
        st.warning("No firms match these filters. Try another industry, year, or search.")
        return

    include_extremes = st.sidebar.checkbox(
        "Include extreme metric values", value=False
    )
    low = float(filtered[metric_column].quantile(0.01))
    high = float(filtered[metric_column].quantile(0.99))
    if include_extremes:
        low = float(filtered[metric_column].min())
        high = float(filtered[metric_column].max())
    if low < high:
        metric_range = st.sidebar.slider(
            f"{metric_name} range ({metric['unit']})",
            min_value=low,
            max_value=high,
            value=(low, high),
            step=max((high - low) / 200, 0.01),
            help=(
                "By default, the range covers the 1st–99th percentiles to keep "
                "extreme filing values from obscuring peer comparisons."
            ),
        )
        filtered = filtered[filtered[metric_column].between(*metric_range)]

    if filtered.empty:
        st.warning("No firms fall within this metric range.")
        return

    selected_values = filtered[metric_column]
    median_value = float(selected_values.median())
    mean_value = float(selected_values.mean())
    st.caption(
        f"Metric: {metric['description']}. Values are calculated from annual "
        "SEC filings; financial amounts are reported in USD millions."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Firms in peer sample", f"{len(filtered):,}")
    col2.metric(
        "Industry",
        "All industries" if industry_choice == ALL_INDUSTRIES else industry_choice,
    )
    col3.metric(
        f"Peer median ({metric['unit']})",
        f"{median_value:,.2f}",
    )
    col4.metric(
        f"Peer mean ({metric['unit']})",
        f"{mean_value:,.2f}",
    )

    if industry_choice == ALL_INDUSTRIES:
        st.subheader("Industry-level comparison")
        industry_summary = (
            filtered.groupby("industry", as_index=False)
            .agg(
                firms=("company", "size"),
                median_metric=(metric_column, "median"),
            )
            .sort_values("firms", ascending=False)
            .head(20)
            .sort_values("median_metric")
        )
        if not industry_summary.empty:
            fig = px.bar(
                industry_summary,
                x="median_metric",
                y="industry",
                orientation="h",
                color="firms",
                hover_data={"firms": True, "median_metric": ":.2f"},
                labels={
                    "median_metric": f"Median {metric_name} ({metric['unit']})",
                    "industry": "SEC industry",
                    "firms": "Firms",
                },
                title="Largest industries by firm count",
                color_continuous_scale="Blues",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch")
    else:
        st.subheader(f"Within-industry peer distribution: {industry_choice}")
        fig = px.box(
            filtered,
            x=metric_column,
            points="all",
            hover_data=["ticker", "company", "fiscal_year"],
            labels={metric_column: f"{metric_name} ({metric['unit']})"},
            title=f"{metric_name} across {len(filtered)} peer firms",
        )
        st.plotly_chart(fig, width="stretch")

    st.subheader("Firm-level peer ranking")
    ranking = filtered.copy()
    ranking["Peer percentile"] = ranking[metric_column].rank(pct=True) * 100
    ranking = ranking.sort_values(metric_column, ascending=False)
    table = ranking[
        [
            "ticker",
            "company",
            "industry",
            "fiscal_year",
            "period_end",
            metric_column,
            "Peer percentile",
        ]
    ].rename(
        columns={
            "ticker": "Ticker",
            "company": "Company",
            "industry": "SEC industry",
            "fiscal_year": "Fiscal year",
            "period_end": "Period end",
            metric_column: f"{metric_name} ({metric['unit']})",
        }
    )
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "Peer percentile": st.column_config.NumberColumn(format="%.1f%%"),
            f"{metric_name} ({metric['unit']})": st.column_config.NumberColumn(
                format="%.2f"
            ),
        },
    )
    st.download_button(
        "Download filtered peer sample (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="financial_peer_sample.csv",
        mime="text/csv",
    )

    st.divider()
    st.caption(
        "Source: SEC Financial Statement Data Sets, 2026 Q2 release. "
        "Industry labels use the SEC Standard Industrial Classification (SIC). "
        "This is a historical cross-sectional comparison, not investment advice. "
        "Ratios are unavailable where filings do not report the required facts."
    )
    with st.expander("Methodology and coverage"):
        coverage = pd.DataFrame(
            {
                "Metric": list(METRICS),
                "Firms with required facts": [
                    int(firms[definition["column"]].notna().sum())
                    for definition in METRICS.values()
                ],
                "Calculation": [
                    definition["description"] for definition in METRICS.values()
                ],
            }
        )
        st.dataframe(coverage, width="stretch", hide_index=True)
        st.markdown(
            "The bundled sample contains the latest annual 10-K filings included "
            "in the SEC's 2026 Q2 quarterly dataset. SEC facts are matched to the "
            "issuer's fiscal-year end and consolidated USD values where available. "
            "Each ratio is computed from the reported values; missing or invalid "
            "denominators are left blank rather than imputed. SIC industries can "
            "have very different sample sizes, so compare the displayed peer count "
            "before drawing conclusions."
        )
        st.markdown(
            "[SEC dataset](https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q2.zip) · "
            "[SEC SIC code list](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list)"
        )


if __name__ == "__main__":
    main()
