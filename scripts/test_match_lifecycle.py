import sys
import time
import requests

API_BASE = "http://localhost:8000/api/v1/market"
ADMIN_TOKEN = "a3f9c4b8de"
HEADERS = {"X-Admin-Token": ADMIN_TOKEN}

def fetch_ranking():
    r = requests.get(f"{API_BASE}/ranking")
    r.raise_for_status()
    return r.json()

def fetch_admin_matches():
    r = requests.get(f"{API_BASE}/admin/matches", headers=HEADERS)
    r.raise_for_status()
    return r.json()

def post_match(payload):
    r = requests.post(f"{API_BASE}/match", json=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def update_match(match_id, payload):
    r = requests.post(f"{API_BASE}/admin/matches/{match_id}", json=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def delete_match(match_id):
    r = requests.delete(f"{API_BASE}/admin/matches/{match_id}", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def find_participants():
    ranking = fetch_ranking()
    if not ranking or len(ranking) < 2:
        print("Need at least 2 participants in ranking to run tests.")
        sys.exit(2)
    return ranking[0], ranking[1]


def snapshot_stats(participant):
    return {
        "id": int(participant["id"]),
        "score": int(participant.get("score") or 0),
        "matches_played": int(participant.get("matches_played") or 0),
        "wins": int(participant.get("wins") or 0),
        "losses": int(participant.get("losses") or 0),
        "draws": int(participant.get("draws") or 0),
        "goals_for": int(participant.get("goals_for") or 0),
        "goals_against": int(participant.get("goals_against") or 0),
        "sets_won": int(participant.get("sets_won") or 0),
        "sets_lost": int(participant.get("sets_lost") or 0),
    }


def assert_stats(before, after, expected_delta):
    for k, v in expected_delta.items():
        before_v = before.get(k, 0)
        after_v = after.get(k, 0)
        exp = before_v + v
        if after_v != exp:
            print(f"Assertion failed for {k}: before={before_v} after={after_v} expected={exp}")
            return False
    return True


if __name__ == '__main__':
    print("Fetching participants...")
    p1, p2 = find_participants()
    print(f"Selected participants: {p1['id']} vs {p2['id']}")

    before_p1 = snapshot_stats(p1)
    before_p2 = snapshot_stats(p2)

    # 1) Create match where p1 wins (calcio): 2-1
    print("Creating match: home wins 2-1 (calcio)")
    payload = {
        "home_squad_id": p1["id"],
        "away_squad_id": p2["id"],
        "home_score": 2,
        "away_score": 1,
        "sport": "calcio",
        "stage": "group",
    }
    res = post_match(payload)
    print("Create response:", res)

    # allow DB eventual consistency
    time.sleep(0.5)

    matches = fetch_admin_matches()
    # find our match - newest matching entry
    match = next((m for m in matches if int(m.get("home_squad_id") or -1) == p1["id"] and int(m.get("away_squad_id") or -1) == p2["id"] and int(m.get("home_score") or -1) == 2 and int(m.get("away_score") or -1) == 1), None)
    if not match:
        print("Match not found in admin list after creation")
        sys.exit(3)
    match_id = int(match["id"])
    print("Match created id:", match_id)

    # fetch ranking after create
    ranking_after_create = fetch_ranking()
    a1 = next((r for r in ranking_after_create if int(r["id"]) == p1["id"]), None)
    a2 = next((r for r in ranking_after_create if int(r["id"]) == p2["id"]), None)
    after_p1 = snapshot_stats(a1)
    after_p2 = snapshot_stats(a2)

    # Expected deltas for calcio home win 2-1
    expected_p1 = {"score": 3, "matches_played": 1, "wins": 1, "goals_for": 2, "goals_against": 1}
    expected_p2 = {"score": 0, "matches_played": 1, "losses": 1, "goals_for": 1, "goals_against": 2}

    ok1 = assert_stats(before_p1, after_p1, expected_p1)
    ok2 = assert_stats(before_p2, after_p2, expected_p2)

    print("Create assertions:", ok1, ok2)
    if not (ok1 and ok2):
        print("Create test failed")
        sys.exit(4)

    # 2) Modify match: now away wins 0-2
    print("Modifying match: home 0 - away 2 (away wins)")
    upd_payload = {"home_score": 0, "away_score": 2}
    update_res = update_match(match_id, upd_payload)
    print("Update response:", update_res)
    time.sleep(0.5)

    ranking_after_update = fetch_ranking()
    b1 = next((r for r in ranking_after_update if int(r["id"]) == p1["id"]), None)
    b2 = next((r for r in ranking_after_update if int(r["id"]) == p2["id"]), None)
    after_update_p1 = snapshot_stats(b1)
    after_update_p2 = snapshot_stats(b2)

    # Expected final stats should be initial + effect of new result (away win 0-2)
    # For away win in calcio: home +0, away +3
    expected_final_p1 = {"score": 0, "matches_played": 1, "losses": 1, "goals_for": 0, "goals_against": 2}
    expected_final_p2 = {"score": 3, "matches_played": 1, "wins": 1, "goals_for": 2, "goals_against": 0}

    ok3 = assert_stats(before_p1, after_update_p1, expected_final_p1)
    ok4 = assert_stats(before_p2, after_update_p2, expected_final_p2)
    print("Update assertions:", ok3, ok4)
    if not (ok3 and ok4):
        print("Update test failed")
        sys.exit(5)

    # 3) Delete match -> should rollback to before state
    print("Deleting match id", match_id)
    del_res = delete_match(match_id)
    print("Delete response:", del_res)
    time.sleep(0.5)

    ranking_after_delete = fetch_ranking()
    c1 = next((r for r in ranking_after_delete if int(r["id"]) == p1["id"]), None)
    c2 = next((r for r in ranking_after_delete if int(r["id"]) == p2["id"]), None)
    after_delete_p1 = snapshot_stats(c1)
    after_delete_p2 = snapshot_stats(c2)

    ok5 = all(after_delete_p1[k] == before_p1[k] for k in before_p1)
    ok6 = all(after_delete_p2[k] == before_p2[k] for k in before_p2)
    print("Delete assertions:", ok5, ok6)
    if not (ok5 and ok6):
        print("Delete test failed")
        sys.exit(6)

    print("All match lifecycle tests passed")
    sys.exit(0)
