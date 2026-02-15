import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 12

PARTY_COLORS = {
    'Fianna Fáil': '#66BB66',
    'Fine Gael': '#6699FF',
    'Labour': '#CC0000',
    'Sinn Féin': '#326760',
    'Green Party': '#99CC33',
    'Independent': '#AAAAAA',
    'Cumann na nGaedheal': '#4169E1',
    'Progressive Democrats': '#0000CD',
    'Workers\' Party': '#8B0000',
}


def load_data():
    with open('factoids.json', 'r', encoding='utf-8') as f:
        factoids = json.load(f)
    with open('visualization_data.json', 'r', encoding='utf-8') as f:
        viz_data = json.load(f)
    return factoids, viz_data


def plot_quota_distribution(factoids, viz_data):
    fig, ax = plt.subplots(figsize=(12, 6))

    winners = np.array(viz_data['quota_histogram']['winners'])
    losers = np.array(viz_data['quota_histogram']['losers'])

    # Filter to reasonable range
    winners = winners[(winners > 0) & (winners < 2.5)]
    losers = losers[(losers > 0) & (losers < 2.5)]

    bins = np.arange(0, 2.55, 0.1)

    ax.hist(losers, bins=bins, alpha=0.6, label='Lost', color='#E74C3C', edgecolor='white')
    ax.hist(winners, bins=bins, alpha=0.6, label='Won', color='#27AE60', edgecolor='white')

    ax.axvline(factoids['quota_analysis']['winners_median'], color='#1D8348',
               linestyle='--', linewidth=2, label=f"Winner median ({factoids['quota_analysis']['winners_median']:.0%})")
    ax.axvline(factoids['quota_analysis']['losers_median'], color='#922B21',
               linestyle='--', linewidth=2, label=f"Loser median ({factoids['quota_analysis']['losers_median']:.0%})")

    ax.axvline(1.0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax.text(1.02, ax.get_ylim()[1]*0.9, 'QUOTA', fontsize=10, rotation=90)

    ax.set_xlabel('First Preference Votes as Fraction of Quota')
    ax.set_ylabel('Number of Candidates')
    ax.set_title('What Does It Take to Win? First Preference Performance in Irish Elections')
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('viz_quota_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_quota_distribution.png")


def plot_party_seats_over_time(factoids):
    fig, ax = plt.subplots(figsize=(14, 7))

    party_trends = pd.DataFrame(factoids['party_trends'])
    main_parties = ['Fianna Fáil', 'Fine Gael', 'Labour', 'Sinn Féin', 'Independent']

    pivot = party_trends[party_trends['party'].isin(main_parties)].pivot(
        index='decade', columns='party', values='wins'
    ).fillna(0)

    pivot = pivot[[p for p in main_parties if p in pivot.columns]]

    colors = [PARTY_COLORS.get(p, '#888888') for p in pivot.columns]

    pivot.plot(kind='area', stacked=True, ax=ax, color=colors, alpha=0.8)

    ax.set_xlabel('Decade')
    ax.set_ylabel('Seats Won')
    ax.set_title('Irish Dáil Seats by Major Party (1920s-2020s)')
    ax.legend(title='Party', loc='upper left', bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig('viz_party_seats_time.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_party_seats_time.png")


def plot_party_win_rates(factoids):
    fig, ax = plt.subplots(figsize=(14, 7))

    party_trends = pd.DataFrame(factoids['party_trends'])

    main_parties = ['Fianna Fáil', 'Fine Gael', 'Labour', 'Sinn Féin']

    for party in main_parties:
        party_data = party_trends[party_trends['party'] == party]
        ax.plot(party_data['decade'], party_data['win_rate'],
                marker='o', linewidth=2, markersize=8,
                color=PARTY_COLORS.get(party, '#888888'), label=party)

    ax.set_xlabel('Decade')
    ax.set_ylabel('Win Rate (%)')
    ax.set_title('Party Efficiency: Win Rate Over Time\n(What % of candidates who run actually win)')
    ax.legend(title='Party')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('viz_party_win_rates.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_party_win_rates.png")


def plot_independent_resurgence(factoids):
    fig, ax = plt.subplots(figsize=(12, 6))

    ind_data = factoids['independent_trends']
    decades = sorted([int(d) for d in ind_data['wins'].keys()])
    wins = [ind_data['wins'][str(d)] for d in decades]
    win_rate = [ind_data['win_rate'][str(d)] for d in decades]

    ax2 = ax.twinx()

    bars = ax.bar(decades, wins, width=7, alpha=0.6, color='#7D3C98', label='Seats Won')
    line = ax2.plot(decades, win_rate, marker='o', color='#E74C3C', linewidth=2,
                    markersize=10, label='Win Rate %')

    ax.set_xlabel('Decade')
    ax.set_ylabel('Seats Won', color='#7D3C98')
    ax2.set_ylabel('Win Rate (%)', color='#E74C3C')
    ax.set_title('The Independent Vote: From Civil War to Modern Politics')

    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('viz_independent_trends.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_independent_trends.png")


def plot_sinn_fein_rise(factoids):
    fig, ax = plt.subplots(figsize=(12, 6))

    party_trends = pd.DataFrame(factoids['party_trends'])
    sf_data = party_trends[party_trends['party'] == 'Sinn Féin'].copy()

    decades = sf_data['decade'].values
    wins = sf_data['wins'].values
    win_rates = sf_data['win_rate'].values

    ax2 = ax.twinx()

    bars = ax.bar(decades, wins, width=7, alpha=0.6, color='#326760', label='Seats Won')
    line = ax2.plot(decades, win_rates, marker='o', color='#E74C3C', linewidth=2,
                    markersize=10, label='Win Rate %')

    if 2020 in decades:
        idx_2020 = list(decades).index(2020)
        ax.annotate(f'88% win rate!\n37 seats', xy=(2020, wins[idx_2020]),
                   xytext=(1990, wins[idx_2020]+10),
                   arrowprops=dict(arrowstyle='->', color='black'),
                   fontsize=12, fontweight='bold')

    ax.set_xlabel('Decade')
    ax.set_ylabel('Seats Won', color='#326760')
    ax2.set_ylabel('Win Rate (%)', color='#E74C3C')
    ax.set_title('The Rise of Sinn Féin: From 0% in the 1960s to 88% Win Rate in 2020')

    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('viz_sinn_fein_rise.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_sinn_fein_rise.png")


def plot_regional_dominance(factoids):
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.flatten()

    regions = factoids['regional_dominance']

    for i, (region, parties) in enumerate(regions.items()):
        if i >= 8:
            break

        ax = axes[i]
        party_names = list(parties.keys())
        seat_counts = list(parties.values())
        colors = [PARTY_COLORS.get(p, '#888888') for p in party_names]

        ax.barh(party_names, seat_counts, color=colors)
        ax.set_title(region, fontsize=12, fontweight='bold')
        ax.set_xlabel('Seats Won')

    plt.suptitle('Regional Party Dominance in Irish Elections', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('viz_regional_dominance.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_regional_dominance.png")


def plot_competitiveness_trend(factoids):
    fig, ax = plt.subplots(figsize=(12, 6))

    yearly = factoids['yearly_stats']
    years = sorted([int(y) for y in yearly['candidates_per_seat'].keys()])
    cps = [yearly['candidates_per_seat'][str(y)] for y in years if yearly['candidates_per_seat'][str(y)] != float('inf')]
    years = [y for y in years if yearly['candidates_per_seat'][str(y)] != float('inf')]

    ax.plot(years, cps, marker='o', linewidth=2, color='#3498DB', markersize=6)
    ax.fill_between(years, cps, alpha=0.3, color='#3498DB')

    ax.set_xlabel('Election Year')
    ax.set_ylabel('Candidates Per Seat')
    ax.set_title('How Competitive Are Irish Elections?\nMore Candidates Fighting for Each Seat')

    ax.annotate('More crowded\nballots', xy=(2016, max(cps)),
               xytext=(2000, max(cps)-0.3),
               arrowprops=dict(arrowstyle='->', color='black'),
               fontsize=11)

    plt.tight_layout()
    plt.savefig('viz_competitiveness_trend.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_competitiveness_trend.png")


def create_all_visualizations():
    print("Creating visualizations...")
    factoids, viz_data = load_data()

    plot_quota_distribution(factoids, viz_data)
    plot_party_seats_over_time(factoids)
    plot_party_win_rates(factoids)
    plot_independent_resurgence(factoids)
    plot_sinn_fein_rise(factoids)
    plot_regional_dominance(factoids)
    plot_competitiveness_trend(factoids)

    print("\nAll visualizations created!")


if __name__ == "__main__":
    create_all_visualizations()
