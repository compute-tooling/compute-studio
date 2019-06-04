# Authentication

API endpoints that create simulations require the user to include their API Token with their request. Here a few methods for retrieving your authentication token:


### [COMP-Developer-ToolKit][1]

```bash
$ pip install compdevkit
$ cdk-token --username myuser --password mypass
Token: your-token-here
```

### [HTTPie][2]

```bash
$ http post https://www.compmodels.org/api-token-auth/ username=hdoupe password=mypass

HTTP/1.1 200 OK
Allow: POST, OPTIONS

{
    "token": "Your token here"
}
```

### [Python with the Requests library][3]

```python
In [1]: import requests                                                                                                       

In [2]: resp = requests.post("https://www.compmodels.org/api-token-auth/", json={"username": "hdoupe", "password": "mypass"})  

In [3]: resp.json()                                                                                                           
Out[3]: {'token': 'Your token here'}
```


[1]: https://github.com/comp-org/COMP-Developer-Toolkit#comp-developer-toolkit
[2]: https://httpie.org/
[3]: https://2.python-requests.org/en/master/