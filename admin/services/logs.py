from admin.schemas.logs import AdminActionLogRead
from admin.schemas.pagination import PaginatedResponse
from admin.utils.pagination import build_pagination_meta, normalize_pagination


def list_action_logs(page: int, per_page: int) -> PaginatedResponse[AdminActionLogRead]:
    current_page, normalized_per_page = normalize_pagination(page, per_page)
    return PaginatedResponse(
        data=[],
        meta=build_pagination_meta(
            total=0,
            page=current_page,
            per_page=normalized_per_page,
        ),
    )
