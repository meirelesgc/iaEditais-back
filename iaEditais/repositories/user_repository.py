from uuid import UUID

from pydantic import EmailStr

from iaEditais.core.connection import Connection
from iaEditais.models import user_model


async def post_user(conn: Connection, user: user_model.User):
    params = user.model_dump()
    SCRIPT_SQL = """
        INSERT INTO public.users (id, username, email, unit_id, phone_number, access_level, password, created_at)
        VALUES (%(id)s, %(username)s, %(email)s, %(unit_id)s, %(phone_number)s, %(access_level)s, %(password)s, %(created_at)s);
        """  # noqa: E501
    return await conn.exec(SCRIPT_SQL, params)


async def get_user(
    conn: Connection,
    id: UUID = None,
    email: EmailStr = None,
    unit_id: UUID = None,
):
    one = False
    params = {}

    filter_id = str()
    if id:
        one = True
        params['id'] = id
        filter_id = 'AND id = %(id)s'

    filter_email = str()
    if email:
        one = True
        params['email'] = email
        filter_email = 'AND email = %(email)s'

    filter_unit = str()
    if unit_id:
        params['unit_id'] = unit_id
        filter_unit = 'AND unit_id = %(unit_id)s'

    SCRIPT_SQL = f"""
        SELECT id, username, email, phone_number, unit_id, access_level, password, created_at,
            updated_at
        FROM public.users
        WHERE 1 = 1
            {filter_id}
            {filter_unit}
            {filter_email};
        """
    return await conn.select(SCRIPT_SQL, params, one)


async def put_user(conn: Connection, user: user_model.User):
    params = user.model_dump()
    SCRIPT_SQL = """
        UPDATE public.users
            SET username = %(username)s,
                email = %(email)s,
                unit_id = %(unit_id)s,
                access_level = %(access_level)s,
                phone_number = %(phone_number)s,
                password = %(password)s,
                updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    return await conn.exec(SCRIPT_SQL, params)


async def delete_user(conn: Connection, id: UUID):
    params = {'id': id}
    SCRIPT_SQL = """
        DELETE FROM public.users
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)
