from datetime import datetime

import marshmallow as ma


class Payload(ma.Schema):
    task_id = ma.fields.UUID(required=False)
    task_name = ma.fields.Str(required=True)
    task_kwargs = ma.fields.Dict(
        keys=ma.fields.Str(), values=ma.fields.Field(), missing=dict
    )
    tag = ma.fields.Str(required=False, allow_none=True)


class Deployment(ma.Schema):
    tag = ma.fields.Str(required=True)
    deployment_name = ma.fields.Str(required=True)


class UserSerializer(ma.Schema):
    username = ma.fields.Str(validate=ma.validate.Length(min=2, max=20))
    email = ma.fields.Email()
    url = ma.fields.URL()
    hashed_token = ma.fields.Str(required=False)
    approved = ma.fields.Bool(default=False)
