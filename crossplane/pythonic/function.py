"""A Crossplane composition function."""

import asyncio
import base64
import builtins
import importlib
import inspect

import grpc
import crossplane.function.logging
import crossplane.function.response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from .. import pythonic

builtins.BaseComposite = pythonic.BaseComposite
builtins.Map = pythonic.Map
builtins.List = pythonic.List
builtins.Unknown = pythonic.Unknown
builtins.Yaml = pythonic.Yaml
builtins.Json = pythonic.Json
builtins.B64Encode = pythonic.B64Encode
builtins.B64Decode = pythonic.B64Decode


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.logger = crossplane.function.logging.get_logger()
        self.clazzes = {}

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

        clazz = self.clazzes.get(composite)
        if not clazz:
            if '\n' in composite:
                module = Module()
                try:
                    exec(composite, module.__dict__)
                except Exception as e:
                    crossplane.function.response.fatal(response, f"Exec exception: {e}")
                    logger.exception('Exec exception')
                    return response
                composite = ['<script>', 'Composite']
            else:
                composite = composite.rsplit('.', 1)
                if len(composite) == 1:
                    crossplane.function.response.fatal(response, f"Composite class name does not include module: {composite[0]}")
                    logger.error(f"Composite class name does not include module: {composite[0]}")
                    return response
                try:
                    module = importlib.import_module(composite[0])
                except Exception as e:
                    crossplane.function.response.fatal(response, f"Import module exception: {e}")
                    logger.exception('Import module exception')
                    return response
            clazz = getattr(module, composite[1], None)
            if not clazz:
                crossplane.function.response.fatal(response, f"{composite[0]} did not define: {composite[1]}")
                logger.error(f"{composite[0]} did not define: {composite[1]}")
                return response
            composite = '.'.join(composite)
            if not inspect.isclass(clazz):
                crossplane.function.response.fatal(response, f"{composite} is not a class")
                logger.error(f"{composite} is not a class")
                return response
            if not issubclass(clazz, BaseComposite):
                crossplane.function.response.fatal(response, f"{composite} is not a subclass of BaseComposite")
                logger.error(f"{composite} is not a subclass of BaseComposite")
                return response
            self.clazzes[composite] = clazz

        try:
            composite = clazz(request, response, logger)
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
    pass
