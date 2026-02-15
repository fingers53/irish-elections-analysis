import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

plt.style.use('seaborn-v0_8-whitegrid')


def load_gender_data():
    df = pd.read_parquet('electionsireland_data/DAIL_elections_master.parquet')
    df['year'] = pd.to_datetime(df['election_date']).dt.year
    df['elected'] = df['status'].isin(['Made Quota', 'Elected', 'Without reaching quota'])

    return df


def analyze_gender(df):
    stats = {}

    stats['total'] = {
        'male_candidates': int((df['gender'] == 'Male').sum()),
        'female_candidates': int((df['gender'] == 'Female').sum()),
        'female_pct': round((df['gender'] == 'Female').mean() * 100, 1)
    }

    winners = df[df['elected']]
    stats['winners'] = {
        'male': int((winners['gender'] == 'Male').sum()),
        'female': int((winners['gender'] == 'Female').sum()),
        'female_pct': round((winners['gender'] == 'Female').mean() * 100, 1) if len(winners) > 0 else 0
    }

    yearly = df.groupby('year').agg({
        'gender': [
            lambda x: (x == 'Female').sum(),
            lambda x: (x == 'Male').sum(),
            lambda x: (x == 'Female').mean() * 100
        ]
    }).round(1)
    yearly.columns = ['female_candidates', 'male_candidates', 'female_pct']
    stats['by_year'] = yearly.to_dict()

    winners_yearly = winners.groupby('year').agg({
        'gender': [
            lambda x: (x == 'Female').sum(),
            lambda x: (x == 'Male').sum(),
            lambda x: (x == 'Female').mean() * 100 if len(x) > 0 else 0
        ]
    }).round(1)
    winners_yearly.columns = ['female_elected', 'male_elected', 'female_elected_pct']
    stats['winners_by_year'] = winners_yearly.to_dict()

    male_df = df[df['gender'] == 'Male']
    female_df = df[df['gender'] == 'Female']

    stats['win_rates'] = {
        'male': round(male_df['elected'].mean() * 100, 1),
        'female': round(female_df['elected'].mean() * 100, 1)
    }

    # Only parties with >= 10 female candidates
    party_gender = df.groupby(['party', 'gender']).agg({
        'elected': ['count', 'sum']
    }).reset_index()
    party_gender.columns = ['party', 'gender', 'candidates', 'elected']

    female_by_party = party_gender[party_gender['gender'] == 'Female']
    female_by_party = female_by_party[female_by_party['candidates'] >= 10]
    female_by_party['win_rate'] = (female_by_party['elected'] / female_by_party['candidates'] * 100).round(1)
    stats['female_by_party'] = female_by_party.sort_values('candidates', ascending=False).head(10).to_dict('records')

    first_women = winners[winners['gender'] == 'Female'].sort_values('year').head(10)
    stats['pioneering_women'] = first_women[['candidate', 'year', 'party', 'constituency_name']].to_dict('records')

    female_winners = winners[winners['gender'] == 'Female']
    top_women = female_winners.groupby('candidate').agg({
        'year': ['min', 'max', 'count'],
        'party': 'first',
        'constituency_name': 'first'
    }).reset_index()
    top_women.columns = ['candidate', 'first_elected', 'last_elected', 'times_elected', 'party', 'constituency']
    top_women = top_women.sort_values('times_elected', ascending=False).head(15)
    stats['most_elected_women'] = top_women.to_dict('records')

    return stats


def plot_gender_timeline(df, stats):
    fig, ax = plt.subplots(figsize=(14, 6))

    years = sorted(stats['by_year']['female_pct'].keys())
    candidates_pct = [stats['by_year']['female_pct'][y] for y in years]

    winners_years = sorted(stats['winners_by_year']['female_elected_pct'].keys())
    winners_pct = [stats['winners_by_year']['female_elected_pct'].get(y, 0) for y in years]

    ax.fill_between(years, candidates_pct, alpha=0.3, color='#9B59B6', label='Female Candidates %')
    ax.plot(years, candidates_pct, marker='o', color='#9B59B6', linewidth=2, markersize=6)

    ax.fill_between(years, winners_pct, alpha=0.3, color='#E74C3C', label='Female TDs Elected %')
    ax.plot(years, winners_pct, marker='s', color='#E74C3C', linewidth=2, markersize=6)

    milestones = [
        (1918, "Constance Markievicz\nfirst woman elected", 5),
        (1992, "Mary Robinson\nPresident", 15),
        (2016, "Gender quotas\nintroduced", 25),
    ]

    for year, label, y_pos in milestones:
        if year in years:
            ax.annotate(label, xy=(year, y_pos), fontsize=9,
                       ha='center', style='italic')
            ax.axvline(year, color='gray', linestyle=':', alpha=0.5)

    ax.set_xlabel('Election Year')
    ax.set_ylabel('Percentage Female (%)')
    ax.set_title('Women in Irish Politics: A Century of Progress\n(Dáil General Elections 1922-2020)')
    ax.legend(loc='upper left')
    ax.set_ylim(0, 35)

    plt.tight_layout()
    plt.savefig('viz_gender_timeline.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_gender_timeline.png")


def plot_gender_by_party(stats):
    fig, ax = plt.subplots(figsize=(12, 6))

    party_data = stats['female_by_party']
    parties = [d['party'][:20] for d in party_data]  # Truncate long names
    candidates = [d['candidates'] for d in party_data]
    elected = [d['elected'] for d in party_data]

    x = np.arange(len(parties))
    width = 0.35

    bars1 = ax.bar(x - width/2, candidates, width, label='Candidates', color='#9B59B6', alpha=0.7)
    bars2 = ax.bar(x + width/2, elected, width, label='Elected', color='#27AE60', alpha=0.7)

    ax.set_xlabel('Party')
    ax.set_ylabel('Number of Women')
    ax.set_title('Female Candidates and TDs by Party')
    ax.set_xticks(x)
    ax.set_xticklabels(parties, rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()
    plt.savefig('viz_gender_by_party.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_gender_by_party.png")


def plot_win_rate_comparison(stats):
    fig, ax = plt.subplots(figsize=(8, 5))

    genders = ['Male', 'Female']
    win_rates = [stats['win_rates']['male'], stats['win_rates']['female']]
    colors = ['#3498DB', '#E91E63']

    bars = ax.bar(genders, win_rates, color=colors, width=0.5)

    for bar, rate in zip(bars, win_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{rate}%', ha='center', fontsize=14, fontweight='bold')

    ax.set_ylabel('Win Rate (%)')
    ax.set_title('Election Win Rate by Gender\n(% of candidates who win)')
    ax.set_ylim(0, max(win_rates) * 1.2)

    plt.tight_layout()
    plt.savefig('viz_gender_win_rate.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: viz_gender_win_rate.png")


def main():
    df = load_gender_data()
    print(f"Loaded {len(df)} records with gender data")

    stats = analyze_gender(df)

    with open('gender_stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
    print("Saved: gender_stats.json")

    plot_gender_timeline(df, stats)
    plot_gender_by_party(stats)
    plot_win_rate_comparison(stats)

    print(f"\nOverall representation:")
    print(f"  Female candidates: {stats['total']['female_candidates']} ({stats['total']['female_pct']}%)")
    print(f"  Female TDs elected: {stats['winners']['female']} ({stats['winners']['female_pct']}%)")

    print(f"\nWin rates:")
    print(f"  Male candidates: {stats['win_rates']['male']}%")
    print(f"  Female candidates: {stats['win_rates']['female']}%")

    print(f"\nPioneering women (first female TDs):")
    for w in stats['pioneering_women'][:5]:
        print(f"  - {w['candidate']} ({w['year']}, {w['party']})")

    print(f"\nMost elected women:")
    for w in stats['most_elected_women'][:5]:
        print(f"  - {w['candidate']}: {w['times_elected']} times ({w['first_elected']}-{w['last_elected']})")

    return stats


if __name__ == "__main__":
    stats = main()
