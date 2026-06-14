from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts
from ..services.space_manager import (
    list_all_spaces,
    get_space_stats,
    get_space_by_id,
    update_space_status,
)

spaces_bp = Blueprint("spaces", __name__)


@spaces_bp.get("/", strict_slashes=False)
def list_spaces():
    with get_connection() as conn:
        rows = list_all_spaces(conn)
        stats = get_space_stats(conn)
    return {"items": rows_to_dicts(rows), "stats": stats}


@spaces_bp.patch("/<int:space_id>")
def update_space(space_id):
    data = request.get_json() or {}
    status = data.get("status")
    plate_number = data.get("plate_number")

    with get_connection() as conn:
        try:
            update_space_status(conn, space_id, status, plate_number)
        except ValueError as e:
            return {"message": str(e)}, 400
        row = get_space_by_id(conn, space_id)

    if not row:
        return {"message": "车位不存在"}, 404
    return dict(row)
