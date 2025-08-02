"""A Crossplane composition function."""

import asyncio
import base64
import inspect

import grpc
import crossplane.function.logging
import crossplane.function.response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
import function.composite
import function.protobuf


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.logger = crossplane.function.logging.get_logger()
        self.modules = {}

    async def RunFunction(
        self, request: fnv1.RunFunctionRequest, _: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        composite = request.observed.composite.resource
        logger = self.logger.bind(
            apiVersion=composite['apiVersion'],
            kind=composite['kind'],
            name=composite['metadata']['name'],
        )
        if request.meta.tag:
            logger = logger.bind(tag=request.meta.tag[:7])
        input = request.input
        if 'step' in input:
            logger = logger.bind(step=input['step'])
        logger.debug('Running')

        response = crossplane.function.response.to(request)

        if composite['apiVersion'] == 'pythonic.fortra.com/v1alpha1' and composite['kind'] == 'Composite':
            if 'composite' not in composite['spec']:
                logger.error('Missing spec "composite"')
                crossplane.function.response.fatal(response, 'Missing spec "composite"')
                return response
            composite = composite['spec']['composite']
        else:
            if 'composite' not in input:
                logger.error('Missing input "composite"')
                crossplane.function.response.fatal(response, 'Missing input "composite"')
                return response
            composite = input['composite']

        module = self.modules.get(composite)
        if not module:
            module = Module()
            try:
                exec(composite, module.__dict__)
            except Exception as e:
                crossplane.function.response.fatal(response, f"Exec exception: {e}")
                logger.exception('Exec exception')
                return response
            if not hasattr(module, 'Composite') or not inspect.isclass(module.Composite):
                crossplane.function.response.fatal(response, 'Function did not define "class Composite')
                logger.error('Composite did not define "class Composite"')
                return response
            self.modules[composite] = module

        try:
            composite = module.Composite(request, response, logger)
        except Exception as e:
            crossplane.function.response.fatal(response, f"Instatiate exception: {e}")
            logger.exception('Instatiate exception')
            return response

        try:
            result = composite.compose()
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            crossplane.function.response.fatal(response, f"Compose exception: {e}")
            logger.exception('Compose exception')
            return response

        for name, resource in [entry for entry in composite.resources]:
            if resource.desired._hasUnknowns:
                if resource.observed:
                    resource.desired._patchUnknowns(resource.observed)
                else:
                    del composite.resources[name]

        if composite.autoReady:
            for name, resource in composite.resources:
                if resource.ready is None:
                    if resource.conditions.Ready.status:
                        resource.ready = True

        logger.debug('Returning')
        return response



class Module:
    def __init__(self):
        self.BaseComposite = function.composite.BaseComposite
        self.Map = function.protobuf.Map
        self.List = function.protobuf.List
        self.Yaml = function.protobuf.Yaml
        self.Json = function.protobuf.Json
        self.B64Encode = lambda s: base64.b64encode(s.encode('utf-8')).decode('utf-8')
        self.B64Decode = lambda s: base64.b64decode(s.encode('utf-8')).decode('utf-8')
