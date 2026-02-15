# Irish Elections Analysis

Analysis of 36,000+ candidate records spanning 100 years of Irish Dáil elections (1920–2020).

**[Read the article](https://fingers53.github.io/irish-elections-analysis/)**

## Key Findings

- Winners average **82% of quota** on first preferences alone — transfers matter, but less than you'd think
- Sinn Féin's 2020 campaign was the most efficient in modern Irish history (**88% win rate**)
- Women have a higher win rate than men (14.7% vs 12.6%), likely due to selection bias
- Independents collapsed to a 3% win rate in the 1980s, then rebounded to 15% by 2020

## Data Sources

- [ElectionsIreland.org](https://electionsireland.org) — 30,070 records
- [IrelandElection.com](https://irelandelection.com) — 36,243 records

## Running Locally

```bash
pip install -r requirements.txt

# Run analysis (generates factoids.json, visualizations, etc.)
python analyze_elections.py
python gender_analysis.py
python geographic_map.py

# Launch the interactive dashboard
streamlit run streamlit_app.py
```

## Project Structure

```
├── streamlit_app.py            # Interactive Streamlit dashboard
├── analyze_elections.py        # Core analysis and factoid extraction
├── data_pipeline.py            # Data cleaning and source merging
├── gender_analysis.py          # Gender representation analysis
├── geographic_map.py           # Map visualizations
├── visualizations.py           # Static chart generation
├── combining_data_sources.ipynb  # Notebook: data pipeline walkthrough
├── quota_analysis.ipynb        # Notebook: quota ratio analysis
├── ARTICLE.md                  # Full write-up
├── docs/                       # GitHub Pages site
├── irelandelection/            # Source data (parquet)
├── electionsireland_data/      # Source data (parquet)
└── requirements.txt
```

## License

MIT
