import httpx


class APITask:
    def __init__(self, owner, title, task_id, task_name, **task_kwargs):
        self.owner = owner
        self.title = title
        self.task_id = task_id
        self.task_name = task_name
        self.task_kwargs = task_kwargs

    async def create(self, asynchronous=False):
        method = "async" if asynchronous else "sync"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://{self.owner}-{self.title}/{method}/{self.task_name}/",
                # f"http://localhost:8888/{method}/{self.task_name}/",
                json={"task_id": self.task_id, "task_kwargs": self.task_kwargs},
            )
        return resp
