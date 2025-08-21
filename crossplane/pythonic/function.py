"""A Crossplane composition function."""

import asyncio
import base64
import builtins
import importlib
import inspect
import logging
import sys

import grpc
import crossplane.function.response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from .. import pythonic

builtins.BaseComposite = pythonic.BaseComposite
builtins.append = pythonic.append
builtins.Map = pythonic.Map
builtins.List = pythonic.List
builtins.Unknown = pythonic.Unknown
builtins.Yaml = pythonic.Yaml
builtins.Json = pythonic.Json
builtins.B64Encode = pythonic.B64Encode
builtins.B64Decode = pythonic.B64Decode

logger = logging.getLogger(__name__)


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self, debug=False):
        """Create a new FunctionRunner."""
        self.debug = debug
        self.clazzes = {}

    def invalidate_module(self, module):
        self.clazzes.clear()
        if module in sys.modules:
            del sys.modules[module]
        importlib.invalidate_caches()

    async def RunFunction(
        self, request: fnv1.RunFunctionRequest, _: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        try:
            return await self.run_function(request)
        except:
            logger.exception('Exception thrown in run fuction')
            raise

    async def run_function(self, request):
        composite = request.observed.composite.resource
        name = list(reversed(composite['apiVersion'].split('/')[0].split('.')))
        name.append(composite['kind'])
        name.append(composite['metadata']['name'])
        logger = logging.getLogger('.'.join(name))
        if 'iteration' in request.context:
            request.context['iteration'] = request.context['iteration'] + 1
        else:
            request.context['iteration'] = 1
        logger.debug(f"Starting compose, {ordinal(request.context['iteration'])} pass")

        response = crossplane.function.response.to(request)

        if composite['apiVersion'] == 'pythonic.fortra.com/v1alpha1' and composite['kind'] == 'Composite':
            if 'composite' not in composite['spec']:
                logger.error('Missing spec "composite"')
                crossplane.function.response.fatal(response, 'Missing spec "composite"')
                return response
            composite = composite['spec']['composite']
        else:
            if 'composite' not in request.input:
                logger.error('Missing input "composite"')
                crossplane.function.response.fatal(response, 'Missing input "composite"')
                return response
            composite = request.input['composite']

        clazz = self.clazzes.get(composite)
        if not clazz:
            if '\n' in composite:
                module = Module()
                try:
                    exec(composite, module.__dict__)
                except Exception as e:
                    logger.exception('Exec exception')
                    crossplane.function.response.fatal(response, f"Exec exception: {e}")
                    return response
                composite = ['<script>', 'Composite']
            else:
                composite = composite.rsplit('.', 1)
                if len(composite) == 1:
                    logger.error(f"Composite class name does not include module: {composite[0]}")
                    crossplane.function.response.fatal(response, f"Composite class name does not include module: {composite[0]}")
                    return response
                try:
                    module = importlib.import_module(composite[0])
                except Exception as e:
                    logger.error(str(e))
                    crossplane.function.response.fatal(response, f"Import module exception: {e}")
                    return response
            clazz = getattr(module, composite[1], None)
            if not clazz:
                logger.error(f"{composite[0]} did not define: {composite[1]}")
                crossplane.function.response.fatal(response, f"{composite[0]} did not define: {composite[1]}")
                return response
            composite = '.'.join(composite)
            if not inspect.isclass(clazz):
                logger.error(f"{composite} is not a class")
                crossplane.function.response.fatal(response, f"{composite} is not a class")
                return response
            if not issubclass(clazz, BaseComposite):
                logger.error(f"{composite} is not a subclass of BaseComposite")
                crossplane.function.response.fatal(response, f"{composite} is not a subclass of BaseComposite")
                return response
            self.clazzes[composite] = clazz

        try:
            composite = clazz(request, response, logger)
        except Exception as e:
            logger.exception('Instatiate exception')
            crossplane.function.response.fatal(response, f"Instatiate exception: {e}")
            return response

        try:
            result = composite.compose()
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.exception('Compose exception')
            crossplane.function.response.fatal(response, f"Compose exception: {e}")
            return response

        requested = []
        for name, required in composite.requireds:
            if required.apiVersion and required.kind:
                r = Map(apiVersion=required.apiVersion, kind=required.kind)
                if required.namespace:
                    r.namespace = required.namespace
                if required.matchName:
                    r.matchName = required.matchName
                for key, value in required.matchLabels:
                    r.matchLabels[key] = value
                if r != composite.context._requireds[name]:
                    composite.context._requireds[name] = r
                    requested.append(name)
        if requested:
            logger.info(f"Requireds requested: {','.join(requested)}")
            return response

        unknownResources = []
        warningResources = []
        fatalResources = []
        for name, resource in sorted(entry for entry in composite.resources):
            unknowns = resource.desired._getUnknowns
            if unknowns:
                unknownResources.append(name)
                warning = False
                fatal = False
                if resource.observed:
                    warningResources.append(name)
                    warning = True
                    if resource.unknownsFatal or (resource.unknownsFatal is None and composite.unknownsFatal):
                        fatalResources.append(name)
                        fatal = True
                if self.debug:
                    for destination, source in sorted(unknowns.items()):
                        destination = self.trimFullName(destination)
                        source = self.trimFullName(source)
                        if fatal:
                            logger.error(f'Observed unknown: {destination} = {source}')
                        elif warning:
                            logger.warning(f'Observed unknown: {destination} = {source}')
                        else:
                            logger.debug(f'Desired unknown: {destination} = {source}')
                if resource.observed:
                    resource.desired._patchUnknowns(resource.observed)
                else:
                    del composite.resources[name]

        if fatalResources:
            level = logger.error
            reason = 'FatalUnknowns'
            message = f"Observed resources with unknowns: {','.join(fatalResources)}"
            status = False
            event = composite.events.fatal
        elif warningResources:
            level = logger.warning
            reason = 'ObservedUnknowns'
            message = f"Observed resources with unknowns: {','.join(warningResources)}"
            status = False
            event = composite.events.warning
        elif unknownResources:
            level = logger.info
            reason = 'DesiredUnknowns'
            message = f"Desired resources with unknowns: {','.join(unknownResources)}"
            status = False
            event = composite.events.info
        else:
            level = None
            reason = 'AllComposed'
            message = 'All resources are composed'
            status = True
            event = None
        if not self.debug and level:
            level(message)
        composite.conditions.ResourcesComposed(reason, message, status)
        if event:
            event(reason, message)

        for name, resource in composite.resources:
            if resource.autoReady or (resource.autoReady is None and composite.autoReady):
                if resource.ready is None:
                    if resource.conditions.Ready.status:
                        resource.ready = True

        logger.info('Completed compose')
        return response

    def trimFullName(self, name):
        name = name.split('.')
        for values in (
                ('request', 'observed', 'resources', None, 'resource'),
                ('request', 'extra_resources', None, 'items', 'resource'),
                ('response', 'desired', 'resources', None, 'resource'),
        ):
            if len(values) <= len(name):
                for ix, value in enumerate(values):
                    if value and value != name[ix] and not name[ix].startswith(f"{value}["):
                       break
                else:
                    ix = 0
                    for value in values:
                        if value:
                            if value == name[ix]:
                                del name[ix]
                            elif ix:
                                name[ix-1] += name[ix][len(value):]
                                del name[ix]
                            else:
                                name[ix] = name[ix][len(value):]
                                ix += 1
                        else:
                            ix += 1
                    break
        return '.'.join(name)


def ordinal(ix):
    ix = int(ix)
    if 11 <= (ix % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(ix % 10, 4)]
    return str(ix) + suffix


class Module:
    pass
