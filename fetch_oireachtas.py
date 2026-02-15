import requests
import pandas as pd

BASE_URL = "https://api.oireachtas.ie/v1/members"
PARAMS = {
    "limit": 100,
    "chamber": "dail",
    "date_start": "1900-01-01",
    "date_end": "2025-01-01",
}
OUTPUT = r"c:\Users\Rober\Documents\Political party\analyisis_of_elections\oireachtas_members.parquet"

def fetch_all_members():
    skip = 0
    all_results = []
    while True:
        params = {**PARAMS, "skip": skip}
        r = requests.get(BASE_URL, params=params)
        r.raise_for_status()
        data = r.json()
        results = data["results"]
        if not results:
            break
        all_results.extend(results)
        total = data["head"]["counts"]["resultCount"]
        print(f"Fetched {min(len(all_results), total)}/{total}")
        if len(all_results) >= total:
            all_results = all_results[:total]
            break
        skip += 100
    return all_results

def parse_records(results):
    rows = []
    for item in results:
        m = item["member"]
        base = {
            "memberCode": m["memberCode"],
            "pId": m["pId"],
            "firstName": m["firstName"],
            "lastName": m["lastName"],
            "fullName": m["fullName"],
            "dateOfDeath": m.get("dateOfDeath"),
        }
        for ms in m["memberships"]:
            mem = ms["membership"]
            parties = mem.get("parties", [])
            party = parties[0]["party"]["showAs"] if parties else None
            represents = mem.get("represents", [])
            constituency = represents[0]["represent"]["showAs"] if represents else None
            row = {
                **base,
                "houseNo": mem["house"]["houseNo"],
                "constituency": constituency,
                "party": party,
                "startDate": mem["dateRange"]["start"],
                "endDate": mem["dateRange"]["end"],
            }
            rows.append(row)
    return rows

if __name__ == "__main__":
    results = fetch_all_members()
    rows = parse_records(results)
    df = pd.DataFrame(rows)
    print(f"\n{len(df)} rows, {df['memberCode'].nunique()} unique members")
    print(df.head())
    df.to_parquet(OUTPUT, index=False)
    print(f"\nSaved to {OUTPUT}")
