"""The caching decorator, exercised against the port it implements."""

from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.puc import Nature
from app.modules.accounts.infrastructure.cache import CachedAccountRepository
from tests.fakes import BrokenRedis, FakeRedis, InMemoryAccountRepository

TTL = 60


def repository(
    redis: FakeRedis,
) -> tuple[CachedAccountRepository, InMemoryAccountRepository]:
    inner = InMemoryAccountRepository(
        [
            Account.open(code="1", name="ACTIVOS", nature=Nature.DEBIT),
            Account.open(code="11", name="DISPONIBLE", nature=Nature.DEBIT),
        ]
    )
    return CachedAccountRepository(inner, redis, ttl=TTL), inner  # type: ignore[arg-type]


async def test_second_read_does_not_reach_the_database() -> None:
    cached, inner = repository(FakeRedis())

    first = await cached.list_subtree(None)
    second = await cached.list_subtree(None)

    assert [a.code for a in first] == [a.code for a in second]
    assert inner.subtree_calls == 1


async def test_cached_entities_survive_the_round_trip() -> None:
    cached, _ = repository(FakeRedis())

    await cached.list_subtree(None)
    restored = await cached.list_subtree(None)

    assert restored[0].nature is Nature.DEBIT
    assert restored[0].level.value == "Clase"


async def test_different_roots_are_cached_apart() -> None:
    cached, inner = repository(FakeRedis())

    await cached.list_subtree(None)
    await cached.list_subtree("11")

    assert inner.subtree_calls == 2


async def test_a_write_invalidates_the_cache() -> None:
    cached, inner = repository(FakeRedis())
    await cached.list_subtree(None)

    await cached.add(Account.open(code="12", name="INVERSIONES", nature=Nature.DEBIT))
    await cached.list_subtree(None)

    assert inner.subtree_calls == 2


async def test_save_invalidates_the_cache() -> None:
    cached, inner = repository(FakeRedis())
    await cached.list_subtree(None)

    account = await cached.get("1")
    assert account is not None
    account.rename("RENAMED")
    await cached.save(account)
    await cached.list_subtree(None)

    assert inner.subtree_calls == 2


async def test_an_empty_batch_does_not_invalidate() -> None:
    cached, inner = repository(FakeRedis())
    await cached.list_subtree(None)

    await cached.add_many([])
    await cached.list_subtree(None)

    assert inner.subtree_calls == 1


async def test_a_broken_cache_still_serves_the_read() -> None:
    """A cache outage must degrade to slow, never to a failed request."""
    cached, inner = repository(BrokenRedis())

    accounts = await cached.list_subtree(None)

    assert [a.code for a in accounts] == ["1", "11"]
    assert inner.subtree_calls == 1


async def test_a_broken_cache_still_allows_writes() -> None:
    cached, inner = repository(BrokenRedis())

    saved = await cached.add(
        Account.open(code="2", name="PASIVO", nature=Nature.CREDIT)
    )

    assert saved.code == "2"
    assert "2" in inner.accounts


async def test_corrupt_payload_is_discarded() -> None:
    redis = FakeRedis()
    cached, inner = repository(redis)
    await cached.list_subtree(None)
    redis.store[next(iter(redis.store))] = "not json"

    accounts = await cached.list_subtree(None)

    assert [a.code for a in accounts] == ["1", "11"]
    assert inner.subtree_calls == 2
