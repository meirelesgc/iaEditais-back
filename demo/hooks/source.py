import httpx
import streamlit as st

from config import Settings


def get_source():
    print(f'{Settings().API}/source/')
    result = httpx.get(f'{Settings().API}/source/')
    return result.json()


def get_source_file(source_id):
    result = httpx.get(f'{Settings().API}/source/{source_id}/')
    return result.content


def post_source(name, description, uploaded_file):
    data = {'name': name, 'description': description}
    headers = {'accept': 'application/json'}
    if not uploaded_file:
        httpx.post(f'{Settings().API}/source/', headers=headers, data=data)
    else:
        files = {
            'file': (uploaded_file.name, uploaded_file, 'application/pdf')
        }
        httpx.post(
            f'{Settings().API}/source/',
            headers=headers,
            files=files,
            data=data,
        )
    st.rerun()


def delete_source(source_id):
    httpx.delete(f'{Settings().API}/source/{source_id}/')
    st.rerun()
