import json

def test_stock_search_by_name(client, sample_product):
    # sample_product inserts "Test Product"
    resp = client.get('/stock/search?query=Test')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert any(d['product_name'] == 'Test Product' for d in data)


def test_stock_search_by_id(client, sample_product):
    # sample_product fixture returns product id
    pid = sample_product
    resp = client.get(f'/stock/search?query={pid}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert any(d['id'] == pid for d in data)


def test_stock_search_empty_returns_empty(client):
    resp = client.get('/stock/search?query=')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == []
