import os
import time
from collections import Counter

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
PLATFORM = "https://euw1.api.riotgames.com"
REGION = "https://europe.api.riotgames.com"

HEADERS = {"X-Riot-Token": API_KEY}

def riot_get(url, params=None):
    while True:
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 429:
            time.sleep(15)
            continue

        if response.status_code != 200:
            print("Status:", response.status_code)
            print("Response:", response.text)
            print("URL:", response.url)

        response.raise_for_status()
        return response.json()

def get_league_players(tier="DIAMOND", division="I", pages=1):
    players = []

    for page in range(1, pages + 1):
        url = f"{PLATFORM}/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{division}"
        data = riot_get(url, params={"page": page})
        players.extend(data)

    return players


def get_summoner(summoner_id):
    url = f"{PLATFORM}/lol/summoner/v4/summoners/{summoner_id}"
    return riot_get(url)


def get_match_ids(puuid, count=50):
    url = f"{REGION}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return riot_get(url, params={
        "queue": 420,
        "count": count
    })


def get_match(match_id):
    url = f"{REGION}/lol/match/v5/matches/{match_id}"
    return riot_get(url)


def extract_player_row(match, puuid):
    for p in match["info"]["participants"]:
        if p["puuid"] == puuid:
            return {
                "puuid": puuid,
                "match_id": match["metadata"]["matchId"],
                "champion": p["championName"],
                "win": p["win"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "team_position": p["teamPosition"],
                "game_duration": match["info"]["gameDuration"],
            }

    return None


def main():
    players = get_league_players(tier="DIAMOND", division="I", pages=1)

    match_rows = []
    player_rows = []

    for player in players[:20]:
        print(player)
        puuid = player["puuid"]
    

        match_ids = get_match_ids(puuid, count=50)
        player_matches = []

        for match_id in match_ids:
            match = get_match(match_id)
            row = extract_player_row(match, puuid)

            if row is not None:
                match_rows.append(row)
                player_matches.append(row)

            time.sleep(1.2)

        if not player_matches:
            continue

        champions = Counter(row["champion"] for row in player_matches)
        main_champion, main_champ_games = champions.most_common(1)[0]
        wins = sum(row["win"] for row in player_matches)

        player_rows.append({
            "puuid": puuid,
            "tier": player["tier"],
            "rank": player["rank"],
            "games": len(player_matches),
            "main_champion": main_champion,
            "main_champ_games": main_champ_games,
            "otp_score": main_champ_games / len(player_matches),
            "winrate": wins / len(player_matches),
        })

        print(f"Done: {main_champion}, OTP={main_champ_games / len(player_matches):.2f}")

    pd.DataFrame(match_rows).to_csv("lol_matches.csv", index=False)
    pd.DataFrame(player_rows).to_csv("lol_players_otp.csv", index=False)

    print("Saved lol_matches.csv and lol_players_otp.csv")


if __name__ == "__main__":
    main()
