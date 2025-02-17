import httpx
import streamlit as st


def get_taxonomy(typification_id):
    response = httpx.get(f'http://localhost:8000/taxonomy/{typification_id}/')
    return response.json()


def post_typification(name, sources):
    data = {
        'name': name,
        'source': [s.get('id') for s in sources],
    }
    httpx.post('http://localhost:8000/typification/', json=data)
    st.rerun()


def post_taxonomy(typification_id, title, description, selected_sources):
    data = {
        'typification_id': typification_id,
        'title': title,
        'description': description,
        'source': selected_sources,
    }
    httpx.post('http://localhost:8000/taxonomy/', json=data)
    st.rerun()


def delete_taxonomy(taxonomy_id):
    httpx.delete(f'http://localhost:8000/taxonomy/{taxonomy_id}/')
    st.rerun()


def delete_branch(branch_id):
    httpx.delete(f'http://localhost:8000/taxonomy/branch/{branch_id}/')
    st.rerun()


def delete_typification(typification_id):
    httpx.delete(f'http://localhost:8000/typification/{typification_id}/')
    st.rerun()


def put_taxonomy(taxonomy):
    httpx.put('http://localhost:8000/taxonomy/', json=taxonomy)
    st.rerun()


def put_typification(typ):
    httpx.put('http://localhost:8000/typification/', json=typ)
    st.rerun()


def put_branch(branch):
    httpx.put('http://localhost:8000/taxonomy/branch/', json=branch)
    st.rerun()


def get_branches_by_taxonomy_id(taxonomy_id) -> dict:
    URL = f'http://localhost:8000/taxonomy/branch/{taxonomy_id}/'
    response = httpx.get(URL)
    return response.json()


def post_branch(taxonomy_id, title, description):
    data = {
        'title': title,
        'description': description,
        'taxonomy_id': taxonomy_id,
    }
    httpx.post('http://localhost:8000/taxonomy/branch/', json=data)
    st.rerun()


def get_typifications():
    response = httpx.get('http://localhost:8000/typification/')
    return response.json()
