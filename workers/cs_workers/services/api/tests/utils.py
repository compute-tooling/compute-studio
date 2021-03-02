def get_access_token(test_client, user):
    resp = test_client.post(
        "/api/v1/login/access-token",
        data={"username": "test", "password": "heyhey2222"},
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    return resp.json()["access_token"]
