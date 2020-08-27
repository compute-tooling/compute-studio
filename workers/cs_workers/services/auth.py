import binascii
import os

import marshmallow as ma
import redis
import tornado.web


from cs_workers.utils import redis_conn_from_env
from cs_workers.services.serializers import UserSerializer

redis_conn = dict(
    username="scheduler",
    password=os.environ.get("REDIS_SCHEDULER_PW"),
    **redis_conn_from_env(),
)


class UserNotFound(Exception):
    pass


class UserExists(Exception):
    pass


class User:
    def __init__(self, username=None, email=None, url=None, token=None, approved=None):
        self.username = username
        self.email = email
        self.url = url
        self.token = token
        self.approved = int(approved)

    @property
    def fields(self):
        return ["username", "email", "url", "token", "approved"]

    def items(self):
        for field in self.fields:
            yield field, getattr(self, field)
        return

    def dump(self):
        return {field: value for field, value in self.items()}

    def save(self, **kwargs):
        if kwargs.keys() - set(self.fields):
            raise ValueError(f"Unknown fields: {','.join(list(kwargs.keys()))}")
        with redis.Redis(**redis_conn) as rclient:
            rclient.set(f"users-tokens-{self.token}", self.username)
            for field, value in self.items():
                if field in kwargs:
                    value = kwargs[field]
                    setattr(self, field, value)
                if isinstance(value, bool):
                    value = int(value)
                rclient.hset(f"users-{self.username}", field, value)
        return self

    def delete(self):
        with redis.Redis(**redis_conn) as rclient:
            token_res = rclient.delete(f"users-tokens-{self.token}")
            user_res = rclient.delete(f"users-{self.username}")
        return token_res and user_res

    def __eq__(self, oth):
        for field in self.fields:
            if getattr(self, field) != getattr(oth, field):
                return False
        return True

    @staticmethod
    def _load_values(values):
        result = {}
        for field, value in values.items():
            field = field.decode()
            value = value.decode()
            if field == "approved":
                value = True if value == "1" else False
            result[field] = value
        return User(**result)

    @staticmethod
    def get(username=None, token=None):
        if username is None and token is None:
            raise UserNotFound()
        if username is not None:
            with redis.Redis(**redis_conn) as rclient:
                values = rclient.hgetall(f"users-{username}")
                if not values:
                    raise UserNotFound()
                user = User._load_values(values)

        elif token is not None:
            with redis.Redis(**redis_conn) as rclient:
                username = rclient.get(f"users-tokens-{token}")
                if username is None:
                    raise UserNotFound()
                values = rclient.hgetall(f"users-{username.decode()}")
                if not values:
                    raise UserNotFound()
                user = User._load_values(values)

        return user

    @staticmethod
    def create(username, email, url, approved):
        try:
            User.get(username=username)
            raise UserExists()
        except UserNotFound:
            pass
        token = binascii.hexlify(os.urandom(32)).decode()
        user = User(username, email, url, token, approved)
        return user.save()


def authenticate_request(request):
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return None
    token = auth_header.split(" ")
    if len(token) != 2:
        return None

    try:
        return User.get(token=token[1])
    except UserNotFound:
        pass

    return None


class AuthApi(tornado.web.RequestHandler):
    def prepare(self):
        self.user = authenticate_request(self.request)

    def get(self):
        if self.user is None:
            raise tornado.web.HTTPError(403)
        self.set_status(200)
        self.write(self.user.dump())

    def post(self):
        try:
            data = UserSerializer().loads(self.request.body.decode("utf-8"))
        except ma.ValidationError as ve:
            self.write(ve.messages)
            self.set_status(400)
            return

        try:
            user = User.create(**data, approved=False)
        except UserExists:
            self.set_status(400)
            self.write({"errors": ["User with username exists."]})
            return

        self.set_status(200)
        self.write(user.dump())

    def delete(self):
        if self.user is None:
            raise tornado.web.HTTPError(403)
        self.user.delete()
        self.set_status(204)
