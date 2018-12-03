import os

from django.core.files.uploadedfile import SimpleUploadedFile

from webapp.apps.core.tests.test_views import CoreAbstractViewsTest
from webapp.apps.core.tests.compute import MockCompute
from webapp.apps.projects.upload.models import FileOutput

def outputs_ok():
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, 'outputs_ok.json'), 'r') as f:
        outputs = f.read()
    return outputs

class UploadMockCompute(MockCompute):
    outputs = outputs_ok()

class TestUpload(CoreAbstractViewsTest):
    """
    Inherits test cases and functionality from CoreAbstractViewsTest
    """
    app_name = 'upload'
    mockcompute = UploadMockCompute
    RunModel = FileOutput

    def inputs_ok(self):
        return {
            'datafile': SimpleUploadedFile(
                'data.csv',
                b'a,b,c\n,1,2,3\n1,2,3',
            )
        }

    def outputs_ok(self):
        return outputs_ok()


def write_outputs_ok():
    import pandas as pd
    import io
    import json
    df = pd.read_csv(io.BytesIO(b'a,b,c\n,1,2,3\n1,2,3'))
    desc = df.describe()

    formatted = {'outputs': [], 'aggr_outputs': [], 'meta':{}}
    formatted['aggr_outputs'].append({
        'tags': {'default': 'default'},
        'title': 'desc',
        'downloadable': [{'filename': 'desc' + '.csv',
                            'text': desc.to_csv()}],
        'renderable': desc.to_html()})
    formatted['meta'] = {'job_times': [4, ]}
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, 'outputs_ok.json'), 'w') as f:
        f.write(json.dumps(formatted))