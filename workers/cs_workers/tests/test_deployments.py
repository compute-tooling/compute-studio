from datetime import datetime
import time

import httpx

from cs_workers.models.clients.server import Server
from cs_workers.config import ModelConfig


PORT = "8889"
HOST = "localhost"
PROTOCOL = "http"
URL = f"{PROTOCOL}://{HOST}:{PORT}"
PROJECT = "cs-workers-dev"
CS_URL = "https://dev.compute.studio"


def test_create_deployment():
    resp = httpx.post(
        f"{URL}/deployments/hdoupe/ccc-widget/",
        json={"tag": "fix-iframe-link3", "deployment_name": "test"},
    )
    assert resp.status_code == 200, f"Got code: {resp.status_code} {resp.text}"

    now = datetime.now()
    max_wait = 120
    success = False
    while (datetime.now() - now).seconds < max_wait:
        resp = httpx.get(f"{URL}/deployments/hdoupe/ccc-widget/test/")
        assert resp.status_code == 200, f"Got code: {resp.status_code} {resp.text}"

        data = resp.json()
        print(resp, data)
        if (
            data["deployment"]["ready"]
            and data["svc"]["ready"]
            and data["ingressroute"]["ready"]
        ):
            print(data)
            success = True
            break

        time.sleep(1)

    if not success:
        raise Exception(f"Deployment not ready in less than {max_wait} seconds: {data}")

    server = Server(
        project=PROJECT,
        owner="hdoupe",
        title="ccc-widget",
        tag="fix-iframe-link3",
        model_config=ModelConfig(PROJECT, CS_URL),
        callable_name="dash",
        deployment_name="test",
        namespace="default",
        incluster=False,
    )

    assert server.ready_stats() == data

    resp = httpx.delete(f"{URL}/deployments/hdoupe/ccc-widget/test/")
    assert resp.status_code == 200, f"Got code: {resp.status_code} {resp.text}"
    assert resp.json() == {
        "deployment": {"deleted": True},
        "svc": {"deleted": True},
        "ingressroute": {"deleted": True},
    }
