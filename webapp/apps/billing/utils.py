import json
import os


def get_billing_data():
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, 'billing.json')) as f:
        billing = json.loads(f.read())
    return billing
