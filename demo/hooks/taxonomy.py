import httpx
import streamlit as st
from config import Settings


def get_taxonomy(typification_id):
    response = httpx.get(
        f'{Settings().API}/taxonomy/{typification_id}/', verify=False
    )
    return response.json()


def post_typification(name, sources):
    data = {
        'name': name,
        'source': [s.get('id') for s in sources],
    }
    httpx.post(f'{Settings().API}/typification/', json=data, verify=False)
    st.rerun()


def post_taxonomy(typification_id, title, description, selected_sources):
    data = {
        'typification_id': typification_id,
        'title': title,
        'description': description,
        'source': selected_sources,
    }
    httpx.post(f'{Settings().API}/taxonomy/', json=data, verify=False)
    st.rerun()


def delete_taxonomy(taxonomy_id):
    httpx.delete(f'{Settings().API}/taxonomy/{taxonomy_id}/', verify=False)
    st.rerun()


def delete_branch(branch_id):
    httpx.delete(
        f'{Settings().API}/taxonomy/branch/{branch_id}/', verify=False
    )
    st.rerun()


def delete_typification(typification_id):
    httpx.delete(
        f'{Settings().API}/typification/{typification_id}/', verify=False
    )
    st.rerun()


def put_taxonomy(taxonomy):
    httpx.put(f'{Settings().API}/taxonomy/', json=taxonomy, verify=False)
    st.rerun()


def put_typification(typ):
    httpx.put(f'{Settings().API}/typification/', json=typ, verify=False)
    st.rerun()


def put_branch(branch):
    httpx.put(f'{Settings().API}/taxonomy/branch/', json=branch, verify=False)
    st.rerun()


def get_branches(taxonomy_id) -> dict:
    URL = f'{Settings().API}/taxonomy/branch/{taxonomy_id}/'
    response = httpx.get(URL, verify=False)
    return response.json()


def post_branch(taxonomy_id, title, description):
    data = {
        'title': title,
        'description': description,
        'taxonomy_id': taxonomy_id,
    }
    httpx.post(f'{Settings().API}/taxonomy/branch/', json=data, verify=False)
    st.rerun()


def get_typifications():
    response = httpx.get(f'{Settings().API}/typification/', verify=False)
    return response.json()
