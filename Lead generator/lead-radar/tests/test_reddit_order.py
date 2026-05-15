"""Reddit endpoint-order optimization — algemene search eerst, subs als fallback.

Voorheen: per query werden 13 subs eerst geprobeerd (elk 1 HTTP-call), dan
1 algemene /search.json.  Bij low-yield subs gingen we 13 calls door
zonder hits.

Fix: algemene /search.json eerst (1 brede call met goede recall).  Subs
alleen als yield < limit.  Bij high-yield queries scheelt dit 13 calls
per query.
"""
from __future__ import annotations


class _FakeResp:
    def __init__(self, data: dict):
        self._data = data
        self.status_code = 200
    def json(self) -> dict:
        return self._data


class _RecordingSession:
    """PoliteSession-replacement die alle calls logt."""
    def __init__(self, fake_response: dict | None = None):
        self.calls: list[tuple[str, dict | None]] = []
        self.fake_response = fake_response or {"data": {"children": []}}

    def get(self, url: str, *, params: dict | None = None, accept_json: bool = False) -> _FakeResp:
        self.calls.append((url, params))
        return _FakeResp(self.fake_response)


def _reddit_listing(n: int) -> dict:
    """Build een /search.json response met N posts."""
    children = []
    for i in range(n):
        children.append({"data": {
            "id": f"post{i}",
            "permalink": f"/r/test/comments/post{i}/title/",
            "title": f"title {i}",
            "selftext": "body",
            "author": "user",
            "created_utc": 1700000000 + i,
            "subreddit": "test",
            "score": 1,
        }})
    return {"data": {"children": children}}


def test_general_search_endpoint_called_first() -> None:
    """Eerste HTTP-call moet /search.json zijn (algemeen), niet /r/<sub>/search.json."""
    from consumer.sources import reddit

    sess = _RecordingSession(fake_response=_reddit_listing(0))
    reddit.fetch("warmtepomp", limit=25, session=sess, subreddits=["thenetherlands", "amsterdam"])

    assert sess.calls, "Geen calls geobserveerd"
    first_url = sess.calls[0][0]
    assert "/search.json" in first_url, f"Eerste call moet algemeen zijn; was {first_url}"
    assert "/r/" not in first_url, (
        f"Eerste call moet algemeen /search.json zijn (geen /r/<sub>/), was {first_url}"
    )


def test_subs_skipped_when_general_yields_enough() -> None:
    """Bij genoeg hits uit /search.json: subs worden niet bezocht."""
    from consumer.sources import reddit

    sess = _RecordingSession(fake_response=_reddit_listing(25))
    reddit.fetch("warmtepomp", limit=25, session=sess,
                 subreddits=["thenetherlands", "amsterdam", "duurzaam"])

    assert len(sess.calls) == 1, (
        f"Verwacht 1 call (algemene); kreeg {len(sess.calls)}: {[c[0] for c in sess.calls]}"
    )


def test_subs_visited_when_general_yields_zero() -> None:
    """Bij 0 hits uit algemene: subs worden wel bezocht als fallback."""
    from consumer.sources import reddit

    sess = _RecordingSession(fake_response=_reddit_listing(0))
    reddit.fetch("very_specific_query", limit=25, session=sess,
                 subreddits=["a", "b", "c"])

    # 1 algemeen + 3 subs = 4 calls
    assert len(sess.calls) == 4, (
        f"Verwacht 4 calls (1 algemeen + 3 subs); kreeg {len(sess.calls)}: "
        f"{[c[0] for c in sess.calls]}"
    )
