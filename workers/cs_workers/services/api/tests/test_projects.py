from .utils import get_access_token
from ..settings import settings
from ..models import Project


class TestProjects:
    def test_sync_projects(self, db, client, user):
        access_token = get_access_token(client, user)
        assert access_token
        data = {
            "owner": "test",
            "title": "test-app",
            "tech": "bokeh",
            "callable_name": "hello",
            "exp_task_time": 10,
            "cpu": 4,
            "memory": 10,
        }

        resp = client.post(
            f"{settings.API_PREFIX_STR}/projects/sync/",
            json=[data],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()
        assert (
            db.query(Project)
            .filter(Project.owner == "test", Project.title == "test-app")
            .one()
        )

        resp = client.post(
            f"{settings.API_PREFIX_STR}/projects/sync/",
            json=[data],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()
        assert (
            db.query(Project)
            .filter(Project.owner == "test", Project.title == "test-app")
            .one()
        )

        resp = client.post(
            f"{settings.API_PREFIX_STR}/projects/sync/",
            json=[dict(data, title="test-app-another")],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()
        assert (
            db.query(Project)
            .filter(Project.owner == "test", Project.title == "test-app-another")
            .one()
        )
        assert db.query(Project).count() == 2

    def test_get_projects(self, db, client, user):
        access_token = get_access_token(client, user)
        assert access_token
        data = {
            "owner": "test",
            "title": "test-app",
            "tech": "bokeh",
            "callable_name": "hello",
            "exp_task_time": 10,
            "cpu": 4,
            "memory": 10,
        }
        for i in range(3):
            resp = client.post(
                f"{settings.API_PREFIX_STR}/projects/sync/",
                json=[dict(data, title=f"new-app-{i}")],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert resp.status_code == 200

        resp = client.get(
            f"{settings.API_PREFIX_STR}/projects/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == db.query(Project).count() == 3
