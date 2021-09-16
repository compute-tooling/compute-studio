import base64
import os
import re
import subprocess
import time

import httpx


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def run(cmd):
    print(f"Running: {cmd}\n")
    s = time.time()
    res = subprocess.run(cmd, shell=True, check=True)
    f = time.time()
    print(f"\n\tFinished in {f-s} seconds.\n")
    return res


def parse_owner_title(owner_title):
    if isinstance(owner_title, tuple) and len(owner_title) == 2:
        owner, title = owner_title
    else:
        owner, title = owner_title.split("/")
    return (owner, title)


def read_github_file(org, repo, branch, filename):
    """
    Read data from github api. Ht to @andersonfrailey for decoding the response
    """
    url = f"https://api.github.com/repos/{org}/{repo}/contents/{filename}?ref={branch}"
    response = httpx.get(url)
    if response.status_code == 403:
        assert "hit rate limit" == 403
    if response.status_code == 404:
        raise FileNotFoundError()
    assert response.status_code == 200, f"Got code: {response.status_code}"
    sanatized_content = response.json()["content"].replace("\n", "")
    encoded_content = sanatized_content.encode()
    decoded_bytes = base64.decodebytes(encoded_content)
    text = decoded_bytes.decode()
    return text


def redis_conn_from_env():
    kwargs = {}
    for kwarg, env in [
        ("host", "REDIS_HOST"),
        ("port", "REDIS_PORT"),
        ("db", "REDIS_DB"),
    ]:
        val = os.environ.get(env)
        if val:
            kwargs[kwarg] = val

    return kwargs


def get_projects(cs_url, api_token=None, auth_headers=None, max_retries=5):
    tries = 0
    while True:
        try:
            return _get_projects(
                cs_url,
                auth_headers={"Authorization": f"Token {api_token}", **auth_headers},
            )
        except Exception as e:
            if tries < max_retries:
                print("Got exception", e)
                print("Sleeping for", 2 ** tries, "seconds")
                time.sleep(2 ** tries)
                tries += 1
            else:
                raise e


def get_cluster_access_token(
    cs_cluster_url, cs_cluster_username, cs_cluster_password, max_retries=5
):
    tries = 0
    while True:
        try:
            resp = httpx.post(
                f"{cs_cluster_url}/api/v1/login/access-token",
                data={
                    "username": cs_cluster_username,
                    "password": cs_cluster_password,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]
        except Exception as e:
            if tries < max_retries:
                print("Got exception retrieving token", e)
                print("Sleeping for", 2 ** tries, "seconds")
                time.sleep(2 ** tries)
                tries += 1
            else:
                raise e


def get_projects_from_cluster(
    cs_cluster_url, cs_cluster_username, cs_cluster_password, max_retries=5
):
    access_token = get_cluster_access_token(
        cs_cluster_url,
        cs_cluster_username,
        cs_cluster_password,
        max_retries=max_retries,
    )
    tries = 0
    while True:
        try:
            return _get_projects(
                cs_cluster_url,
                auth_headers={"Authorization": f"Bearer {access_token}"},
                path="/api/v1/projects/",
            )
        except Exception as e:
            if tries < max_retries:
                print("Got exception", e)
                print("Sleeping for", 2 ** tries, "seconds")
                time.sleep(2 ** tries)
                tries += 1
            else:
                raise e


def _get_projects(cs_url, auth_headers=None, path="/apps/api/v1/"):
    headers = auth_headers or {}
    client = httpx.Client(headers=headers, timeout=5)
    resp = client.get(f"{cs_url}{path}")
    assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
    page = resp.json()

    # BC: Not using pagination yet.
    if isinstance(page, list):
        return hash_projects(page)

    results = page["results"]
    next_url = page["next"]
    while next_url is not None:
        resp = client.get(next_url)
        assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
        page = resp.json()

        results += page["results"]
        next_url = page["next"]

    return hash_projects(results)


def hash_projects(payload):
    projects = {}
    for project in payload:
        projects[f"{project['owner']}/{project['title']}"] = project
    return projects
