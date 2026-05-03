from math import ceil
from typing import Any

from sqlalchemy.orm import Query

from admin.schemas.pagination import PaginationMeta


def normalize_pagination(page: int, per_page: int) -> tuple[int, int]:
    return max(page, 1), min(max(per_page, 1), 100)


def build_pagination_meta(total: int, page: int, per_page: int) -> PaginationMeta:
    last_page = max(ceil(total / per_page), 1) if per_page else 1
    return PaginationMeta(
        current_page=page,
        per_page=per_page,
        last_page=last_page,
        total=total,
    )


def paginate_query(query: Query, page: int, per_page: int) -> tuple[list[Any], PaginationMeta]:
    current_page, normalized_per_page = normalize_pagination(page, per_page)
    total = query.order_by(None).count()
    items = (
        query.limit(normalized_per_page)
        .offset((current_page - 1) * normalized_per_page)
        .all()
    )
    return items, build_pagination_meta(total, current_page, normalized_per_page)
