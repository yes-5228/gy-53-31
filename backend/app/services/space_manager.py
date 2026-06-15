class SpaceInUseError(Exception):
    pass


class InvalidSpaceTransitionError(Exception):
    pass


class SpaceNotFoundError(Exception):
    pass


VALID_OCCUPY_STATUSES = {"free", "reserved"}
VALID_STATUSES = {"free", "occupied", "reserved", "maintenance"}


def get_space_by_code(conn, code):
    return conn.execute("SELECT * FROM spaces WHERE code = ?", (code,)).fetchone()


def get_space_by_id(conn, space_id):
    return conn.execute("SELECT * FROM spaces WHERE id = ?", (space_id,)).fetchone()


def list_all_spaces(conn):
    return conn.execute("SELECT * FROM spaces ORDER BY area, code").fetchall()


def get_space_stats(conn):
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM spaces
        GROUP BY status
        """
    ).fetchall()
    return {row["status"]: row["count"] for row in rows}


def can_occupy(space):
    return space["status"] in VALID_OCCUPY_STATUSES


def _has_active_parking_order(conn, space_code):
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM parking_orders
        WHERE space_code = ? AND status = 'parking'
        """,
        (space_code,),
    ).fetchone()
    return row["count"] > 0


def occupy_space(conn, code, plate_number):
    conn.execute(
        """
        UPDATE spaces
        SET status = 'occupied', plate_number = ?, updated_at = datetime('now', 'localtime')
        WHERE code = ?
        """,
        (plate_number, code),
    )


def release_space(conn, code):
    if _has_active_parking_order(conn, code):
        raise SpaceInUseError("该车位存在未结算订单，请先完成结算后再释放")
    conn.execute(
        """
        UPDATE spaces
        SET status = 'free', plate_number = NULL, updated_at = datetime('now', 'localtime')
        WHERE code = ?
        """,
        (code,),
    )


def update_space_status(conn, space_id, status, plate_number):
    if status not in VALID_STATUSES:
        raise ValueError("车位状态不合法")

    space = get_space_by_id(conn, space_id)
    if not space:
        raise SpaceNotFoundError("车位不存在")

    if space["status"] == "occupied" and status == "free":
        if _has_active_parking_order(conn, space["code"]):
            raise SpaceInUseError("该车位存在未结算订单，请先完成对应车辆结算后再释放")

    conn.execute(
        """
        UPDATE spaces
        SET status = ?, plate_number = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (status, plate_number if status == "occupied" else None, space_id),
    )
