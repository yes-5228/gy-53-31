from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts
from ..services.billing import calculate_fee
from ..services.parking_order import (
    list_recent_orders,
    create_entry,
    settle_order,
    release_space_by_order,
    ValidationError,
    SpaceNotFoundError,
    SpaceNotAvailableError,
    OrderNotFoundError,
    OrderAlreadyPaidError,
    OrderNotPaidError,
)

parking_bp = Blueprint("parking", __name__)


@parking_bp.get("/orders")
def list_orders():
    with get_connection() as conn:
        rows = list_recent_orders(conn)
    return {"items": rows_to_dicts(rows)}


@parking_bp.post("/entry")
def create_entry_view():
    data = request.get_json() or {}
    try:
        with get_connection() as conn:
            row = create_entry(
                conn,
                data.get("plate_number"),
                data.get("space_code"),
                data.get("entry_time"),
            )
    except ValidationError as e:
        return {"message": str(e)}, 400
    except SpaceNotFoundError as e:
        return {"message": str(e)}, 404
    except SpaceNotAvailableError as e:
        return {"message": str(e)}, 409
    return dict(row), 201


@parking_bp.post("/calculate")
def calculate():
    data = request.get_json() or {}
    if not data.get("entry_time") or not data.get("exit_time"):
        return {"message": "入场时间和离场时间不能为空"}, 400
    return calculate_fee(data["entry_time"], data["exit_time"])


@parking_bp.post("/exit/<int:order_id>")
def close_order(order_id):
    data = request.get_json() or {}
    try:
        with get_connection() as conn:
            row = settle_order(conn, order_id, data.get("exit_time"))
    except OrderNotFoundError as e:
        return {"message": str(e)}, 404
    except OrderAlreadyPaidError as e:
        return {"message": str(e)}, 409
    return dict(row)


@parking_bp.post("/release/<int:order_id>")
def release_space(order_id):
    try:
        with get_connection() as conn:
            space = release_space_by_order(conn, order_id)
    except OrderNotFoundError as e:
        return {"message": str(e)}, 404
    except OrderNotPaidError as e:
        return {"message": str(e)}, 409
    return dict(space)
