from ..database import get_connection


VALID_OCCUPY_STATUSES = {"free", "reserved"}


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
    conn.execute(
        """
        UPDATE spaces
        SET status = 'free', plate_number = NULL, updated_at = datetime('now', 'localtime')
        WHERE code = ?
        """,
        (code,),
    )


def update_space_status(conn, space_id, status, plate_number):
    allowed = {"free", "occupied", "reserved", "maintenance"}
    if status not in allowed:
        raise ValueError("车位状态不合法")
    conn.execute(
        """
        UPDATE spaces
        SET status = ?, plate_number = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (status, plate_number if status == "occupied" else None, space_id),
    )
