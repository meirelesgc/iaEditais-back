import httpx
import streamlit as st
from config import Settings


def post_order(name, typification):
    typification = [t['id'] for t in typification]
    data = {'name': name, 'typification': typification}
    httpx.post(f'{Settings().API}/order/', json=data)
    st.rerun()


def get_order():
    response = httpx.get(f'{Settings().API}/order/')
    return response.json()


def delete_order(order_id):
    httpx.delete(f'{Settings().API}/order/{order_id}/')
    st.rerun()


def get_detailed_order(order_id):
    response = httpx.get(f'{Settings().API}/order/{order_id}/')
    return response.json()


def get_release(order_id):
    response = httpx.get(f'{Settings().API}/order/{order_id}/release/')
    return response.json()


def post_release(uploaded_file, order_id):
    files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
    httpx.post(f'{Settings().API}/order/{order_id}/release/', files=files, timeout=2000)  # fmt: skip
    st.rerun()


def delete_release(release_id):
    httpx.delete(f'{Settings().API}/order/release/{release_id}/')
    st.rerun()
