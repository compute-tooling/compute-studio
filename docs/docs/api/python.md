# Python

The COMP REST API can easily be wrapped with a [Python class](#api-implementation) to provide a more intuitive way to use the API:

[How do I get my auth token?](/api/auth/)

```python
api = API("PSLmodels", "Tax-Brain", api_token="your token")

res = api.create(
    meta_parameters={
        "data_source": "PUF",
        "year": 2020,
    },
    adjustment={
        "policy": {
            "II_em": [{"year": 2020, "value": 5000}]
        }
    }
)

# output: 
# {'inputs': {'meta_parameters': {'year': 2020,
#    'data_source': 'PUF',
#    'use_full_sample': True},
#   'adjustment': {'policy': {'II_em': [{'year': 2020, 'value': 5000}]},
#    'behavior': {}},
#   'inputs_file': {'policy': {'II_em': {'2020': 5000}}, 'behavior': {}},
#   'errors_warnings': {'policy': {'errors': {}, 'warnings': {}},
#    'behavior': {'errors': {}, 'warnings': {}},
#    'GUI': {'errors': {}, 'warnings': {}},
#    'API': {'errors': {}, 'warnings': {}}}},
#  'outputs': None,
#  'traceback': None,
#  'creation_date': '2019-06-04T17:30:23.581357-05:00',
#  'api_url': '/PSLmodels/Tax-Brain/api/v1/41105/',
#  'gui_url': '/PSLmodels/Tax-Brain/41105/',
#  'eta': 5.0,
#  'model_pk': 41105}
 
```

Retrieve the result as a Pandas DataFrame:

```python
result = api.results(res["model_pk"])

result["Total Liabilities Change by Calendar Year (Billions).csv"]


# output:
# Unnamed: 0 	2020 	2021 	2022 	2023 	2024 	2025 	2026 	2027 	2028 	2029
# 0 	Individual Income Tax Liability Change 	$-168.49 	$-175.45 	$-183.43 	$-190.69 	$-198.26 	$-207.17 	$-32.96 	$-34.10 	$-35.26 	$-36.46
# 1 	Payroll Tax Liability Change 	$0.00 	$0.00 	$0.00 	$0.00 	$0.00 	$0.00 	$0.00 	$0.00 	$0.00 	$0.00
# 2 	Combined Payroll and Individual Income Tax Lia... 	$-168.49 	$-175.45 	$-183.43 	$-190.69 	$-198.26 	$-207.17 	$-32.96 	$-34.10 	$-35.26 	$-36.46

```

View the model's inputs:

```python
api.inputs()

# output:
# {'meta_parameters': {'year': {'validators': {'choice': {'choices': [2013,
#       2014,
#       2015,
#       2016,
#       2017,
#       2018,
#       2019,
#       2020,
#       2021,
#       2022,
#       2023,
#       2024,
#       2025,
#       2026,
#       2027,
#       2028]}},
#    'description': 'Year for parameters.',
#    'title': 'Start Year',
#    'number_dims': 0,
#    'type': 'int',
#    'value': [{'value': 2019}]},
#   'data_source': {'validators': {'choice': {'choices': ['PUF', 'CPS']}},
#    'description': 'Data source can be PUF or CPS',
#    'title': 'Data Source',
#    'number_dims': 0,
#    'type': 'str',
#    'value': [{'value': 'PUF'}]},
#   'use_full_sample': {'validators': {'choice': {'choices': [True, False]}},
#    'description': 'Use entire data set or a 2% sample.',
#    'title': 'Use Full Sample',
#    'number_dims': 0,
#    'type': 'bool',
#    'value': [{'value': True}]}},
#  'model_parameters': {'policy': {'CPI_offset': {'validators': {'range': {'min': -0.005,
#       'max': 0.005}},
#     'section_2': 'Offsets',
#     'section_1': 'Parameter Indexing',
#     'description': 'Values are zero before 2017; reforms that introduce indexing with chained CPI would have values around -0.0025 beginning in the year before the first year policy parameters will have values computed with chained CPI.',
#     'title': 'Decimal offset ADDED to unchained CPI to get parameter indexing rate',
#     'number_dims': 0,
#     'notes': "See April 2013 CBO report entitled 'What Would Be the Effect on the Deficit of Using the Chained CPI to Index Benefit Programs and the Tax Code?', which includes this: 'The chained CPI grows more slowly than the traditional CPI does: an average of about 0.25 percentage points more slowly per year over the past decade.' <https://www.cbo.gov/publication/44089>",
#     'type': 'float',
#     'value': [{'year': 2019, 'value': -0.0025}]},
#    'FICA_ss_trt': {'validators': {'range': {'min': 0, 'max': 1}},
#     'section_2': 'Social Security FICA',
#     'section_1': 'Payroll Taxes',
#     'description': 'Social Security FICA rate, including both employer and employee.',
#     'title': 'Social Security payroll tax rate',
#     'number_dims': 0,
#     'notes': '',
#     'type': 'float',
#     'value': [{'year': 2019, 'value': 0.124}]},
#    'SS_Earnings_c': {'validators': {'range': {'min': 0, 'max': 9e+99}},
#     'section_2': 'Social Security FICA',
#     'checkbox': True,
#     'section_1': 'Payroll Taxes',
#     'description': 'Individual earnings below this amount are subjected to Social Security (OASDI) payroll tax.',
#     'title': 'Maximum taxable earnings (MTE) for Social Security',
#     'number_dims': 0,
#     'notes': 'This parameter is indexed by the rate of growth in average wages, not by the price inflation rate.',
#     'type': 'float',
#     'value': [{'year': 2019, 'value': 133048.08}]},
#    'SS_Earnings_thd': {'validators': {'range': {'min': 0, 'max': 9e+99}},
#     'section_2': 'Social Security FICA',
#     'checkbox': False,
#     'section_1': 'Payroll Taxes',
#     'description': 'Individual earnings above this threshold are subjected to Social Security (OASDI) payroll tax, in addition to earnings below the maximum taxable earnings threshold.',
#     'title': 'Additional Taxable Earnings Threshold for Social Security',
#     'number_dims': 0,
#     'notes': '',
#     'type': 'float',
#     'value': [{'year': 2019, 'value': 9e+99}]},
#
#   ...
```

## API implementation:

```python
from io import StringIO
import time
import os

import requests
import pandas as pd


class APIException(Exception):
    pass

class API:
    host = "https://www.compmodels.org"

    def __init__(self, owner, title, api_token=None):
        self.owner = owner
        self.title = title
        api_token = self.get_token(api_token)
        self.auth_header = {
            "Authorization": f"Token {api_token}"
        }
        self.sim_url = f"{self.host}/{owner}/{title}/api/v1/"
        self.inputs_url = f"{self.host}/{owner}/{title}/api/v1/inputs/"

    def inputs(self, meta_parameters: dict = None):
        meta_parameters = meta_parameters or {}
        if not meta_parameters:
            resp = requests.get(self.inputs_url)
        else:
            resp = requests.post(
                self.inputs_url,
                json=meta_parameters,
            )
        if resp.status_code == 200:
            return resp.json()
        raise APIException(resp.text)

    def create(self, adjustment: dict = None, meta_parameters: dict = None):
        adjustment = adjustment or {}
        meta_parameters = meta_parameters or {}
        resp = requests.post(
            self.sim_url,
            json={
                "adjustment": adjustment, 
                "meta_parameters": meta_parameters
            },
            headers=self.auth_header
        )
        if resp.status_code == 201:
            return resp.json()
        raise APIException(resp.text)

    def detail(self, model_pk):
        while True:
            resp = requests.get(f"{self.sim_url}{model_pk}/")
            if resp.status_code == 202:
                pass
            elif resp.status_code == 200:
                return resp.json()
            else:
                raise APIException(resp.text)
            time.sleep(20)

    def results(self, model_pk):
        result = self.detail(model_pk)
        res = {}
        for output in result["outputs"]["downloadable"]:
            if output["media_type"] == "CSV":
                res[output["title"]] = pd.read_csv(
                    StringIO(output["data"])
                )
            else:
                print(f'{output["media_type"]} not implemented yet')
        return res

    def get_token(self, api_token):
        if api_token:
            return api_token
        elif os.environ.get("COMP_API_TOKEN", None) is not None:
            return os.environ["COMP_API_TOKEN"]
        elif os.path.exists("~/.comp-api-token"):
            with open("~/.comp-api-token", "r") as f:
                return f.read().strip()
        else:
            raise APIException(
                "API token not found. It can be passed as an argument to "
                "this class, as an environment variable, or read from "
                "~/.comp-api-token"
            )
```
