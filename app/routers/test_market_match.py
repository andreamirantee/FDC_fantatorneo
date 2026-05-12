import pytest

from ..schemas import MatchResult
from .market import record_match


class _Result:
    def __init__(self, data):
        self.data = data


class _TableQuery:
    def __init__(self, client, table_name):
        self._client = client
        self._table = table_name
        self._filters = []
        self._limit = None
        self._select_fields = None
        self._operation = "select"
        self._update_payload = None
        self._insert_payload = None

    def select(self, fields):
        self._operation = "select"
        self._select_fields = [f.strip() for f in fields.split(",")]
        return self

    def eq(self, key, value):
        self._filters.append(lambda row: row.get(key) == value)
        return self

    def is_(self, key, value):
        if value == "null":
            self._filters.append(lambda row: row.get(key) is None)
        else:
            self._filters.append(lambda row: row.get(key) == value)
        return self

    def limit(self, count):
        self._limit = count
        return self

    def update(self, payload):
        self._operation = "update"
        self._update_payload = payload
        return self

    def insert(self, payload):
        self._operation = "insert"
        self._insert_payload = payload
        return self

    def execute(self):
        table = self._client._tables.setdefault(self._table, [])
        rows = list(table)
        for predicate in self._filters:
            rows = [row for row in rows if predicate(row)]
        if self._limit is not None:
            rows = rows[: self._limit]

        if self._operation == "select":
            if self._select_fields:
                data = [
                    {field: row.get(field) for field in self._select_fields}
                    for row in rows
                ]
            else:
                data = [dict(row) for row in rows]
            return _Result(data)

        if self._operation == "update":
            updated = []
            for row in table:
                if all(predicate(row) for predicate in self._filters):
                    row.update(self._update_payload)
                    updated.append(dict(row))
            return _Result(updated)

        if self._operation == "insert":
            payload = self._insert_payload
            if isinstance(payload, list):
                table.extend([dict(item) for item in payload])
                return _Result([dict(item) for item in payload])
            table.append(dict(payload))
            return _Result([dict(payload)])

        return _Result([])


class _FakeClient:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def table(self, name):
        return _TableQuery(self, name)


def _build_client_for_calcio():
    return _FakeClient(
        tables={
            "participants": [
                {
                    "id": 1,
                    "role": "Calcio",
                    "group_code": "A",
                    "score": 0,
                    "matches_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "sets_won": 0,
                    "sets_lost": 0,
                },
                {
                    "id": 2,
                    "role": "Calcio",
                    "group_code": "A",
                    "score": 0,
                    "matches_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "sets_won": 0,
                    "sets_lost": 0,
                },
            ],
            "team_participants_history": [
                {"team_id": 10, "participant_id": 1, "released_at": None},
                {"team_id": 20, "participant_id": 2, "released_at": None},
            ],
            "teams": [
                {"id": 10, "score": 5},
                {"id": 20, "score": 7},
            ],
            "matches": [],
        }
    )


def test_record_match_calcio_updates_points_and_teams():
    client = _build_client_for_calcio()
    payload = MatchResult(
        home_squad_id=1,
        away_squad_id=2,
        home_score=2,
        away_score=1,
        sport="Calcio",
        stage="group",
    )

    result = record_match(payload, client=client, x_admin_token="a3f9c4b8de")

    assert result["home_points_awarded"] == 3
    assert result["away_points_awarded"] == 0

    home = next(row for row in client._tables["participants"] if row["id"] == 1)
    away = next(row for row in client._tables["participants"] if row["id"] == 2)
    assert home["score"] == 3
    assert away["score"] == 0
    assert home["wins"] == 1
    assert away["losses"] == 1
    assert home["goals_for"] == 2
    assert home["goals_against"] == 1
    assert away["goals_for"] == 1
    assert away["goals_against"] == 2

    team_home = next(row for row in client._tables["teams"] if row["id"] == 10)
    team_away = next(row for row in client._tables["teams"] if row["id"] == 20)
    assert team_home["score"] == 8
    assert team_away["score"] == 7


def test_record_match_group_stage_sets_group_code():
    client = _FakeClient(
        tables={
            "participants": [
                {
                    "id": 11,
                    "role": "Pallavolo",
                    "group_code": "B",
                    "score": 0,
                    "matches_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "sets_won": 0,
                    "sets_lost": 0,
                },
                {
                    "id": 12,
                    "role": "Pallavolo",
                    "group_code": "B",
                    "score": 0,
                    "matches_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "sets_won": 0,
                    "sets_lost": 0,
                },
            ],
            "team_participants_history": [],
            "teams": [],
            "matches": [],
        }
    )

    payload = MatchResult(
        home_squad_id=11,
        away_squad_id=12,
        home_score=3,
        away_score=1,
        sport="Pallavolo",
        stage="group",
    )

    record_match(payload, client=client, x_admin_token="a3f9c4b8de")

    assert client._tables["matches"][0]["group_code"] == "B"
    assert client._tables["matches"][0]["sport"] == "pallavolo"
