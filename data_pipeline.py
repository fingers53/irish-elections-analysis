import pandas as pd
import numpy as np
import jellyfish
import json
from pathlib import Path

# Variant names -> canonical names (based on current Dáil constituencies)
CONSTITUENCY_MAPPING = {
    "Carlow Kilkenny": "Carlow–Kilkenny",
    "Carlow-Kilkenny": "Carlow–Kilkenny",
    "Carlow–Kilkenny": "Carlow–Kilkenny",

    "Cavan Monaghan": "Cavan–Monaghan",
    "Cavan-Monaghan": "Cavan–Monaghan",
    "Cavan–Monaghan": "Cavan–Monaghan",

    "Cork South Central": "Cork South-Central",
    "Cork South–Central": "Cork South-Central",
    "Cork North Central": "Cork North-Central",
    "Cork North–Central": "Cork North-Central",
    "Cork South West": "Cork South-West",
    "Cork South–West": "Cork South-West",
    "Cork North West": "Cork North-West",
    "Cork North–West": "Cork North-West",

    "Dublin Mid West": "Dublin Mid-West",
    "Dublin Mid–West": "Dublin Mid-West",
    "Dublin North West": "Dublin North-West",
    "Dublin North–West": "Dublin North-West",
    "Dublin South West": "Dublin South-West",
    "Dublin South–West": "Dublin South-West",
    "Dublin South Central": "Dublin South-Central",
    "Dublin South–Central": "Dublin South-Central",
    "Dun Laoghaire": "Dún Laoghaire",
    "Dun Laoghaire Rathdown": "Dún Laoghaire",

    # "Leix" and "Laoighis" are older Irish spellings of Laois
    "Leix Offaly": "Laois–Offaly",
    "Laoighis Offaly": "Laois–Offaly",
    "Laois Offaly": "Laois–Offaly",
    "Laois-Offaly": "Laois–Offaly",
    "Laois–Offaly": "Laois–Offaly",

    "Longford Westmeath": "Longford–Westmeath",
    "Longford-Westmeath": "Longford–Westmeath",
    "Longford–Westmeath": "Longford–Westmeath",

    "Sligo Leitrim": "Sligo–Leitrim",
    "Sligo-Leitrim": "Sligo–Leitrim",
    "Sligo–Leitrim": "Sligo–Leitrim",

    "Roscommon Galway": "Roscommon–Galway",
    "Roscommon-Galway": "Roscommon–Galway",
    "Roscommon–Galway": "Roscommon–Galway",
}

PARTY_MAPPING = {
    "Labour": "Labour Party",
    "Labour Party": "Labour Party",
    "Fianna Fail": "Fianna Fáil",
    "Fianna Fáil": "Fianna Fáil",
    "Fine Gael": "Fine Gael",
    "Sinn Fein": "Sinn Féin",
    "Sinn Féin": "Sinn Féin",
    "Green/Comhaontas Glas": "Green Party",
    "Green Party": "Green Party",
    "Non party/Independent": "Independent",
    "Independent": "Independent",
    "Republican": "Sinn Féin",  # Historical - pre-split
    "Progressive Democrats": "Progressive Democrats",
    "Workers Party": "Workers' Party",
    "Workers' Party": "Workers' Party",
    "Democratic Left": "Democratic Left",
    "People Before Profit": "People Before Profit",
    "Solidarity - People Before Profit": "Solidarity–PBP",
    "Social Democrats": "Social Democrats",
    "Aontú": "Aontú",
    "Renua": "Renua Ireland",
}


def standardize_constituency(name):
    if pd.isna(name):
        return None

    if name in CONSTITUENCY_MAPPING:
        return CONSTITUENCY_MAPPING[name]

    # Try with normalized dashes/spaces
    normalized = name.replace("–", "-").replace("—", "-")
    if normalized in CONSTITUENCY_MAPPING:
        return CONSTITUENCY_MAPPING[normalized]

    return name


def standardize_party(name):
    if pd.isna(name):
        return "Unknown"

    if name in PARTY_MAPPING:
        return PARTY_MAPPING[name]

    # Fuzzy match for close variants
    for key, value in PARTY_MAPPING.items():
        if jellyfish.jaro_winkler_similarity(str(name), str(key)) > 0.9:
            return value

    return name


def get_year_from_date(date_str):
    if date_str is None:
        return None
    if isinstance(date_str, (int, float)):
        return int(date_str)

    date_str = str(date_str)
    if len(date_str) == 4 and date_str.isdigit():
        return int(date_str)

    # Try to get last 4 characters as year
    try:
        return int(date_str[-4:])
    except:
        return None


def clean_election_type(election_type_str):
    if pd.isna(election_type_str):
        return None

    election_type_str = str(election_type_str)

    if 'Town' in election_type_str or 'Local' in election_type_str:
        return 'LOCAL'
    elif 'Dail' in election_type_str or 'general' in election_type_str.lower():
        return 'GENERAL'
    elif 'Seanad' in election_type_str:
        return 'SEANAD'
    elif 'Westminster' in election_type_str:
        return 'WESTMINSTER'
    elif 'European' in election_type_str:
        return 'EUROPEAN'
    elif 'By Election' in election_type_str or 'by-election' in election_type_str.lower():
        return 'BY-ELECTION'
    else:
        return None


def clean_elected_status(status):
    if pd.isna(status):
        return None

    status = str(status).lower()
    if status == 'elected' or status == 'true':
        return True
    elif status in ['not elected', 'false']:
        return False
    else:
        return None


def load_and_clean_electionsireland():
    print("Loading ElectionsIreland data...")
    df = pd.read_parquet('electionsireland_data/ElectionsIreland_candidate.parquet')
    df = df.rename(columns={'ID': 'candidate_ID'})

    df['year'] = df['date'].apply(get_year_from_date)
    df['election_type'] = df['election_type'].apply(clean_election_type)
    df['elected'] = df['status'].apply(clean_elected_status)
    df['constituency_clean'] = df['constituency_name'].apply(standardize_constituency)
    df['party_clean'] = df['party'].apply(standardize_party)

    # Remove appointments, resignations, etc.
    df = df[df['elected'].notna()].copy()

    df = df[[
        'year', 'candidate', 'candidate_ID', 'constituency_name', 'constituency_clean',
        'party', 'party_clean', 'elected', 'election_type',
        'first_pref_count', 'first_pref_pct', 'pct_of_quota_reached_with_first_pref'
    ]].copy()

    df['source'] = 'electionsireland'

    print(f"  Loaded {len(df)} records")
    return df


def load_and_clean_irelandelection():
    print("Loading IrelandElection data...")
    df = pd.read_parquet('irelandelection/ALL_CANDIDATES.parquet')

    df = df.rename(columns={
        'first_pref_quota_ratio': 'pct_of_quota_reached_with_first_pref',
        'constituency': 'constituency_name'
    })

    df['year'] = df['year'].astype(float)
    df['constituency_clean'] = df['constituency_name'].apply(standardize_constituency)
    df['party_clean'] = df['party'].apply(standardize_party)
    df['election_type'] = df['election_type'].str.upper()

    df.loc[df['election_type'] == 'GENERAL', 'election_type'] = 'GENERAL'
    df.loc[df['election_type'] == 'LOCAL', 'election_type'] = 'LOCAL'

    df['candidate_ID'] = None
    df['source'] = 'irelandelection'

    df = df[[
        'year', 'candidate', 'candidate_ID', 'constituency_name', 'constituency_clean',
        'party', 'party_clean', 'elected', 'election_type',
        'first_pref_count', 'first_pref_pct', 'pct_of_quota_reached_with_first_pref',
        'source'
    ]].copy()

    print(f"  Loaded {len(df)} records")
    return df


# Match on year, election type, candidate name similarity, and constituency similarity
def match_records(df1, df2):
    print("\nMatching records between datasets...")

    matched_pairs = []
    df2_matched_indices = set()

    df2_by_year = df2.groupby('year')

    for idx1, row1 in df1.iterrows():
        if row1['year'] not in df2_by_year.groups:
            continue

        candidates_same_year = df2.loc[df2_by_year.groups[row1['year']]]

        for idx2, row2 in candidates_same_year.iterrows():
            if idx2 in df2_matched_indices:
                continue

            name_sim = jellyfish.jaro_winkler_similarity(
                str(row1['candidate']).lower(),
                str(row2['candidate']).lower()
            )
            if name_sim < 0.85:
                continue

            if row1['election_type'] != row2['election_type']:
                continue

            const_sim = jellyfish.jaro_winkler_similarity(
                str(row1['constituency_clean'] or row1['constituency_name']).lower(),
                str(row2['constituency_clean'] or row2['constituency_name']).lower()
            )

            # Party similarity as a fallback signal
            party_sim = jellyfish.jaro_winkler_similarity(
                str(row1['party_clean']).lower(),
                str(row2['party_clean']).lower()
            )

            if const_sim > 0.8 or (party_sim > 0.85 and const_sim > 0.6):
                matched_pairs.append((idx1, idx2))
                df2_matched_indices.add(idx2)
                break

    print(f"  Found {len(matched_pairs)} matching pairs")
    return matched_pairs, df2_matched_indices


def merge_datasets(df1, df2, matched_pairs, df2_matched_indices):
    print("\nMerging datasets...")

    merged_records = []
    df1_matched_indices = set(p[0] for p in matched_pairs)

    # Take best data from each source for matched pairs
    for idx1, idx2 in matched_pairs:
        row1 = df1.loc[idx1]
        row2 = df2.loc[idx2]

        merged = {
            'year': row1['year'],
            'candidate': row1['candidate'],
            'candidate_ID': row1['candidate_ID'],
            'constituency_name': row2['constituency_name'] if len(str(row2['constituency_name'])) > len(str(row1['constituency_name'])) else row1['constituency_name'],
            'constituency_clean': row1['constituency_clean'] or row2['constituency_clean'],
            'party': row1['party'],
            'party_clean': row1['party_clean'] or row2['party_clean'],
            'elected': row1['elected'] if row1['elected'] is not None else row2['elected'],
            'election_type': row1['election_type'],
            'first_pref_count': row1['first_pref_count'] if pd.notna(row1['first_pref_count']) else row2['first_pref_count'],
            'first_pref_pct': row2['first_pref_pct'] if pd.notna(row2['first_pref_pct']) else row1['first_pref_pct'],
            'pct_of_quota_reached_with_first_pref': row2['pct_of_quota_reached_with_first_pref'] if pd.notna(row2['pct_of_quota_reached_with_first_pref']) else row1['pct_of_quota_reached_with_first_pref'],
            'source': 'merged'
        }
        merged_records.append(merged)

    for idx, row in df1.iterrows():
        if idx not in df1_matched_indices:
            merged_records.append(row.to_dict())

    # Unmatched df2 rows get new IDs
    max_id = df1['candidate_ID'].max() + 1
    for idx, row in df2.iterrows():
        if idx not in df2_matched_indices:
            record = row.to_dict()
            record['candidate_ID'] = max_id
            max_id += 1
            merged_records.append(record)

    result = pd.DataFrame(merged_records)
    print(f"  Merged dataset has {len(result)} records")
    return result


def create_analysis_dataset(df):
    print("\nCreating analysis dataset...")

    # Focus on Dáil (GENERAL) elections for main analysis
    dail_df = df[df['election_type'] == 'GENERAL'].copy()

    dail_df['decade'] = (dail_df['year'] // 10 * 10).astype(int)
    dail_df['won'] = dail_df['elected'].astype(bool)
    dail_df['quota_ratio'] = pd.to_numeric(
        dail_df['pct_of_quota_reached_with_first_pref'],
        errors='coerce'
    )

    print(f"  Dáil elections dataset: {len(dail_df)} records")
    print(f"  Year range: {dail_df['year'].min():.0f} - {dail_df['year'].max():.0f}")
    print(f"  Unique candidates: {dail_df['candidate_ID'].nunique()}")
    print(f"  Unique constituencies: {dail_df['constituency_clean'].nunique()}")

    return dail_df


def compute_statistics(df):
    print("\nComputing statistics...")

    stats = {}

    winners = df[df['won']]['quota_ratio'].dropna()
    losers = df[~df['won']]['quota_ratio'].dropna()

    stats['winners_mean_quota'] = winners.mean()
    stats['winners_median_quota'] = winners.median()
    stats['losers_mean_quota'] = losers.mean()
    stats['losers_median_quota'] = losers.median()

    # Anomalies - people who exceeded quota but lost
    anomalies = df[~df['won'] & (df['quota_ratio'] > 1.0)]
    stats['exceeded_quota_but_lost'] = len(anomalies)
    stats['anomaly_records'] = anomalies[['year', 'candidate', 'constituency_clean', 'quota_ratio']].to_dict('records')

    party_stats = df.groupby('party_clean').agg({
        'won': ['sum', 'count'],
        'quota_ratio': 'mean'
    }).round(3)
    party_stats.columns = ['wins', 'total_candidates', 'avg_quota_ratio']
    party_stats['win_rate'] = (party_stats['wins'] / party_stats['total_candidates'] * 100).round(1)
    stats['party_performance'] = party_stats.sort_values('wins', ascending=False).head(10).to_dict()

    decade_stats = df.groupby('decade').agg({
        'candidate_ID': 'nunique',
        'constituency_clean': 'nunique',
        'won': 'sum'
    })
    decade_stats.columns = ['unique_candidates', 'constituencies', 'seats_filled']
    stats['by_decade'] = decade_stats.to_dict()

    return stats


def run_pipeline():
    print("=" * 60)
    print("IRISH ELECTIONS DATA PIPELINE")
    print("=" * 60)

    df1 = load_and_clean_electionsireland()
    df2 = load_and_clean_irelandelection()

    matched_pairs, df2_matched = match_records(df1, df2)
    merged_df = merge_datasets(df1, df2, matched_pairs, df2_matched)

    merged_df.to_parquet('merged_elections_full.parquet', index=False)
    print("\n  Saved: merged_elections_full.parquet")

    analysis_df = create_analysis_dataset(merged_df)
    analysis_df.to_parquet('dail_elections_analysis.parquet', index=False)
    print("  Saved: dail_elections_analysis.parquet")

    stats = compute_statistics(analysis_df)
    with open('election_statistics.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    print("  Saved: election_statistics.json")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    return merged_df, analysis_df, stats


if __name__ == "__main__":
    merged_df, analysis_df, stats = run_pipeline()

    print("\nKEY FINDINGS:")
    print(f"   Winners avg quota ratio: {stats['winners_mean_quota']:.2f}")
    print(f"   Losers avg quota ratio: {stats['losers_mean_quota']:.2f}")
    print(f"   Candidates who exceeded quota but lost: {stats['exceeded_quota_but_lost']}")
