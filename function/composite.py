
import datetime
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

import function.protobuf


_notset = object()


class BaseComposite:
    def __init__(self, request, response, logger):
        self.request = function.protobuf.Message(None, None, request.DESCRIPTOR, request, 'Function Request')
        self.response = function.protobuf.Message(None, None, response.DESCRIPTOR, response)
        self.logger = logger
        self.autoReady = True
        self.credentials = Credentials(self.request)
        self.context = self.response.context
        self.environment = self.context['apiextensions.crossplane.io/environment']
        self.requireds = Requireds(self)
        self.resources = Resources(self)
        self.results = Results(self.response)

        self.observed = self.request.observed.composite
        self.desired = self.response.desired.composite
        self.apiVersion = self.observed.resource.apiVersion
        self.kind = self.observed.resource.kind
        self.metadata = self.observed.resource.metadata
        self.spec = self.observed.resource.spec
        self.status = Status(self.observed.resource.status, self.desired.resource.status)
        self.conditions = Conditions(self.observed, self.response)
        self.connection = Connection(self.observed, self.desired)

    @property
    def ttl(self):
        return self.response.meta.ttl.seconds

    @ttl.setter
    def ttl(self, ttl):
        self.response.meta.ttl.seconds = ttl    

    @property
    def ready(self):
        ready = self.desired.ready
        if ready == fnv1.Ready.READY_TRUE:
            return True
        if ready == fnv1.Ready.READY_FALSE:
            return False
        return None

    @ready.setter
    def ready(self, ready):
        if ready:
            self.desired.ready = fnv1.Ready.READY_TRUE
        elif ready == None:
            self.desired.ready = fnv1.Ready.READY_UNSPECIFIED
        else:
            self.desired.ready = fnv1.Ready.READY_FALSE

    async def compose(self):
        raise NotImplementedError()


class Requireds:
    def __init__(self, composite):
        self._composite = composite

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        return RequiredResources(self._composite, key)


class RequiredResources:
    def __init__(self, composite, name):
        self.name = name
        self._selector = composite.response.requirements.extra_resources[name]
        self._resources = composite.request.extra_resources[name]

    def __call__(self, apiVersion=_notset, kind=_notset, name=_notset, labels=_notset):
        self._selector()
        if apiVersion != _notset:
            self.apiVersion = apiVersion
        if kind != _notset:
            self.kind = kind
        if name != _notset:
            self.matchName = name
        if labels != _notset:
            self.matchLabels = labels
        return self

    @property
    def apiVersion(self):
        return self._selector.api_version

    @apiVersion.setter
    def apiVersion(self, apiVersion):
        self._selector.api_version = apiVersion

    @property
    def kind(self):
        return self._selector.kind

    @kind.setter
    def kind(self, kind):
        self._selector.kind = kind

    @property
    def matchName(self):
        return self._selector.match_name

    @matchName.setter
    def matchName(self, name):
        self._selector.match_name = name

    @property
    def matchLabels(self):
        return self._selector.match_labels

    @matchLabels.setter
    def matchLabels(self, labels):
        self._selector.match_labels.labels = labels

    def __getitem__(self, key):
        if key >= len(self._resources.items):
            return RequiredResource(self.name, fnv1.Resource())
        return RequiredResource(self.name, self._resources.items[key])

    def __bool__(self):
        return len(self._resources.items) > 0

    def __len__(self):
        return len(self._resources.items)

    def __iter__(self):
        for ix in range(len(self)):
            yield self[ix]


class RequiredResource:
    def __init__(self, name, resource):
        self.name = name
        self.observed = resource
        self.apiVersion = resource.resource.apiVersion
        self.kind = resource.resource.kind
        self.metadata = resource.resource.metadata
        self.spec = resource.resource.spec
        self.status = resource.resource.status
        self.conditions = Conditions(resource)


class Results:
    def __init__(self, response):
        self._results = response.results

    def add(self, message=_notset, fatal=_notset, warning=_notset, reaoson=_notset, claim=_notset):
        result = Result(self._results.add())
        if fatal != _notset:
            result.fatal = fatal
        elif warning != _notset:
            result.warning = warning
        if message != _notset:
            result.message = message
        if reason != _notset:
            result.reason = reason
        if claim != _notset:
            result.claim = claim
        return result

    def __bool__(self):
        return len(self._results) > 0

    def __len__(self):
        len(self._results)

    def __getitem__(self, key):
        if key >= len(self._results):
            return Result()
        return Result(self._results[ix])

    def __iter__(self):
        for ix in range(len(self._results)):
            yield self[ix]


class Result:
    def __init(self, result=None):
        self._result = result

    def __bool__(self):
        return self._result is not None

    @property
    def fatal(self):
        return bool(self) and self._result == fnv1.Severity.SEVERITY_FATAL
    @fatal.setter
    def fatal(self, fatal):
        if bool(self):
            if fatal:
                self._result = fnv1.Severity.SEVERITY_FATAL
            else:
                self._result = fnv1.Severity.SEVERITY_NORMAL

    @property
    def warning(self):
        return bool(self) and self._result == fnv1.Severity.SEVERITY_WARNING
    @warning.setter
    def warning(self, warning):
        if bool(self):
            if warning:
                self._result = fnv1.Severity.SEVERITY_WARNING
            else:
                self._result = fnv1.Severity.SEVERITY_NORMAL

    @property
    def message(self):
        return self._result.message if bool(self) else None
    @message.setter
    def message(self, message):
        if bool(self):
            self._result.message = message

    @property
    def reason(self):
        return self._result.reason if bool(self) else None
    @reason.setter
    def reason(self, reason):
        if bool(self):
            self._result.reason = reason

    @property
    def claim(self):
        return bool(self) and self._result == fnv1.Target.TARGET_COMPOSITE_AND_CLAIM
    @claim.setter
    def claim(self, claim):
        if bool(self):
            if claim is True:
                self._result.target = fnv1.Target.TARGET_COMPOSITE_AND_CLAIM
            elif claim is False:
                self._result.target = fnv1.Target.TARGET_COMPOSITE
            else:
                self._result.target = fnv1.Target.TARGET_UNSPECIFIED


class Credentials:
    def __init__(self, request):
        self.__dict__['_request'] = request

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        return self._request.credentials[key].credentials_data

    def __bool__(self):
        return bool(_request.credentials)

    def __len__(self):
        return len(self._request.credentials)

    def __contains__(self, key):
        return key in _request.credentials

    def __iter__(self):
        for key, resource in self._request.credentials:
            yield key, self[key]


class Resources:
    def __init__(self, composite):
        self._composite = composite

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        return Resource(self._composite, key)

    def __bool__(self):
        return bool(self._composite.response.desired.resources)

    def __len__(self):
        return len(self._composite.response.desired.resources)

    def __contains__(self, key):
        return key in self._composite.response.desired.resources

    def __iter__(self):
        for key, resource in self._composite.response.desired.resources:
            yield key, self[key]


class Resource:
    def __init__(self, composite, name):
        self.name = name
        self.observed = composite.request.observed.resources[name]
        self.desired = composite.response.desired.resources[name]
        self.metadata = self.desired.resource.metadata
        self.spec = self.desired.resource.spec
        self.status = self.observed.resource.status
        self.conditions = Conditions(self.observed)
        self.connection = Connection(self.observed, self.desired)

    def __call__(self, apiVersion=_notset, kind=_notset, name=_notset):
        self.desired.resource()
        if apiVersion != _notset:
            self.apiVersion = apiVersion
        if kind != _notset:
            self.kind = kind
        if name != _notset:
            self.metadata.name = name
        return self

    @property
    def apiVersion(self):
        return self.observed.resource.apiVersion

    @apiVersion.setter
    def apiVersion(self, apiVersion):
        self.desired.resource.apiVersion = apiVersion

    @property
    def kind(self):
        return self.observed.resource.kind

    @kind.setter
    def kind(self, kind):
        self.desired.resource.kind = kind

    @property
    def externalName(self):
        name = self.metadata.annotations['crossplane.io/external-name']
        if name is None:
            name = self.observed.resource.metadata.annotations['crossplane.io/external-name']
        return name

    @externalName.setter
    def externalName(self, name):
        self.metadata.annotations['crossplane.io/external-name'] = name

    @property
    def ready(self):
        ready = self.desired.ready
        if ready == fnv1.Ready.READY_UNSPECIFIED:
            ready = self.observed.ready
        if ready == fnv1.Ready.READY_TRUE:
            return True
        if ready == fnv1.Ready.READY_FALSE:
            return False
        return None

    @ready.setter
    def ready(self, ready):
        if ready:
            self.desired.ready = fnv1.Ready.READY_TRUE
        elif ready == None:
            self.desired.ready = fnv1.Ready.READY_UNSPECIFIED
        else:
            self.desired.ready = fnv1.Ready.READY_FALSE


class Status:
    def __init__(self, observed, desired):
        self.__dict__['_observed'] = observed
        self.__dict__['_desired'] = desired

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        value = self._desired[key]
        if value is None:
            value = self._observed[key]
        return value

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        self._desired[key] = value


class Conditions:
    def __init__(self, observed, response=None):
        self._observed = observed
        self._response = response

    def __getattr__(self, type):
        return self[type]

    def __getitem__(self, type):
        return Condition(self, type)


class Condition(function.protobuf.ProtobufValue):
    def __init__(self, conditions, type):
        self._conditions = conditions
        self.type = type

    @property
    def _protobuf_value(self):
        status = self.status
        value = {
            'type': self.type,
            'status': 'Unknown' if status is None else str(status),
            'reason': self.reason or '',
            'message': self.message or '',
        }
        time = self.lastTransitionTime
        if time is not None:
            value['lastTransitionTime'] = time.isoformat().replace('+00:00', 'Z')
        return value

    def __call__(self, status=_notset, reason=_notset, message=_notset, claim=_notset):
        self._find_condition(True)
        if status != _notset:
            self.status = status
        if reason != _notset:
            self.reason = reason
        if message != _notset:
            self.message = message
        if claim != _notset:
            self.claim = claim
        return self

    @property
    def status(self):
        condition = self._find_condition()
        if condition:
            if condition.status in (fnv1.Status.STATUS_CONDITION_TRUE, 'True', True):
                return True
            if condition.status in (fnv1.Status.STATUS_CONDITION_FALSE, 'False', False):
                return False
        return None

    @status.setter
    def status(self, status):
        condition = self._find_condition(True)
        if status is None:
            condition.status = fnv1.Status.STATUS_CONDITION_UNKNOWN
        elif status is True:
            condition.status = fnv1.Status.STATUS_CONDITION_TRUE
        elif status is False:
            condition.status = fnv1.Status.STATUS_CONDITION_FALSE
        else:
            condition.status = fnv1.Status.STATUS_CONDITION_UNSPECIFIED

    @property
    def reason(self):
        condition = self._find_condition()
        if condition:
            return condition.reason
        return None

    @reason.setter
    def reason(self, reason):
        self._find_condition(True).reason = reason

    @property
    def message(self):
        condition = self._find_condition()
        if condition:
            return condition.message
        return None

    @message.setter
    def message(self, message):
        self._find_condition(True).message = message

    @property
    def lastTransitionTime(self):
        for observed in self._conditions._observed.resource.status.conditions:
            if observed.type == self.type:
                time = observed.lastTransitionTime
                if time is not None:
                    return datetime.datetime.fromisoformat(time)
        return None

    @property
    def claim(self):
        condition = self._find_condition()
        return condition and condition.target == fnv1.Target.TARGET_COMPOSITE_AND_CLAIM

    @claim.setter
    def claim(self, claim):
        condition = self._find_condition(True)
        if claim is True:
            condition.target = fnv1.Target.TARGET_COMPOSITE_AND_CLAIM
        elif claim is False:
            condition.target = fnv1.Target.TARGET_COMPOSITE
        else:
            condition.target = fnv1.Target.TARGET_UNSPECIFIED

    def _find_condition(self, create=False):
        if self._conditions._response is not None:
            for condition in self._conditions._response.conditions:
                if condition.type == self.type:
                    return condition
        for observed in self._conditions._observed.resource.status.conditions:
            if observed.type == self.type:
                break
        else:
            observed = None
        if not create:
            return observed
        if self._conditions._response is None:
            raise ValueError('Condition is read only')
        condition = fnv1.Condition()
        condition.type = self.type
        if observed:
            condition.status = observed.status
            condition.reason = observed.reason
            condition.message = observed.message
            condition.target = observed.target
        return self._conditions._response.conditions.append(condition)


class Connection:
    def __init__(self, observed, desired=None):
        self.__dict__['_observed'] = observed
        self.__dict__['_desired'] = desired

    def __bool__(self):
        if self._desired is not None and len(self._desired.connection_details) > 0:
            return True
        if self._observed is not None and len(self._observed.connection_details) > 0:
            return True
        return False

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if self._desired is not None:
            value = self._desired.connection_details[key]
        else:
            value = None
        if value is None and self._observed is not None:
            value = self._observed.connection_details[key]
        return value

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if self._desired is None:
            raise ValueError('Conection is read only')
        self._desired.connection_details[key] = value
