import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path

st.set_page_config(
    page_title="Irish Elections Explorer",
    page_icon="🗳️",
    layout="wide"
)

PARTY_COLORS = {
    'Fianna Fáil': '#66BB66',
    'Fine Gael': '#6699FF',
    'Labour': '#CC0000',
    'Labour Party': '#CC0000',
    'Sinn Féin': '#326760',
    'Green Party': '#99CC33',
    'Independent': '#AAAAAA',
    'Cumann na nGaedheal': '#4169E1',
    'Progressive Democrats': '#0000CD',
}

COUNTY_COORDS = {
    'Dublin': (53.35, -6.26), 'Wicklow': (52.98, -6.05), 'Wexford': (52.47, -6.46),
    'Carlow': (52.84, -6.93), 'Kilkenny': (52.65, -7.25), 'Laois': (53.03, -7.55),
    'Offaly': (53.23, -7.72), 'Westmeath': (53.52, -7.45), 'Longford': (53.73, -7.80),
    'Meath': (53.65, -6.66), 'Louth': (53.92, -6.49), 'Kildare': (53.16, -6.91),
    'Cork': (51.90, -8.47), 'Kerry': (52.15, -9.57), 'Limerick': (52.66, -8.63),
    'Clare': (52.84, -8.98), 'Tipperary': (52.47, -7.86), 'Waterford': (52.26, -7.11),
    'Galway': (53.27, -8.86), 'Mayo': (53.90, -9.30), 'Sligo': (54.27, -8.47),
    'Leitrim': (54.15, -8.00), 'Roscommon': (53.63, -8.19),
    'Donegal': (54.95, -7.73), 'Cavan': (53.99, -7.36), 'Monaghan': (54.25, -6.97),
}


def get_constituency_coords(const_name):
    const_lower = str(const_name).lower()
    for county, coords in COUNTY_COORDS.items():
        if county.lower() in const_lower:
            return coords
    return (53.5, -7.5)


@st.cache_data
def load_data():
    df = pd.read_parquet('irelandelection/ALL_CANDIDATES.parquet')
    df = df.rename(columns={
        'first_pref_quota_ratio': 'quota_ratio',
        'constituency': 'constituency_name'
    })
    df['year'] = df['year'].astype(int)
    df['won'] = df['elected'].astype(bool)

    with open('factoids.json', 'r', encoding='utf-8') as f:
        factoids = json.load(f)

    gender_df = None
    gender_stats = None
    if Path('electionsireland_data/DAIL_elections_master.parquet').exists():
        gender_df = pd.read_parquet('electionsireland_data/DAIL_elections_master.parquet')
        gender_df['year'] = pd.to_datetime(gender_df['election_date']).dt.year
        gender_df['elected'] = gender_df['status'].isin(['Made Quota', 'Elected', 'Without reaching quota'])

    if Path('gender_stats.json').exists():
        with open('gender_stats.json', 'r', encoding='utf-8') as f:
            gender_stats = json.load(f)

    return df, factoids, gender_df, gender_stats


def main():
    st.title("Irish Elections Explorer")
    st.markdown("*100 Years of Dáil Elections: 1920-2020*")

    df, factoids, gender_df, gender_stats = load_data()

    st.sidebar.header("Filters")

    election_types = st.sidebar.multiselect(
        "Election Type",
        options=df['election_type'].unique().tolist(),
        default=['GENERAL']
    )

    year_range = st.sidebar.slider(
        "Year Range",
        min_value=int(df['year'].min()),
        max_value=int(df['year'].max()),
        value=(1960, 2020)
    )

    filtered_df = df[
        (df['election_type'].isin(election_types)) &
        (df['year'] >= year_range[0]) &
        (df['year'] <= year_range[1])
    ]

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Overview",
        "Party Analysis",
        "Gender",
        "Map",
        "Constituency",
        "Search"
    ])

    with tab1:
        st.header("Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Records", f"{len(filtered_df):,}")
        with col2:
            st.metric("Elections", filtered_df['year'].nunique())
        with col3:
            winners = filtered_df[filtered_df['won']]
            st.metric("Winners", f"{len(winners):,}")
        with col4:
            avg_quota = filtered_df[filtered_df['won']]['quota_ratio'].mean()
            st.metric("Avg Winner Quota", f"{avg_quota:.0%}" if pd.notna(avg_quota) else "N/A")

        st.subheader("What Does It Take to Win?")

        general = filtered_df[filtered_df['election_type'] == 'GENERAL'].copy()
        winners_q = general[general['won']]['quota_ratio'].dropna()
        losers_q = general[~general['won']]['quota_ratio'].dropna()

        winners_q = winners_q[(winners_q > 0) & (winners_q < 2.5)]
        losers_q = losers_q[(losers_q > 0) & (losers_q < 2.5)]

        fig = go.Figure()
        fig.add_trace(go.Histogram(x=losers_q, name='Lost', marker_color='#E74C3C', opacity=0.6))
        fig.add_trace(go.Histogram(x=winners_q, name='Won', marker_color='#27AE60', opacity=0.6))
        fig.update_layout(
            barmode='overlay',
            xaxis_title='First Preferences as Fraction of Quota',
            yaxis_title='Count',
            title='Distribution of First Preference Performance'
        )
        fig.add_vline(x=1.0, line_dash="dash", line_color="black", annotation_text="Quota")

        st.plotly_chart(fig, use_container_width=True)

        st.info(f"""
        **Key Insight**: Winners typically need **{factoids['quota_analysis']['winners_median']:.0%}** of the quota
        on first preferences, while losers average only **{factoids['quota_analysis']['losers_median']:.0%}**.
        """)

    with tab2:
        st.header("Party Analysis")

        party_trends = pd.DataFrame(factoids['party_trends'])
        main_parties = ['Fianna Fáil', 'Fine Gael', 'Labour', 'Sinn Féin', 'Independent']

        party_select = st.multiselect(
            "Select parties to display",
            options=party_trends['party'].unique().tolist(),
            default=main_parties
        )

        chart_data = party_trends[party_trends['party'].isin(party_select)]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Seats Won by Decade")
            fig = px.line(
                chart_data, x='decade', y='wins', color='party',
                markers=True, color_discrete_map=PARTY_COLORS
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Win Rate by Decade")
            fig2 = px.line(
                chart_data, x='decade', y='win_rate', color='party',
                markers=True, color_discrete_map=PARTY_COLORS
            )
            fig2.update_layout(yaxis_title='Win Rate (%)')
            st.plotly_chart(fig2, use_container_width=True)

        st.success("""
        **2020 Highlight**: Sinn Féin achieved an **88.1% win rate** - 37 out of 42 candidates won!
        """)

    with tab3:
        st.header("Gender Representation")

        if gender_stats:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Female Candidates", f"{gender_stats['total']['female_candidates']}")
            with col2:
                st.metric("Female TDs Elected", f"{gender_stats['winners']['female']}")
            with col3:
                st.metric("Female Win Rate", f"{gender_stats['win_rates']['female']}%")

            st.subheader("Women's Representation Over Time")

            years = sorted(gender_stats['by_year']['female_pct'].keys())
            female_pct = [gender_stats['by_year']['female_pct'][y] for y in years]
            winner_pct = [gender_stats['winners_by_year']['female_elected_pct'].get(y, 0) for y in years]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[int(y) for y in years], y=female_pct,
                mode='lines+markers', name='Female Candidates %',
                line=dict(color='#9B59B6'), fill='tozeroy'
            ))
            fig.add_trace(go.Scatter(
                x=[int(y) for y in years], y=winner_pct,
                mode='lines+markers', name='Female TDs Elected %',
                line=dict(color='#E74C3C'), fill='tozeroy'
            ))
            fig.update_layout(
                xaxis_title='Year', yaxis_title='Percentage (%)',
                title='Women in Irish Politics: A Century of Progress'
            )
            st.plotly_chart(fig, use_container_width=True)

            st.info("""
            **Surprising Finding**: Women have a **14.7% win rate** compared to **12.6%** for men.
            When women run, they're more likely to win!
            """)

            st.subheader("Pioneering Women")
            pioneers = pd.DataFrame(gender_stats['pioneering_women'])
            st.dataframe(pioneers, use_container_width=True)

        else:
            st.warning("Gender data not available. Run gender_analysis.py first.")

    with tab4:
        st.header("Geographic Distribution")

        general = df[df['election_type'] == 'GENERAL'].copy()
        winners = general[general['won']]

        const_party = winners.groupby(['constituency_name', 'party']).size().reset_index(name='seats')
        const_dominant = const_party.loc[const_party.groupby('constituency_name')['seats'].idxmax()]

        const_stats = winners.groupby('constituency_name').agg({
            'candidate': 'count'
        }).reset_index()
        const_stats.columns = ['constituency_name', 'total_seats']

        const_stats = const_stats.merge(
            const_dominant[['constituency_name', 'party', 'seats']],
            on='constituency_name'
        )
        const_stats = const_stats.rename(columns={'party': 'dominant_party'})

        const_stats['lat'] = const_stats['constituency_name'].apply(lambda x: get_constituency_coords(x)[0])
        const_stats['lon'] = const_stats['constituency_name'].apply(lambda x: get_constituency_coords(x)[1])
        const_stats['color'] = const_stats['dominant_party'].map(lambda x: PARTY_COLORS.get(x, '#888888'))

        fig = px.scatter_mapbox(
            const_stats,
            lat='lat', lon='lon',
            color='dominant_party',
            size='total_seats',
            hover_name='constituency_name',
            hover_data={'seats': True, 'dominant_party': True},
            color_discrete_map=PARTY_COLORS,
            zoom=5.5,
            center=dict(lat=53.5, lon=-7.8),
            mapbox_style='carto-positron',
            title='Party Dominance by Constituency'
        )
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Regional Summary")

        def get_region(const):
            const = str(const).lower()
            if 'dublin' in const: return 'Dublin'
            elif 'cork' in const: return 'Cork'
            elif 'galway' in const: return 'Galway'
            elif 'limerick' in const: return 'Limerick'
            elif any(x in const for x in ['donegal', 'cavan', 'monaghan']): return 'Ulster (ROI)'
            elif any(x in const for x in ['mayo', 'sligo', 'roscommon', 'leitrim']): return 'Connacht'
            else: return 'Other'

        winners['region'] = winners['constituency_name'].apply(get_region)
        region_summary = winners.groupby(['region', 'party']).size().unstack(fill_value=0)

        st.dataframe(region_summary.head(10), use_container_width=True)

    with tab5:
        st.header("Constituency Lookup")

        constituencies = sorted(filtered_df['constituency_name'].dropna().unique().tolist())
        selected_const = st.selectbox("Select a constituency", constituencies)

        const_data = filtered_df[filtered_df['constituency_name'] == selected_const]

        if len(const_data) > 0:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Statistics")
                winners_const = const_data[const_data['won']]
                st.metric("Elections Covered", const_data['year'].nunique())
                st.metric("Total Candidates", len(const_data))
                st.metric("Seats Filled", len(winners_const))

            with col2:
                st.subheader("Party Breakdown")
                party_counts = winners_const.groupby('party').size().sort_values(ascending=False)
                fig = px.pie(
                    values=party_counts.values[:6],
                    names=party_counts.index[:6],
                    color=party_counts.index[:6],
                    color_discrete_map=PARTY_COLORS
                )
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Recent Results")
            recent = const_data.sort_values('year', ascending=False).head(20)
            st.dataframe(
                recent[['year', 'candidate', 'party', 'elected', 'first_pref_pct', 'quota_ratio']].reset_index(drop=True),
                use_container_width=True
            )

    with tab6:
        st.header("Candidate Search")

        search_term = st.text_input("Search for a candidate name (min 3 characters)")

        if search_term and len(search_term) >= 3:
            matches = df[df['candidate'].str.contains(search_term, case=False, na=False)]

            if len(matches) > 0:
                st.write(f"Found **{len(matches)}** records")

                candidates = matches.groupby('candidate').agg({
                    'year': ['min', 'max', 'count'],
                    'elected': 'sum',
                    'party': lambda x: ', '.join(x.unique()[:3]),
                    'constituency_name': lambda x: ', '.join(x.unique()[:3])
                }).reset_index()

                candidates.columns = ['Name', 'First Year', 'Last Year', 'Elections',
                                     'Times Elected', 'Parties', 'Constituencies']

                st.dataframe(
                    candidates.sort_values('Times Elected', ascending=False),
                    use_container_width=True
                )

                if st.checkbox("Show detailed records"):
                    st.dataframe(matches.sort_values(['candidate', 'year']), use_container_width=True)
            else:
                st.warning("No candidates found.")

    st.markdown("---")
    st.markdown("""
    **Data Sources**: [ElectionsIreland.org](https://electionsireland.org),
    [IrelandElection.com](https://irelandelection.com) |
    *Built with Streamlit* |
    [View Article](ARTICLE.md)
    """)


if __name__ == "__main__":
    main()
