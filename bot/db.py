import os
import re

def connect():
    import psycopg
    from psycopg.rows import dict_row

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("ยังไม่ได้ตั้ง DATABASE_URL")
    return psycopg.connect(
        dsn,
        connect_timeout=10,
        sslmode=os.getenv("DB_SSLMODE", "require"),
        row_factory=dict_row,
    )


def _normalize(value: str) -> str:
    return re.sub(r"[\s.\-]+", "", value or "").lower()


def _levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for index_a, char_a in enumerate(a, 1):
        current = [index_a]
        for index_b, char_b in enumerate(b, 1):
            current.append(min(
                previous[index_b] + 1,
                current[index_b - 1] + 1,
                previous[index_b - 1] + (char_a != char_b),
            ))
        previous = current
    return previous[-1]


def _fuzzy_best_ids(candidates: list[tuple[int, str]], query: str) -> list[int]:
    query = _normalize(query)
    best_distance = None
    best_ids: list[int] = []
    for candidate_id, text in candidates:
        candidate = _normalize(text)
        if not candidate:
            continue
        distance = _levenshtein(query, candidate)
        if distance > max(1, round(len(candidate) * 0.4)):
            continue
        if best_distance is None or distance < best_distance:
            best_distance, best_ids = distance, [candidate_id]
        elif distance == best_distance and candidate_id not in best_ids:
            best_ids.append(candidate_id)
    return best_ids


BASE_SELECT = """
SELECT c.id, c.name, c.phone, c.email, c.line_id, c.position,
       c.contact_role, c.contact_type, c.is_available_24h, c.note,
       o.name AS organization_name
FROM contacts c LEFT JOIN organizations o ON o.id = c.organization_id
"""


def search_contacts(query: str, limit: int = 20):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name FROM organizations WHERE LOWER(name)=LOWER(%s) OR LOWER(code)=LOWER(%s) LIMIT 1",
            (query, query),
        )
        organization = cursor.fetchone()
        if not organization:
            like = f"%{query}%"
            cursor.execute(
                "SELECT id, name FROM organizations WHERE name ILIKE %s OR code ILIKE %s ORDER BY name LIMIT 1",
                (like, like),
            )
            organization = cursor.fetchone()
        if organization:
            cursor.execute(BASE_SELECT + " WHERE c.organization_id=%s ORDER BY c.contact_role,c.name LIMIT %s", (organization["id"], limit))
            return organization["name"], cursor.fetchall(), False

        like = f"%{query}%"
        cursor.execute(
            BASE_SELECT + " WHERE c.name ILIKE %s OR c.phone ILIKE %s OR c.email ILIKE %s OR c.position ILIKE %s ORDER BY c.contact_role,c.name LIMIT %s",
            (like, like, like, like, limit),
        )
        contacts = cursor.fetchall()
        if contacts:
            return None, contacts, False

        cursor.execute("SELECT id,name,code FROM organizations")
        organizations = cursor.fetchall()
        candidates = [(row["id"], row["name"]) for row in organizations]
        candidates += [(row["id"], row["code"]) for row in organizations if row["code"]]
        ids = _fuzzy_best_ids(candidates, query)
        if ids:
            matched = next(row for row in organizations if row["id"] == ids[0])
            cursor.execute(BASE_SELECT + " WHERE c.organization_id=%s ORDER BY c.contact_role,c.name LIMIT %s", (matched["id"], limit))
            return matched["name"], cursor.fetchall(), True

        cursor.execute("SELECT id,name FROM contacts")
        contacts = cursor.fetchall()
        ids = _fuzzy_best_ids([(row["id"], row["name"]) for row in contacts], query)
        if ids:
            cursor.execute(BASE_SELECT + " WHERE c.id=ANY(%s) ORDER BY c.contact_role,c.name", (ids,))
            return None, cursor.fetchall(), True
        return None, [], False


def list_emergency_contacts(limit: int = 10):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(BASE_SELECT + " WHERE c.contact_type='EMERGENCY' ORDER BY c.is_available_24h DESC,c.contact_role,c.name LIMIT %s", (limit,))
        return cursor.fetchall()


def add_contact(fields: dict) -> int:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM organizations WHERE LOWER(name)=LOWER(%s) LIMIT 1", (fields["organization"],))
        organization = cursor.fetchone()
        if organization:
            organization_id = organization["id"]
        else:
            cursor.execute("INSERT INTO organizations(name,code) VALUES(%s,%s) RETURNING id", (fields["organization"], fields.get("organization_code")))
            organization_id = cursor.fetchone()["id"]
        cursor.execute(
            """INSERT INTO contacts
            (organization_id,name,phone,email,line_id,position,contact_role,contact_type,is_available_24h,note)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (organization_id, fields["name"], fields.get("phone"), fields.get("email"),
             fields.get("line_id"), fields.get("position"), fields.get("contact_role", "SECONDARY"),
             fields.get("contact_type", "GENERAL"), fields.get("is_available_24h", False), fields.get("note")),
        )
        return cursor.fetchone()["id"]


def dump_all(limit: int = 500):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(BASE_SELECT + " ORDER BY o.name NULLS LAST,c.contact_role,c.name LIMIT %s", (limit,))
        return cursor.fetchall()


def database_status():
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM organizations")
        organizations = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) AS count FROM contacts")
        contacts = cursor.fetchone()["count"]
    return {"organization_count": organizations, "contact_count": contacts}
