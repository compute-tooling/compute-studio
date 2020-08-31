import binascii
import os

try:
    import jwt
    import cs_crypt
except ImportError:
    jwt = None
    cs_crypt = None
    cryptkeeper = None

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


def get_cyptkeeper():
    if cs_crypt is None:
        return None
    else:
        try:
            return cs_crypt.CryptKeeper()
        except cs_crypt.EncryptionUnavailable:
            return None


cryptkeeper = get_cryptkeeper()


class UserNotFound(Exception):
    pass


class UserExists(Exception):
    pass


class User:
    def __init__(
        self, username=None, email=None, url=None, jwt_secret=None, approved=None
    ):
        self.username = username
        self.email = email
        self.url = url
        self.jwt_secret = jwt_secret
        self.approved = int(approved)

    @property
    def fields(self):
        return ["username", "email", "url", "approved"]

    def items(self, include_jwt_secret=False):
        fields = list(self.fields)
        if include_jwt_secret:
            fields += ["jwt_secret"]
        for field in fields:
            yield field, getattr(self, field)
        return

    def dump(self, include_jwt_secret=False):
        values = {}
        for field, value in self.items(include_jwt_secret=include_jwt_secret):
            if field == "jwt_secret":
                values[field] = cryptkeeper.decrypt(value)
            else:
                values[field] = value
        return values

    def save(self, **kwargs):
        if kwargs.keys() - set(self.fields):
            raise ValueError(f"Unknown fields: {','.join(list(kwargs.keys()))}")
        with redis.Redis(**redis_conn) as rclient:
            for field, value in self.items(include_jwt_secret=True):
                if field in kwargs:
                    value = kwargs[field]
                    setattr(self, field, value)
                if isinstance(value, bool):
                    value = int(value)
                rclient.hset(f"users-{self.username}", field, value)
        return self

    def delete(self):
        with redis.Redis(**redis_conn) as rclient:
            user_res = rclient.delete(f"users-{self.username}")
        return bool(user_res)

    def __eq__(self, oth):
        for field in self.fields:
            if getattr(self, field) != getattr(oth, field):
                return False
        return True

    def get_jwt_token(self):
        return jwt.encode(self.dump(), cryptkeeper.decrypt(self.jwt_secret))

    def read_jwt_token(self, jwt_token):
        return jwt.decode(jwt_token, cryptkeeper.decrypt(self.jwt_secret))

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
    def get(username):
        if username is None:
            raise UserNotFound()

        with redis.Redis(**redis_conn) as rclient:
            values = rclient.hgetall(f"users-{username}")
            if not values:
                raise UserNotFound()
            return User._load_values(values)

    @staticmethod
    def create(username, email, url, approved):
        try:
            User.get(username=username)
            raise UserExists()
        except UserNotFound:
            pass
        jwt_secret = binascii.hexlify(os.urandom(32)).decode()
        encrypted = cryptkeeper.encrypt(jwt_secret)
        user = User(username, email, url, encrypted, approved)
        return user.save()


def authenticate_request(request):
    jwt_token = request.headers.get("Authorization")
    cluster_user = request.headers.get("Cluster-User")
    if jwt_token is None or cluster_user is None:
        return None

    try:
        user = User.get(cluster_user)
    except UserNotFound:
        return None

    try:
        user.read_jwt_token(jwt_token)
    except Exception:
        import traceback

        traceback.print_exc()
        return None

    return user


class AuthApi(tornado.web.RequestHandler):
    def prepare(self):
        self.user = authenticate_request(self.request)

    def get(self):
        print("GET -- /auth/")
        if self.user is None:
            raise tornado.web.HTTPError(403)
        self.set_status(200)
        self.write(self.user.dump())

    def post(self):
        print("POST -- /auth")
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
        self.write(user.dump(include_jwt_secret=True))

    def delete(self):
        print("DELETE -- /auth/")
        if self.user is None:
            raise tornado.web.HTTPError(403)
        self.user.delete()
        self.set_status(204)
