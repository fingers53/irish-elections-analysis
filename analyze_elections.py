import pandas as pd
import numpy as np
import json
from pathlib import Path


def load_data():
    print("Loading election data...")

    df = pd.read_parquet('irelandelection/ALL_CANDIDATES.parquet')

    df = df.rename(columns={
        'first_pref_quota_ratio': 'quota_ratio',
        'constituency': 'constituency_name'
    })

    df['year'] = df['year'].astype(int)
    df['decade'] = (df['year'] // 10 * 10).astype(int)
    df['won'] = df['elected'].astype(bool)

    party_map = {
        'Labour Party': 'Labour',
        'Fianna Fáil': 'Fianna Fáil',
        'Fianna Fail': 'Fianna Fáil',
        'Fine Gael': 'Fine Gael',
        'Sinn Féin': 'Sinn Féin',
        'Sinn Fein': 'Sinn Féin',
        'Green Party': 'Green Party',
        'Independent': 'Independent',
        'Progressive Democrats': 'Progressive Democrats',
        'Workers\' Party': 'Workers\' Party',
        'Democratic Left': 'Democratic Left',
        'People Before Profit': 'People Before Profit',
        'Solidarity - People Before Profit': 'Solidarity-PBP',
        'Social Democrats': 'Social Democrats',
    }
    df['party_clean'] = df['party'].map(lambda x: party_map.get(x, x))

    print(f"  Loaded {len(df):,} candidate records")
    print(f"  Years: {df['year'].min()} - {df['year'].max()}")
    print(f"  Election types: {df['election_type'].unique().tolist()}")

    return df


def extract_factoids(df):
    factoids = {}

    general = df[df['election_type'] == 'GENERAL'].copy()

    winners = general[general['won']]['quota_ratio'].dropna()
    losers = general[~general['won']]['quota_ratio'].dropna()

    factoids['quota_analysis'] = {
        'winners_mean': round(winners.mean(), 3),
        'winners_median': round(winners.median(), 3),
        'winners_std': round(winners.std(), 3),
        'losers_mean': round(losers.mean(), 3),
        'losers_median': round(losers.median(), 3),
        'losers_std': round(losers.std(), 3),
        'gap': round(winners.mean() - losers.mean(), 3),
    }

    # Candidates who exceeded quota but still lost
    anomalies = general[~general['won'] & (general['quota_ratio'] > 1.0)].copy()
    anomalies = anomalies.sort_values('quota_ratio', ascending=False)
    factoids['exceeded_quota_but_lost'] = {
        'count': len(anomalies),
        'cases': anomalies[['year', 'candidate', 'constituency_name', 'party', 'quota_ratio']].head(10).to_dict('records')
    }

    party_by_decade = general.groupby(['decade', 'party_clean']).agg({
        'won': ['sum', 'count']
    }).reset_index()
    party_by_decade.columns = ['decade', 'party', 'wins', 'candidates']
    party_by_decade['win_rate'] = (party_by_decade['wins'] / party_by_decade['candidates'] * 100).round(1)

    top_parties = general.groupby('party_clean')['won'].sum().nlargest(7).index.tolist()
    party_trends = party_by_decade[party_by_decade['party'].isin(top_parties)]
    factoids['party_trends'] = party_trends.to_dict('records')

    party_overall = general.groupby('party_clean').agg({
        'won': ['sum', 'count'],
        'quota_ratio': ['mean', 'median']
    }).round(3)
    party_overall.columns = ['wins', 'candidates', 'avg_quota', 'median_quota']
    party_overall['win_rate'] = (party_overall['wins'] / party_overall['candidates'] * 100).round(1)
    party_overall = party_overall.sort_values('wins', ascending=False)
    factoids['party_overall'] = party_overall.head(15).to_dict()

    const_stats = general[general['won']].groupby('constituency_name').agg({
        'quota_ratio': ['mean', 'std', 'count']
    }).round(3)
    const_stats.columns = ['avg_winner_quota', 'std_winner_quota', 'elections']
    const_stats = const_stats[const_stats['elections'] >= 5]

    most_competitive = const_stats.nsmallest(10, 'avg_winner_quota')
    factoids['most_competitive_constituencies'] = most_competitive.to_dict()

    safest = const_stats.nlargest(10, 'avg_winner_quota')
    factoids['safest_constituencies'] = safest.to_dict()

    yearly_stats = general.groupby('year').agg({
        'candidate': 'count',
        'won': 'sum',
        'constituency_name': 'nunique'
    })
    yearly_stats.columns = ['total_candidates', 'seats_filled', 'constituencies']
    yearly_stats['candidates_per_seat'] = (yearly_stats['total_candidates'] / yearly_stats['seats_filled']).round(2)
    factoids['yearly_stats'] = yearly_stats.to_dict()

    independents = general[general['party_clean'] == 'Independent']
    ind_by_decade = independents.groupby('decade').agg({
        'won': ['sum', 'count']
    })
    ind_by_decade.columns = ['wins', 'candidates']
    ind_by_decade['win_rate'] = (ind_by_decade['wins'] / ind_by_decade['candidates'] * 100).round(1)
    factoids['independent_trends'] = ind_by_decade.to_dict()

    close_winners = general[general['won']].nsmallest(20, 'quota_ratio')
    factoids['closest_wins'] = close_winners[['year', 'candidate', 'constituency_name', 'party', 'quota_ratio']].to_dict('records')

    landslides = general[general['won']].nlargest(20, 'quota_ratio')
    factoids['biggest_landslides'] = landslides[['year', 'candidate', 'constituency_name', 'party', 'quota_ratio', 'first_pref_pct']].to_dict('records')

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
        elif any(x in const for x in ['kerry', 'clare', 'tipperary']):
            return 'Munster (other)'
        elif any(x in const for x in ['mayo', 'sligo', 'roscommon', 'leitrim']):
            return 'Connacht'
        elif any(x in const for x in ['donegal', 'cavan', 'monaghan']):
            return 'Ulster (ROI)'
        else:
            return 'Leinster (other)'

    general['region'] = general['constituency_name'].apply(get_region)
    region_party = general[general['won']].groupby(['region', 'party_clean']).size().unstack(fill_value=0)

    regional_dominance = {}
    for region in region_party.index:
        top = region_party.loc[region].nlargest(3)
        regional_dominance[region] = {p: int(v) for p, v in top.items()}
    factoids['regional_dominance'] = regional_dominance

    return factoids


def prepare_visualization_data(df):
    viz_data = {}

    general = df[df['election_type'] == 'GENERAL'].copy()

    winners = general[general['won']]['quota_ratio'].dropna()
    losers = general[~general['won']]['quota_ratio'].dropna()

    viz_data['quota_histogram'] = {
        'winners': winners.tolist(),
        'losers': losers.tolist(),
        'bins': list(np.arange(0, 3.1, 0.1))
    }

    top_parties = ['Fianna Fáil', 'Fine Gael', 'Labour', 'Sinn Féin', 'Green Party', 'Independent']
    party_time = general.groupby(['year', 'party_clean']).agg({
        'first_pref_pct': 'sum',
        'won': 'sum'
    }).reset_index()
    party_time = party_time[party_time['party_clean'].isin(top_parties)]
    viz_data['party_over_time'] = party_time.to_dict('records')

    seats_by_party = general[general['won']].groupby(['year', 'party_clean']).size().unstack(fill_value=0)
    viz_data['seats_by_party'] = {
        'years': seats_by_party.index.tolist(),
        'parties': {col: seats_by_party[col].tolist() for col in seats_by_party.columns if col in top_parties}
    }

    comp_over_time = general[general['won']].groupby('year')['quota_ratio'].mean()
    viz_data['competitiveness_trend'] = {
        'years': comp_over_time.index.tolist(),
        'avg_winner_quota': comp_over_time.tolist()
    }

    return viz_data


def main():
    print("=" * 60)
    print("IRISH ELECTIONS ANALYSIS")
    print("=" * 60)

    df = load_data()

    print("\nExtracting factoids...")
    factoids = extract_factoids(df)

    with open('factoids.json', 'w', encoding='utf-8') as f:
        json.dump(factoids, f, indent=2, ensure_ascii=False, default=str)
    print("  Saved: factoids.json")

    print("\nPreparing visualization data...")
    viz_data = prepare_visualization_data(df)

    with open('visualization_data.json', 'w', encoding='utf-8') as f:
        json.dump(viz_data, f, indent=2, ensure_ascii=False, default=str)
    print("  Saved: visualization_data.json")

    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    qa = factoids['quota_analysis']
    print(f"\nQUOTA ANALYSIS:")
    print(f"   Winners need ~{qa['winners_median']:.0%} of quota on first count")
    print(f"   Losers average only {qa['losers_median']:.0%} of quota")
    print(f"   The gap: {qa['gap']:.0%}")

    print(f"\nANOMALIES:")
    print(f"   {factoids['exceeded_quota_but_lost']['count']} candidates exceeded quota but still lost!")
    for case in factoids['exceeded_quota_but_lost']['cases'][:3]:
        print(f"   - {case['candidate']} ({case['year']}, {case['constituency_name']}): {case['quota_ratio']:.2f}x quota")

    print(f"\nTOP PARTIES (total Dail seats won):")
    for i, (party, wins) in enumerate(list(factoids['party_overall']['wins'].items())[:5]):
        print(f"   {i+1}. {party}: {wins} seats")

    print(f"\nMOST COMPETITIVE CONSTITUENCIES:")
    for const, avg in list(factoids['most_competitive_constituencies']['avg_winner_quota'].items())[:5]:
        print(f"   - {const}: winners avg {avg:.0%} quota")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return df, factoids, viz_data


if __name__ == "__main__":
    df, factoids, viz_data = main()
