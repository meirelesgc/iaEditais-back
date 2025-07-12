async def user_unit_post(conn, user_unit):
    params = user_unit.model_dump()
    SCRIPT_SQL = """
        INSERT INTO user_units (user_id, unit_id)
        VALUES (%(user_id)s, %(unit_id)s)
        ON CONFLICT DO NOTHING
        """
    await conn.exec(SCRIPT_SQL, params)


async def user_unit_delete(conn, user_id, unit_id):
    params = {'user_id': user_id, 'unit_id': unit_id}
    SCRIPT_SQL = """
        DELETE FROM user_units
        WHERE user_id = %(user_id)s AND unit_id = %(unit_id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def user_unit_get_user(conn, user_id):
    params = {'user_id': user_id}
    SCRIPT_SQL = """
        SELECT u.id, u.name, u.location, u.created_at, u.updated_at
        FROM units u
        JOIN user_units uu ON uu.unit_id = u.id
        WHERE uu.user_id = %(user_id)s;
        """
    return await conn.select(SCRIPT_SQL, params)


async def user_unit_get_unity(conn, unit_id):
    params = {'unit_id': unit_id}
    SCRIPT_SQL = """
        SELECT u.id, u.username, u.email, u.access_level, u.created_at,
            u.updated_at
        FROM users u
        JOIN user_units uu ON uu.user_id = u.id
        WHERE uu.unit_id = %(unit_id)s;
        """
    return await conn.select(SCRIPT_SQL, params)
