from datetime import datetime

from ..database import get_connection
from .billing import calculate_fee
from .space_manager import (
    get_space_by_code,
    can_occupy,
    occupy_space,
    release_space,
)


class OrderNotFoundError(Exception):
    pass


class OrderAlreadyPaidError(Exception):
    pass


class SpaceNotFoundError(Exception):
    pass


class SpaceNotAvailableError(Exception):
    pass


class ValidationError(Exception):
    pass


def list_recent_orders(conn, limit=100):
    rows = conn.execute(
        "SELECT * FROM parking_orders ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return rows


def get_order_by_id(conn, order_id):
    return conn.execute("SELECT * FROM parking_orders WHERE id = ?", (order_id,)).fetchone()


def create_entry(conn, plate_number, space_code, entry_time=None):
    if not plate_number or not space_code:
        raise ValidationError("车牌号和车位号不能为空")

    space = get_space_by_code(conn, space_code)
    if not space:
        raise SpaceNotFoundError("车位不存在")
    if not can_occupy(space):
        raise SpaceNotAvailableError("车位当前不可入场")

    if not entry_time:
        entry_time = datetime.now().isoformat(timespec="minutes")

    cur = conn.execute(
        """
        INSERT INTO parking_orders (plate_number, space_code, entry_time, status)
        VALUES (?, ?, ?, 'parking')
        """,
        (plate_number, space_code, entry_time),
    )
    occupy_space(conn, space_code, plate_number)
    return conn.execute("SELECT * FROM parking_orders WHERE id = ?", (cur.lastrowid,)).fetchone()


def settle_order(conn, order_id, exit_time=None):
    order = get_order_by_id(conn, order_id)
    if not order:
        raise OrderNotFoundError("停车订单不存在")
    if order["status"] == "paid":
        raise OrderAlreadyPaidError("订单已结算")

    if not exit_time:
        exit_time = datetime.now().isoformat(timespec="minutes")

    bill = calculate_fee(order["entry_time"], exit_time)
    conn.execute(
        """
        UPDATE parking_orders
        SET exit_time = ?, duration_hours = ?, amount = ?, status = 'paid'
        WHERE id = ?
        """,
        (exit_time, bill["duration_hours"], bill["amount"], order_id),
    )
    release_space(conn, order["space_code"])
    return conn.execute("SELECT * FROM parking_orders WHERE id = ?", (order_id,)).fetchone()
