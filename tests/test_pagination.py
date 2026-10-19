import asyncio

from core.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    PaginationParams,
    get_pagination,
)


def test_pagination_defaults_and_skip():
    pagination = PaginationParams(page=2, page_size=20)

    assert DEFAULT_PAGE == 1
    assert DEFAULT_PAGE_SIZE == 20
    assert pagination.skip == 20


def test_pagination_dependency_returns_params():
    pagination = asyncio.run(get_pagination(page=3, page_size=10))

    assert pagination.page == 3
    assert pagination.page_size == 10
    assert pagination.skip == 20
