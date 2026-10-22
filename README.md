# Financial Peer Analyzer

A Streamlit app for exploring financial performance within industries. The
bundled sample contains **565 public-company issuers** from SEC annual filings,
classified with SEC Standard Industrial Classification (SIC) codes.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Analysis features

- Filter by SEC industry, fiscal year, firm name, and ticker.
- Compare return on assets, current ratio, liabilities-to-assets, or net profit
  margin.
- View peer distributions, industry medians, peer rankings, and export the
  filtered sample to CSV.
- Review metric coverage and calculations in the methodology panel.

The bundled sample is from the SEC Financial Statement Data Set for **2026 Q2**.
It contains annual 10-K filings for 565 issuers across 203 SIC industries. The
selected ratio is available for a subset of firms when a required fact is not
reported; the app displays the resulting sample size and coverage. Financial
amounts are in USD millions. It is a historical cross-sectional analysis, not
investment advice.

Sources: [SEC Financial Statement Data Sets](https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q2.zip) and
[SEC SIC code list](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list).
