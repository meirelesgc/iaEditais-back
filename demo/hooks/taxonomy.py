import httpx
import streamlit as st


def get_taxonomy():
    response = httpx.get('http://localhost:8000/taxonomy/')
    return response.json()


def get_detailed_taxonomy(taxonomy_id): ...


def post_taxonomy(title, description, selected_sources):
    data = {
        'title': title,
        'description': description,
        'selected_sources': selected_sources,
    }
    httpx.post('http://localhost:8000/taxonomy/', json=data)
    st.rerun()


def delete_taxonomy(taxonomy_id):
    httpx.delete(f'http://localhost:8000/taxonomy/{taxonomy_id}/')
    st.rerun()


def put_taxonomy(taxonomy):
    httpx.put('http://localhost:8000/taxonomy/', json=taxonomy)
    st.rerun()


def get_branches_by_taxonomy_id(taxonomy_id):
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
