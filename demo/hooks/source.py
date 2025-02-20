import httpx
import streamlit as st


def get_source():
    result = httpx.get("http://localhost:8000/source/")
    return result.json()


def get_source_file(source_id):
    result = httpx.get(f"http://localhost:8000/source/{source_id}/")
    return result.content


def post_source(name, description, uploaded_file):
    data = {"name": name, "description": description}
    headers = {"accept": "application/json"}
    if not uploaded_file:
        httpx.post("http://127.0.0.1:8000/source/", headers=headers, data=data)
    else:
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        httpx.post(
            "http://127.0.0.1:8000/source/",
            headers=headers,
            files=files,
            data=data,
        )
    st.rerun()


def delete_source(source_id):
    httpx.delete(f"http://localhost:8000/source/{source_id}/")
    st.rerun()
