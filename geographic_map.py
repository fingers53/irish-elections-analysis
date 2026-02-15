import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json

COUNTY_COORDS = {
    # Leinster
    'Dublin': (53.35, -6.26),
    'Wicklow': (52.98, -6.05),
    'Wexford': (52.47, -6.46),
    'Carlow': (52.84, -6.93),
    'Kilkenny': (52.65, -7.25),
    'Laois': (53.03, -7.55),
    'Offaly': (53.23, -7.72),
    'Westmeath': (53.52, -7.45),
    'Longford': (53.73, -7.80),
    'Meath': (53.65, -6.66),
    'Louth': (53.92, -6.49),
    'Kildare': (53.16, -6.91),

    # Munster
    'Cork': (51.90, -8.47),
    'Kerry': (52.15, -9.57),
    'Limerick': (52.66, -8.63),
    'Clare': (52.84, -8.98),
    'Tipperary': (52.47, -7.86),
    'Waterford': (52.26, -7.11),

    # Connacht
    'Galway': (53.27, -8.86),
    'Mayo': (53.90, -9.30),
    'Sligo': (54.27, -8.47),
    'Leitrim': (54.15, -8.00),
    'Roscommon': (53.63, -8.19),

    # Ulster (ROI)
    'Donegal': (54.95, -7.73),
    'Cavan': (53.99, -7.36),
    'Monaghan': (54.25, -6.97),
}


def get_constituency_coords(const_name):
    const_lower = const_name.lower()

    for county, coords in COUNTY_COORDS.items():
        if county.lower() in const_lower:
            # small random offset to prevent overlap
            return (coords[0] + np.random.uniform(-0.1, 0.1),
                   coords[1] + np.random.uniform(-0.1, 0.1))

    if 'dublin' in const_lower:
        return COUNTY_COORDS['Dublin']
    elif 'cork' in const_lower:
        return COUNTY_COORDS['Cork']
    elif 'galway' in const_lower:
        return COUNTY_COORDS['Galway']
    elif 'limerick' in const_lower:
        return COUNTY_COORDS['Limerick']

    return (53.5, -7.5)


def load_data():
    df = pd.read_parquet('irelandelection/ALL_CANDIDATES.parquet')
    df = df.rename(columns={'constituency': 'constituency_name'})
    df['year'] = df['year'].astype(int)
    df['won'] = df['elected'].astype(bool)
    return df


def create_constituency_summary(df):
    general = df[df['election_type'] == 'GENERAL'].copy()
    winners = general[general['won']]

    const_party = winners.groupby(['constituency_name', 'party']).size().reset_index(name='seats')
    const_dominant = const_party.loc[const_party.groupby('constituency_name')['seats'].idxmax()]

    const_stats = winners.groupby('constituency_name').agg({
        'year': ['min', 'max', 'nunique'],
        'candidate': 'count',
        'first_pref_quota_ratio': 'mean'
    }).reset_index()
    const_stats.columns = ['constituency_name', 'first_election', 'last_election',
                          'num_elections', 'total_seats', 'avg_quota']

    const_stats = const_stats.merge(
        const_dominant[['constituency_name', 'party', 'seats']],
        on='constituency_name',
        how='left'
    )
    const_stats = const_stats.rename(columns={'party': 'dominant_party', 'seats': 'dominant_party_seats'})

    const_stats['lat'] = const_stats['constituency_name'].apply(lambda x: get_constituency_coords(x)[0])
    const_stats['lon'] = const_stats['constituency_name'].apply(lambda x: get_constituency_coords(x)[1])

    return const_stats


def create_party_map(df, const_stats):
    party_colors = {
        'Fianna Fáil': '#66BB66',
        'Fine Gael': '#6699FF',
        'Labour Party': '#CC0000',
        'Labour': '#CC0000',
        'Sinn Féin': '#326760',
        'Independent': '#AAAAAA',
        'Cumann na nGaedheal': '#4169E1',
    }

    const_stats['color'] = const_stats['dominant_party'].map(
        lambda x: party_colors.get(x, '#888888')
    )

    fig = go.Figure()

    for party in const_stats['dominant_party'].unique():
        party_data = const_stats[const_stats['dominant_party'] == party]

        fig.add_trace(go.Scattergeo(
            lon=party_data['lon'],
            lat=party_data['lat'],
            text=party_data.apply(
                lambda r: f"<b>{r['constituency_name']}</b><br>"
                         f"Dominant: {r['dominant_party']}<br>"
                         f"Seats: {r['dominant_party_seats']}<br>"
                         f"Elections: {r['num_elections']}",
                axis=1
            ),
            marker=dict(
                size=party_data['total_seats'] / 2 + 5,
                color=party_colors.get(party, '#888888'),
                opacity=0.7,
                line=dict(width=1, color='white')
            ),
            name=party,
            hoverinfo='text'
        ))

    fig.update_layout(
        title='Party Dominance by Constituency<br><sub>Bubble size = total seats won</sub>',
        geo=dict(
            scope='europe',
            center=dict(lat=53.5, lon=-8.0),
            projection_scale=30,
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            coastlinecolor='rgb(150, 150, 150)',
            showocean=True,
            oceancolor='rgb(230, 240, 250)',
            showlakes=True,
            lakecolor='rgb(200, 220, 240)',
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        width=800,
        height=700
    )

    fig.write_html('map_party_dominance.html')
    print("Saved: map_party_dominance.html")

    fig.write_image('viz_party_map.png', scale=2)
    print("Saved: viz_party_map.png")

    return fig


def create_regional_heatmap(df):
    import matplotlib.pyplot as plt

    general = df[df['election_type'] == 'GENERAL'].copy()
    winners = general[general['won']]

    def get_region(const):
        const = str(const).lower()
        if 'dublin' in const:
            return 'Dublin'
        elif 'cork' in const:
            return 'Cork'
        elif 'galway' in const:
            return 'Galway'
        elif 'limerick' in const:
            return 'Limerick'
        elif any(x in const for x in ['kerry', 'clare', 'tipperary', 'waterford']):
            return 'Munster'
        elif any(x in const for x in ['mayo', 'sligo', 'roscommon', 'leitrim']):
            return 'Connacht'
        elif any(x in const for x in ['donegal', 'cavan', 'monaghan']):
            return 'Ulster'
        else:
            return 'Leinster'

    winners['region'] = winners['constituency_name'].apply(get_region)

    main_parties = ['Fianna Fáil', 'Fine Gael', 'Labour Party', 'Sinn Féin', 'Independent']
    region_party = winners[winners['party'].isin(main_parties)].groupby(
        ['region', 'party']
    ).size().unstack(fill_value=0)

    region_pct = region_party.div(region_party.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(12, 8))

    party_colors = {
        'Fianna Fáil': '#66BB66',
        'Fine Gael': '#6699FF',
        'Labour Party': '#CC0000',
        'Sinn Féin': '#326760',
        'Independent': '#AAAAAA',
    }

    cols = [c for c in main_parties if c in region_pct.columns]
    region_pct = region_pct[cols]

    im = ax.imshow(region_pct.values, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(np.arange(len(region_pct.columns)))
    ax.set_yticks(np.arange(len(region_pct.index)))
    ax.set_xticklabels(region_pct.columns, rotation=45, ha='right')
    ax.set_yticklabels(region_pct.index)

    for i in range(len(region_pct.index)):
        for j in range(len(region_pct.columns)):
            val = region_pct.values[i, j]
            color = 'white' if val > 30 else 'black'
            ax.text(j, i, f'{val:.0f}%', ha='center', va='center', color=color, fontsize=10)

    ax.set_title('Party Vote Share by Region (%)\nDáil Elections 1920-2020')
    plt.colorbar(im, ax=ax, label='Vote Share %')

    plt.tight_layout()
    plt.savefig('viz_regional_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_regional_heatmap.png")


def main():
    print("GEOGRAPHIC ANALYSIS")

    df = load_data()
    print(f"Loaded {len(df)} records")

    const_stats = create_constituency_summary(df)
    print(f"Analyzed {len(const_stats)} constituencies")

    const_stats.to_csv('constituency_stats.csv', index=False)
    print("Saved: constituency_stats.csv")

    try:
        create_party_map(df, const_stats)
    except Exception as e:
        print(f"Note: Could not create interactive map image (plotly kaleido may not be installed): {e}")
        print("HTML map was still created successfully.")

    create_regional_heatmap(df)

    print("\nMap files created!")


if __name__ == "__main__":
    main()
