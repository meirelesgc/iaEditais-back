def test_basic_info(client):
    response = client.get('/info')
    data = response.json()
    keys = {
        'name',
        'version',
        'description',
        'authors',
        'license',
        'urls',
    }
    assert keys.issubset(data.keys())
