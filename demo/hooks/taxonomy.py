import httpx


def get_taxonomy(typification_id):
    response = httpx.get(f"http://localhost:8000/taxonomy/{typification_id}/")
    return response.json()


def post_typification(name, sources):
    data = {
        "name": name,
        "source": [s.get("id") for s in sources],
    }
    httpx.post("http://localhost:8000/typification/", json=data)


def post_taxonomy(typification_id, title, description, selected_sources):
    data = {
        "typification_id": typification_id,
        "title": title,
        "description": description,
        "source": selected_sources,
    }
    httpx.post("http://localhost:8000/taxonomy/", json=data)


def delete_taxonomy(taxonomy_id):
    httpx.delete(f"http://localhost:8000/taxonomy/{taxonomy_id}/")


def delete_branch(branch_id):
    httpx.delete(f"http://localhost:8000/taxonomy/branch/{branch_id}/")


def delete_typification(typification_id):
    httpx.delete(f"http://localhost:8000/typification/{typification_id}/")


def put_taxonomy(taxonomy):
    httpx.put("http://localhost:8000/taxonomy/", json=taxonomy)


def put_typification(typ):
    httpx.put("http://localhost:8000/typification/", json=typ)


def put_branch(branch):
    httpx.put("http://localhost:8000/taxonomy/branch/", json=branch)


def get_branches(taxonomy_id) -> dict:
    URL = f"http://localhost:8000/taxonomy/branch/{taxonomy_id}/"
    response = httpx.get(URL)
    return response.json()


def post_branch(taxonomy_id, title, description):
    data = {
        "title": title,
        "description": description,
        "taxonomy_id": taxonomy_id,
    }
    httpx.post("http://localhost:8000/taxonomy/branch/", json=data)


def get_typifications():
    response = httpx.get("http://localhost:8000/typification/")
    return response.json()
