
import warnings
warnings.filterwarnings('ignore', module='^google[.]protobuf[.]runtime_version$', lineno=98)

import pathlib
import pytest
import yaml
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from google.protobuf import json_format

from function import fn
from tests import utils


@pytest.mark.parametrize(
    'fn_case',
    [
        path
        for path in (pathlib.Path(__file__).parent / 'fn_cases').iterdir()
        if path.is_file() and path.suffix == '.yaml'
    ],
)
@pytest.mark.asyncio
async def test_run_function(fn_case):
    test = yaml.safe_load(fn_case.read_text())

    request = fnv1.RunFunctionRequest(
        observed=fnv1.State(
            composite=fnv1.Resource(
                resource={
                    'apiVersion': 'pythonic.fortra.com/v1alpha1',
                    'kind': 'PyTest',
                    'metadata': {
                        'name': fn_case.stem,
                    },
                },
            ),
        ),
    )
    utils.message_merge(request, test['request'])
    utils.map_defaults(test['response'], {
        'meta': {
            'ttl': {
                'seconds': 60,
            },
        },
        'context': {}
    })

    response = utils.message_dict(
        await fn.FunctionRunner().RunFunction(request, None)
    )

    #print(yaml.dump(response))
    #assert False

    assert response == test['response']
