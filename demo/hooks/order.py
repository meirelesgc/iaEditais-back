import httpx
import streamlit as st


def post_order(name, type):
    data = {'name': name}
    httpx.post('http://localhost:8000/order/', json=data)
    st.rerun()


def get_order():
    response = httpx.get('http://localhost:8000/order/')
    return response.json()


def get_detailed_order(order_id):
    response = httpx.get(f'http://localhost:8000/order/{order_id}/')
    return response.json()


def post_release(uploaded_file, order_id, taxonomies):
    taxonomies = [tax['id'] for tax in taxonomies]
    data = {'order_id': order_id, 'taxonomies': taxonomies}
    files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
    httpx.post('http://localhost:8000/order/release/', files=files, data=data, timeout=2000)  # fmt: skip
    st.rerun()


def delete_release(order_id):
    response = httpx.delete(f'http://localhost:8000/order/release/{order_id}/')
    return response.json()
