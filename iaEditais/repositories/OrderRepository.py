from iaEditais.schemas.Order import Order, Release
import json
from psycopg.types.json import Jsonb
from uuid import UUID
from iaEditais.repositories import conn


def post_order(order: Order) -> None:
    params = order.model_dump()
    SCRIPT_SQL = """
        INSERT INTO orders (id, name, created_at, updated_at) 
        VALUES (%(id)s, %(name)s, %(created_at)s, %(updated_at)s);
        """
    conn().exec(SCRIPT_SQL, params)


def get_order(order_id: UUID = None) -> list[Order]:
    one = False
    params = {}

    filter_id = str()
    if order_id:
        one = True
        params['id'] = order_id
        filter_id = 'AND id = %(id)s'

    SCRIPT_SQL = f"""
        SELECT id, name, created_at, updated_at
        FROM orders
        WHERE 1 = 1
            {filter_id};
        """
    results = conn().select(SCRIPT_SQL, params, one)
    return results


def get_releases(
    order_id: UUID = None, release_id: UUID = None
) -> list[Release] | Release:
    one = False
    params = {}
    filter_id = str()

    if order_id:
        params = {'order_id': order_id}
        filter_id = 'AND order_id = %(order_id)s'

    if release_id:
        one = True
        params = {'release_id': release_id}
        filter_id = 'AND id = %(release_id)s'

    SCRIPT_SQL = f"""
        SELECT id, order_id, taxonomies, taxonomy, created_at
        FROM releases
        WHERE 1 = 1
            {filter_id}
        """
    results = conn().select(SCRIPT_SQL, params, one)
    return results


def delete_order(order_id: UUID):
    params = {'id': order_id}
    SCRIPT_SQL = """
        DELETE FROM orders 
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)


def post_release(release: Release):
    params = release.model_dump()
    params['taxonomy'] = json.dumps(release.taxonomy, default=str)
    params['taxonomy'] = Jsonb(json.loads(params['taxonomy']))

    params['taxonomy_score'] = json.dumps(release.taxonomy, default=str)
    params['taxonomy_score'] = Jsonb(json.loads(params['taxonomy_score']))

    SCRIPT_SQL = """
        INSERT INTO releases (id, order_id, taxonomies, taxonomy, taxonomy_score, created_at)
        VALUES (%(id)s, %(order_id)s, %(taxonomies)s, %(taxonomy)s, %(taxonomy_score)s, %(created_at)s);
        """

    conn().exec(SCRIPT_SQL, params)
