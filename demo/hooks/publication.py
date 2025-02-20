import httpx
import streamlit as st


def post_order(name, typification):
    typification = [t["id"] for t in typification]
    data = {"name": name, "typification": typification}
    httpx.post("http://localhost:8000/order/", json=data)
    st.rerun()


def get_order():
    response = httpx.get("http://localhost:8000/order/")
    return response.json()


def delete_order(order_id):
    httpx.delete(f"http://localhost:8000/order/{order_id}/")
    st.rerun()


def get_detailed_order(order_id):
    response = httpx.get(f"http://localhost:8000/order/{order_id}/")
    return response.json()


def get_release(order_id):
    print(f"http://localhost:8000/order/{order_id}/release/")
    response = httpx.get(f"http://localhost:8000/order/{order_id}/release/")
    return response.json()


def post_release(uploaded_file, order_id):
    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
    httpx.post(f'http://localhost:8000/order/{order_id}/release/', files=files, timeout=2000)  # fmt: skip
    st.rerun()


def delete_release(release_id):
    httpx.delete(f"http://localhost:8000/order/release/{release_id}/")
    st.rerun()
