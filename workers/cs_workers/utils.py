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


def get_projects(cs_url, api_token=None, auth_headers=None):
    if api_token is not None:
        headers = {"Authorization": f"Token {api_token}"}
    elif auth_headers is not None:
        headers = auth_headers
    else:
        headers = {}
    resp = httpx.get(f"{cs_url}/apps/api/v1/", headers=headers)
    assert resp.status_code == 200, f"Got code {resp.status_code}"
    return hash_projects(resp.json())


def hash_projects(payload):
    projects = {}
    for project in payload:
        projects[f"{project['owner']}/{project['title']}"] = project
    return projects
