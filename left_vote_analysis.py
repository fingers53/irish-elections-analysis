import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from scipy import stats

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 12

LEFT_PARTIES = {
    'Labour Party': 'Labour',
    'Labour': 'Labour',
    'Sinn Féin': 'Sinn Féin',
    'Sinn Fein': 'Sinn Féin',
    'Sinn Féin (Workers\' Party)': 'Workers\' Party',
    'Workers\' Party': 'Workers\' Party',
    'Workers Party': 'Workers\' Party',
    'Democratic Left': 'Democratic Left',
    'People Before Profit': 'PBP/Solidarity',
    'People Before Profit Alliance': 'PBP/Solidarity',
    'Solidarity People Before Profit': 'PBP/Solidarity',
    'Solidarity - People Before Profit': 'PBP/Solidarity',
    'Solidarity': 'PBP/Solidarity',
    'Social Democrats': 'Social Democrats',
    'Socialist Workers': 'Other Socialist',
    'Socialist': 'Other Socialist',
    'Socialist Party': 'Other Socialist',
    'Socialist Labour Party': 'Other Socialist',
    'Democratic Socialist': 'Other Socialist',
    'Independent Socialist': 'Other Socialist',
}

LEFT_COLORS = {
    'Labour': '#CC0000',
    'Sinn Féin': '#326760',
    'Workers\' Party': '#8B0000',
    'Democratic Left': '#B22222',
    'PBP/Solidarity': '#8B008B',
    'Social Democrats': '#752F8A',
    'Other Socialist': '#CD5C5C',
}

# General election years and which local/European elections preceded them
ELECTION_PAIRS = [
    ('LOCAL', 1991, 'GENERAL', 1992),
    ('LOCAL', 1999, 'GENERAL', 2002),
    ('EUROPEAN', 2004, 'GENERAL', 2007),
    ('LOCAL', 2004, 'GENERAL', 2007),
    ('EUROPEAN', 2009, 'GENERAL', 2011),
    ('LOCAL', 2009, 'GENERAL', 2011),
    ('EUROPEAN', 2014, 'GENERAL', 2016),
    ('LOCAL', 2014, 'GENERAL', 2016),
    ('EUROPEAN', 2019, 'GENERAL', 2020),
    ('LOCAL', 2019, 'GENERAL', 2020),
]


def load_all_elections():
    df = pd.read_parquet('irelandelection/ALL_CANDIDATES.parquet')
    df['year'] = df['year'].astype(int)
    df['won'] = df['elected'].astype(bool)
    df['first_pref_count'] = pd.to_numeric(df['first_pref_count'], errors='coerce')
    return df


def classify_left(party):
    return LEFT_PARTIES.get(party, None)


def left_vote_pool(df):
    """Compute left-wing vote share across general elections over time."""
    general = df[df['election_type'] == 'GENERAL'].copy()
    general['left_party'] = general['party'].map(classify_left)

    results = []
    for year in sorted(general['year'].unique()):
        year_df = general[general['year'] == year]
        total_votes = year_df['first_pref_count'].sum()
        if total_votes == 0 or pd.isna(total_votes):
            continue

        left_df = year_df[year_df['left_party'].notna()]
        row = {'year': int(year), 'total_votes': int(total_votes)}

        for lp in ['Labour', 'Sinn Féin', 'Workers\' Party', 'Democratic Left',
                    'PBP/Solidarity', 'Social Democrats', 'Other Socialist']:
            party_votes = left_df[left_df['left_party'] == lp]['first_pref_count'].sum()
            row[lp] = int(party_votes)

        row['left_total'] = sum(row[lp] for lp in LEFT_COLORS)
        row['left_pct'] = round(row['left_total'] / total_votes * 100, 1)
        results.append(row)

    return results


def party_vote_shares(df, election_type, year):
    """Compute first-preference vote share per party for a given election."""
    subset = df[(df['election_type'] == election_type) & (df['year'] == year)]
    total = subset['first_pref_count'].sum()
    if total == 0 or pd.isna(total):
        return {}

    shares = {}
    for party in ['Fianna Fáil', 'Fianna Fail', 'Fine Gael',
                   'Labour Party', 'Labour',
                   'Sinn Féin', 'Sinn Fein',
                   'Green Party', 'Green/Comhaontas Glas',
                   'Independent', 'Non party/Independent',
                   'Progressive Democrats', 'Social Democrats',
                   'People Before Profit', 'People Before Profit Alliance',
                   'Solidarity People Before Profit', 'Solidarity - People Before Profit',
                   'Workers\' Party', 'Workers Party']:
        votes = subset[subset['party'] == party]['first_pref_count'].sum()
        if votes > 0:
            shares[party] = votes

    # Merge variants
    merged = {}
    merged['Fianna Fáil'] = shares.get('Fianna Fáil', 0) + shares.get('Fianna Fail', 0)
    merged['Fine Gael'] = shares.get('Fine Gael', 0)
    merged['Labour'] = shares.get('Labour Party', 0) + shares.get('Labour', 0)
    merged['Sinn Féin'] = shares.get('Sinn Féin', 0) + shares.get('Sinn Fein', 0)
    merged['Green Party'] = shares.get('Green Party', 0) + shares.get('Green/Comhaontas Glas', 0)
    merged['Independent'] = shares.get('Independent', 0) + shares.get('Non party/Independent', 0)
    merged['PDs'] = shares.get('Progressive Democrats', 0)
    merged['Social Democrats'] = shares.get('Social Democrats', 0)
    merged['PBP'] = (shares.get('People Before Profit', 0) +
                     shares.get('People Before Profit Alliance', 0) +
                     shares.get('Solidarity People Before Profit', 0) +
                     shares.get('Solidarity - People Before Profit', 0))

    return {k: round(v / total * 100, 2) for k, v in merged.items() if v > 0}


def election_correlations(df):
    """Compare party vote shares between local/European and subsequent general elections."""
    results = []
    scatter_points = []

    for pred_type, pred_year, gen_type, gen_year in ELECTION_PAIRS:
        pred_shares = party_vote_shares(df, pred_type, pred_year)
        gen_shares = party_vote_shares(df, gen_type, gen_year)

        if not pred_shares or not gen_shares:
            continue

        common_parties = set(pred_shares.keys()) & set(gen_shares.keys())
        # Only include parties with meaningful vote share
        common_parties = {p for p in common_parties
                         if pred_shares[p] > 1.0 or gen_shares[p] > 1.0}

        pair_result = {
            'predictor': f"{pred_type} {pred_year}",
            'general': f"GENERAL {gen_year}",
            'parties': {}
        }

        for party in sorted(common_parties):
            pair_result['parties'][party] = {
                'predictor_share': pred_shares[party],
                'general_share': gen_shares[party],
                'diff': round(gen_shares[party] - pred_shares[party], 2)
            }
            scatter_points.append({
                'party': party,
                'predictor_type': pred_type,
                'pred_year': pred_year,
                'gen_year': gen_year,
                'pred_share': pred_shares[party],
                'gen_share': gen_shares[party],
            })

        results.append(pair_result)

    return results, scatter_points


def plot_left_vote_pool(pool_data):
    fig, ax = plt.subplots(figsize=(14, 7))

    years = [d['year'] for d in pool_data if d['year'] >= 1948]
    data = [d for d in pool_data if d['year'] >= 1948]

    plot_parties = ['Labour', 'Sinn Féin', 'Workers\' Party', 'Democratic Left',
                    'PBP/Solidarity', 'Social Democrats']

    bottoms = np.zeros(len(years))
    for party in plot_parties:
        values = []
        for d in data:
            total = d['total_votes']
            values.append(d.get(party, 0) / total * 100 if total else 0)
        values = np.array(values)

        if values.sum() > 0:
            ax.bar(years, values, bottom=bottoms, width=3,
                   color=LEFT_COLORS.get(party, '#888'), label=party, alpha=0.85)
            bottoms += values

    ax.set_xlabel('Election Year')
    ax.set_ylabel('% of Total First Preferences')
    ax.set_title('The Left Vote Pool: Where Do Left-Wing Votes Go?')
    ax.legend(loc='upper left', framealpha=0.9)
    ax.set_ylim(0, max(bottoms) * 1.15)

    # Annotate key events
    ax.annotate('Labour enters\ncoalition (2011)', xy=(2011, 25), xytext=(1998, 32),
                arrowprops=dict(arrowstyle='->', color='grey'),
                fontsize=9, color='grey')
    ax.annotate('SF surge\n(2020)', xy=(2020, 30), xytext=(2015, 38),
                arrowprops=dict(arrowstyle='->', color='grey'),
                fontsize=9, color='grey')

    plt.tight_layout()
    plt.savefig('viz_left_vote_pool.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_left_vote_pool.png")


def plot_labour_sf_mirror(pool_data):
    fig, ax = plt.subplots(figsize=(12, 6))

    data = [d for d in pool_data if d['year'] >= 1987]
    years = [d['year'] for d in data]
    labour_pct = [d['Labour'] / d['total_votes'] * 100 for d in data]
    sf_pct = [d['Sinn Féin'] / d['total_votes'] * 100 for d in data]

    ax.plot(years, labour_pct, marker='o', linewidth=2.5, color='#CC0000',
            markersize=8, label='Labour')
    ax.plot(years, sf_pct, marker='s', linewidth=2.5, color='#326760',
            markersize=8, label='Sinn Féin')

    ax.fill_between(years, labour_pct, alpha=0.15, color='#CC0000')
    ax.fill_between(years, sf_pct, alpha=0.15, color='#326760')

    # Highlight the crossover
    ax.axvline(2011, color='grey', linestyle=':', alpha=0.6)
    ax.text(2011.3, ax.get_ylim()[1] * 0.85, 'FG-Labour\ncoalition',
            fontsize=9, color='grey', va='top')

    ax.set_xlabel('Election Year')
    ax.set_ylabel('% of Total First Preferences')
    ax.set_title('Labour and Sinn Féin: The Left-Wing Vote Transfer')
    ax.legend(framealpha=0.9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('viz_labour_sf_mirror.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_labour_sf_mirror.png")


def plot_election_predictor(scatter_points):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for i, etype in enumerate(['LOCAL', 'EUROPEAN']):
        ax = axes[i]
        pts = [p for p in scatter_points if p['predictor_type'] == etype]

        if not pts:
            ax.set_title(f'{etype.title()} Elections: No data')
            continue

        x = [p['pred_share'] for p in pts]
        y = [p['gen_share'] for p in pts]
        parties = [p['party'] for p in pts]

        party_colors = {
            'Fianna Fáil': '#66BB66', 'Fine Gael': '#6699FF',
            'Labour': '#CC0000', 'Sinn Féin': '#326760',
            'Green Party': '#99CC33', 'Independent': '#AAAAAA',
        }

        for px, py, party in zip(x, y, parties):
            c = party_colors.get(party, '#888888')
            ax.scatter(px, py, c=c, s=60, alpha=0.7, edgecolors='white', linewidths=0.5)

        # Line of best fit
        if len(x) > 2:
            slope, intercept, r_value, _, _ = stats.linregress(x, y)
            x_line = np.linspace(0, max(x) * 1.1, 100)
            ax.plot(x_line, slope * x_line + intercept, 'k--', alpha=0.4, linewidth=1)
            ax.text(0.05, 0.95, f'r = {r_value:.2f}\nr² = {r_value**2:.2f}',
                    transform=ax.transAxes, fontsize=10, va='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Perfect prediction line
        lim = max(max(x, default=0), max(y, default=0)) * 1.1
        ax.plot([0, lim], [0, lim], 'grey', alpha=0.3, linestyle='-')

        ax.set_xlabel(f'{etype.title()} Election Vote Share (%)')
        ax.set_ylabel('Next General Election Vote Share (%)')
        ax.set_title(f'{etype.title()} Elections as Predictor')
        ax.set_xlim(0, lim)
        ax.set_ylim(0, lim)

        # Legend for parties
        from matplotlib.lines import Line2D
        handles = [Line2D([0], [0], marker='o', color='w',
                          markerfacecolor=c, markersize=8, label=p)
                   for p, c in party_colors.items()
                   if p in set(parties)]
        ax.legend(handles=handles, fontsize=8, loc='lower right')

    plt.suptitle('Do Local and European Elections Predict Dáil Results?', fontsize=13)
    plt.tight_layout()
    plt.savefig('viz_election_predictor.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_election_predictor.png")


def main():
    print("Loading all election data...")
    df = load_all_elections()
    print(f"  {len(df):,} records across {df['election_type'].nunique()} election types")

    print("\nAnalyzing left vote pool...")
    pool = left_vote_pool(df)
    print(f"  {len(pool)} general elections analyzed")

    print("\nComputing election correlations...")
    corr_results, scatter = election_correlations(df)
    print(f"  {len(corr_results)} election pairs analyzed")
    print(f"  {len(scatter)} party-level data points")

    # Save analysis results
    output = {
        'left_vote_pool': pool,
        'election_correlations': corr_results,
        'labour_sf_summary': {
            year_data['year']: {
                'labour_pct': round(year_data['Labour'] / year_data['total_votes'] * 100, 1),
                'sf_pct': round(year_data['Sinn Féin'] / year_data['total_votes'] * 100, 1),
                'left_total_pct': year_data['left_pct'],
            }
            for year_data in pool
            if year_data['year'] >= 1987
        }
    }

    with open('left_vote_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\nSaved: left_vote_analysis.json")

    # Generate visualizations
    plot_left_vote_pool(pool)
    plot_labour_sf_mirror(pool)
    plot_election_predictor(scatter)

    # Print highlights
    print("\nLEFT VOTE POOL HIGHLIGHTS:")
    for d in pool:
        if d['year'] >= 2002:
            lab = d['Labour'] / d['total_votes'] * 100
            sf = d['Sinn Féin'] / d['total_votes'] * 100
            print(f"  {d['year']}: Labour {lab:.1f}%, SF {sf:.1f}%, Left total {d['left_pct']}%")

    print("\nELECTION PREDICTION HIGHLIGHTS:")
    for pair in corr_results:
        print(f"\n  {pair['predictor']} -> {pair['general']}:")
        for party, data in sorted(pair['parties'].items()):
            diff = data['diff']
            arrow = '+' if diff > 0 else ''
            print(f"    {party}: {data['predictor_share']:.1f}% -> {data['general_share']:.1f}% ({arrow}{diff:.1f})")


if __name__ == "__main__":
    main()
