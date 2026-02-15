import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from scipy import stats

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 12

PARTY_COLORS = {
    'Fianna Fáil': '#66BB66', 'Fine Gael': '#6699FF',
    'Labour': '#CC0000', 'Sinn Féin': '#326760',
    'Green Party': '#99CC33', 'Independent': '#AAAAAA',
}

PARTY_MAP = {
    'Labour Party': 'Labour', 'Labour': 'Labour',
    'Fianna Fáil': 'Fianna Fáil', 'Fianna Fail': 'Fianna Fáil',
    'Fine Gael': 'Fine Gael',
    'Sinn Féin': 'Sinn Féin', 'Sinn Fein': 'Sinn Féin',
    'Green Party': 'Green Party', 'Green/Comhaontas Glas': 'Green Party',
    'Independent': 'Independent', 'Non party/Independent': 'Independent',
    'Progressive Democrats': 'PDs',
    'Social Democrats': 'Social Democrats',
    'People Before Profit': 'PBP', 'People Before Profit Alliance': 'PBP',
    'Solidarity People Before Profit': 'PBP',
    'Solidarity - People Before Profit': 'PBP',
    'Workers\' Party': 'Workers\' Party', 'Workers Party': 'Workers\' Party',
}

# General elections with their preceding local/European elections
GENERAL_YEARS = [1992, 1997, 2002, 2007, 2011, 2016, 2020]
PAIRS = [
    ('LOCAL', 1991, 1992), ('LOCAL', 1999, 2002),
    ('LOCAL', 2004, 2007), ('EUROPEAN', 2004, 2007),
    ('LOCAL', 2009, 2011), ('EUROPEAN', 2009, 2011),
    ('LOCAL', 2014, 2016), ('EUROPEAN', 2014, 2016),
    ('LOCAL', 2019, 2020), ('EUROPEAN', 2019, 2020),
]


def load_data():
    df = pd.read_parquet('irelandelection/ALL_CANDIDATES.parquet')
    df['year'] = df['year'].astype(int)
    df['won'] = df['elected'].astype(bool)
    df['first_pref_count'] = pd.to_numeric(df['first_pref_count'], errors='coerce')
    df['party_clean'] = df['party'].map(lambda x: PARTY_MAP.get(x, x))
    return df


def get_vote_shares(df, election_type, year):
    sub = df[(df['election_type'] == election_type) & (df['year'] == year)]
    total = sub['first_pref_count'].sum()
    if total == 0 or pd.isna(total):
        return {}
    grouped = sub.groupby('party_clean')['first_pref_count'].sum()
    return (grouped / total * 100).to_dict()


# --- DELTA PREDICTOR ---

def delta_analysis(df):
    """Compare changes in vote share between elections, not absolute levels."""
    main_parties = ['Fianna Fáil', 'Fine Gael', 'Labour', 'Sinn Féin',
                    'Green Party', 'Independent']

    # Get general election vote shares for baseline
    gen_shares = {}
    for year in sorted(df[df['election_type'] == 'GENERAL']['year'].unique()):
        gen_shares[year] = get_vote_shares(df, 'GENERAL', year)

    delta_points = []
    for pred_type, pred_year, gen_year in PAIRS:
        pred_shares = get_vote_shares(df, pred_type, pred_year)
        next_gen = gen_shares.get(gen_year, {})

        # Find previous general election
        prev_years = [y for y in gen_shares if y < gen_year]
        if not prev_years:
            continue
        prev_gen_year = max(prev_years)
        prev_gen = gen_shares.get(prev_gen_year, {})

        for party in main_parties:
            prev_val = prev_gen.get(party, 0)
            pred_val = pred_shares.get(party, 0)
            next_val = next_gen.get(party, 0)

            if prev_val == 0 and pred_val == 0:
                continue

            # Delta: change from previous general to predictor election
            pred_delta = pred_val - prev_val
            # Delta: change from previous general to next general
            gen_delta = next_val - prev_val

            delta_points.append({
                'party': party,
                'pred_type': pred_type,
                'pred_year': pred_year,
                'gen_year': gen_year,
                'prev_gen_year': prev_gen_year,
                'pred_delta': round(pred_delta, 2),
                'gen_delta': round(gen_delta, 2),
            })

    return delta_points


def plot_delta_predictor(delta_points):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for i, etype in enumerate(['LOCAL', 'EUROPEAN']):
        ax = axes[i]
        pts = [p for p in delta_points if p['pred_type'] == etype]
        if not pts:
            continue

        x = [p['pred_delta'] for p in pts]
        y = [p['gen_delta'] for p in pts]
        parties = [p['party'] for p in pts]

        for px, py, party in zip(x, y, parties):
            c = PARTY_COLORS.get(party, '#888')
            ax.scatter(px, py, c=c, s=60, alpha=0.7, edgecolors='white', linewidths=0.5)

        if len(x) > 2:
            slope, intercept, r_value, _, _ = stats.linregress(x, y)
            x_range = np.linspace(min(x) - 2, max(x) + 2, 100)
            ax.plot(x_range, slope * x_range + intercept, 'k--', alpha=0.4)
            ax.text(0.05, 0.95, f'r = {r_value:.2f}\nr² = {r_value**2:.2f}',
                    transform=ax.transAxes, fontsize=10, va='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Zero lines
        ax.axhline(0, color='grey', alpha=0.3, linewidth=0.8)
        ax.axvline(0, color='grey', alpha=0.3, linewidth=0.8)

        ax.set_xlabel(f'Change in {etype.title()} Vote Share (pp)')
        ax.set_ylabel('Change in Next General Election (pp)')
        ax.set_title(f'{etype.title()} Election Deltas')

        from matplotlib.lines import Line2D
        handles = [Line2D([0], [0], marker='o', color='w',
                          markerfacecolor=c, markersize=8, label=p)
                   for p, c in PARTY_COLORS.items()
                   if p in set(parties)]
        ax.legend(handles=handles, fontsize=8, loc='lower right')

    plt.suptitle('Do Gains/Losses in Local Elections Predict Gains/Losses in the Dáil?', fontsize=13)
    plt.tight_layout()
    plt.savefig('viz_delta_predictor.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_delta_predictor.png")


# --- SAFEST SEATS / STRONGEST POLITICIANS ---

def safest_seats(df):
    """Find politicians who consistently exceeded quota across elections."""
    general = df[df['election_type'] == 'GENERAL'].copy()
    general['quota_ratio'] = pd.to_numeric(
        general.get('first_pref_quota_ratio', pd.Series(dtype=float)), errors='coerce')

    winners = general[general['won']].copy()

    # Group by candidate name — imperfect but workable for general patterns
    career = winners.groupby('candidate').agg(
        elections_won=('year', 'count'),
        years=('year', lambda x: sorted(x.tolist())),
        avg_quota=('quota_ratio', 'mean'),
        min_quota=('quota_ratio', 'min'),
        parties=('party_clean', lambda x: list(x.unique())),
        constituencies=('constituency', lambda x: list(x.unique())),
    ).reset_index()

    # Most elections won
    most_wins = career.nlargest(20, 'elections_won')

    # Highest average quota ratio (min 4 elections to filter noise)
    career_seasoned = career[career['elections_won'] >= 4]
    # Filter out data errors (quota > 3 is likely bad data)
    career_seasoned = career_seasoned[career_seasoned['avg_quota'] < 3]
    highest_quota = career_seasoned.nlargest(15, 'avg_quota')

    return most_wins, highest_quota


def plot_strongest_politicians(most_wins, highest_quota):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Most elections won
    top10 = most_wins.head(10)
    bars = ax1.barh(range(len(top10)), top10['elections_won'],
                    color='#2C3E50', alpha=0.8)
    ax1.set_yticks(range(len(top10)))
    ax1.set_yticklabels([f"{row['candidate']}" for _, row in top10.iterrows()],
                        fontsize=10)
    ax1.set_xlabel('Elections Won')
    ax1.set_title('Most General Elections Won')
    ax1.invert_yaxis()

    for j, (_, row) in enumerate(top10.iterrows()):
        years = row['years']
        ax1.text(row['elections_won'] + 0.1, j,
                f" {min(years)}–{max(years)}",
                va='center', fontsize=8, color='grey')

    # Highest quota dominance
    top10q = highest_quota.head(10)
    bars2 = ax2.barh(range(len(top10q)), top10q['avg_quota'] * 100,
                     color='#8E44AD', alpha=0.8)
    ax2.set_yticks(range(len(top10q)))
    ax2.set_yticklabels([f"{row['candidate']}" for _, row in top10q.iterrows()],
                        fontsize=10)
    ax2.set_xlabel('Avg First Pref as % of Quota')
    ax2.set_title('Highest Quota Dominance (min 4 elections)')
    ax2.invert_yaxis()
    ax2.axvline(100, color='grey', linestyle=':', alpha=0.5)
    ax2.text(101, -0.5, 'QUOTA', fontsize=8, color='grey')

    plt.suptitle('The Strongest Politicians in Irish Electoral History', fontsize=14)
    plt.tight_layout()
    plt.savefig('viz_strongest_politicians.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_strongest_politicians.png")


# --- MOST VOLATILE CONSTITUENCIES ---

def volatile_constituencies(df):
    """Track which constituencies changed their dominant party most often."""
    general = df[df['election_type'] == 'GENERAL'].copy()

    # For each constituency+year, find party with most seats won
    const_year = general[general['won']].groupby(
        ['constituency', 'year']
    )['party_clean'].agg(lambda x: x.value_counts().index[0]).reset_index()
    const_year.columns = ['constituency', 'year', 'dominant_party']
    const_year = const_year.sort_values(['constituency', 'year'])

    # Count party changes per constituency
    changes = []
    for const, group in const_year.groupby('constituency'):
        if len(group) < 3:
            continue
        parties = group['dominant_party'].tolist()
        years = group['year'].tolist()
        n_changes = sum(1 for i in range(1, len(parties)) if parties[i] != parties[i-1])
        n_elections = len(parties)

        change_years = []
        for i in range(1, len(parties)):
            if parties[i] != parties[i-1]:
                change_years.append({
                    'year': years[i],
                    'from': parties[i-1],
                    'to': parties[i]
                })

        changes.append({
            'constituency': const,
            'n_elections': n_elections,
            'n_changes': n_changes,
            'volatility': round(n_changes / (n_elections - 1) * 100, 1),
            'changes': change_years,
            'parties': list(set(parties)),
        })

    return sorted(changes, key=lambda x: x['volatility'], reverse=True)


def plot_volatile_constituencies(volatility_data):
    fig, ax = plt.subplots(figsize=(14, 8))

    # Top 15 most volatile (with at least 5 elections for stability)
    filtered = [v for v in volatility_data if v['n_elections'] >= 5]
    top15 = filtered[:15]

    names = [v['constituency'] for v in top15]
    vals = [v['volatility'] for v in top15]
    n_changes = [v['n_changes'] for v in top15]

    bars = ax.barh(range(len(top15)), vals, color='#E74C3C', alpha=0.8)
    ax.set_yticks(range(len(top15)))
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel('Volatility (% of elections with a party change)')
    ax.set_title('Most Volatile Constituencies\n(How often does the dominant party change?)')
    ax.invert_yaxis()

    for j, (v, nc) in enumerate(zip(vals, n_changes)):
        ax.text(v + 0.5, j, f'{nc} changes', va='center', fontsize=8, color='grey')

    # Bottom 15 — most stable
    bottom15 = filtered[-15:]
    bottom15.reverse()

    fig2, ax2 = plt.subplots(figsize=(14, 8))
    names2 = [v['constituency'] for v in bottom15]
    vals2 = [v['volatility'] for v in bottom15]

    bars2 = ax2.barh(range(len(bottom15)), vals2, color='#27AE60', alpha=0.8)
    ax2.set_yticks(range(len(bottom15)))
    ax2.set_yticklabels(names2, fontsize=10)
    ax2.set_xlabel('Volatility (% of elections with a party change)')
    ax2.set_title('Most Stable Constituencies\n(Lowest rate of dominant party change)')
    ax2.invert_yaxis()

    for j, v in enumerate(bottom15):
        parties = ', '.join(v['parties'])
        ax2.text(max(vals2) * 0.02, j, f"  {parties}", va='center', fontsize=8, color='grey')

    fig.tight_layout()
    fig.savefig('viz_volatile_constituencies.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved: viz_volatile_constituencies.png")

    fig2.tight_layout()
    fig2.savefig('viz_stable_constituencies.png', dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print("Saved: viz_stable_constituencies.png")


def main():
    print("Loading election data...")
    df = load_data()

    print("\nDelta analysis...")
    deltas = delta_analysis(df)
    print(f"  {len(deltas)} delta data points")
    plot_delta_predictor(deltas)

    # Check: do gains in locals predict gains in generals?
    local_deltas = [d for d in deltas if d['pred_type'] == 'LOCAL']
    if local_deltas:
        x = [d['pred_delta'] for d in local_deltas]
        y = [d['gen_delta'] for d in local_deltas]
        r = np.corrcoef(x, y)[0, 1]
        print(f"  Local delta correlation: r={r:.3f}, r²={r**2:.3f}")

        # How often does the direction match?
        same_dir = sum(1 for dx, dy in zip(x, y)
                       if (dx > 0 and dy > 0) or (dx < 0 and dy < 0) or (dx == 0))
        print(f"  Direction match: {same_dir}/{len(x)} ({same_dir/len(x)*100:.0f}%)")

    print("\nSafest seats analysis...")
    most_wins, highest_quota = safest_seats(df)
    print("  Top 5 most elections won:")
    for _, row in most_wins.head(5).iterrows():
        print(f"    {row['candidate']}: {row['elections_won']} wins "
              f"({min(row['years'])}–{max(row['years'])})")
    print("  Top 5 highest avg quota (min 4 elections):")
    for _, row in highest_quota.head(5).iterrows():
        print(f"    {row['candidate']}: {row['avg_quota']*100:.0f}% avg quota "
              f"over {row['elections_won']} elections")
    plot_strongest_politicians(most_wins, highest_quota)

    print("\nVolatile constituencies analysis...")
    volatility = volatile_constituencies(df)
    print("  Top 5 most volatile (min 5 elections):")
    for v in [x for x in volatility if x['n_elections'] >= 5][:5]:
        print(f"    {v['constituency']}: {v['volatility']}% volatility "
              f"({v['n_changes']} changes in {v['n_elections']} elections)")
    print("  Top 5 most stable:")
    stable = [x for x in volatility if x['n_elections'] >= 5]
    for v in stable[-5:]:
        print(f"    {v['constituency']}: {v['volatility']}% volatility, "
              f"parties: {', '.join(v['parties'])}")
    plot_volatile_constituencies(volatility)

    # Save results
    output = {
        'delta_analysis': deltas,
        'most_elections_won': [
            {'candidate': row['candidate'], 'wins': int(row['elections_won']),
             'years': [int(y) for y in row['years']],
             'parties': row['parties'],
             'constituencies': row['constituencies']}
            for _, row in most_wins.head(15).iterrows()
        ],
        'highest_quota_dominance': [
            {'candidate': row['candidate'], 'avg_quota_pct': round(row['avg_quota'] * 100, 1),
             'elections': int(row['elections_won']), 'parties': row['parties']}
            for _, row in highest_quota.head(15).iterrows()
        ],
        'volatile_constituencies': [
            {k: v for k, v in c.items()} for c in volatility[:20]
        ],
        'stable_constituencies': [
            {k: v for k, v in c.items()} for c in volatility[-10:]
        ],
    }

    with open('constituency_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\nSaved: constituency_analysis.json")


if __name__ == "__main__":
    main()
