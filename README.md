# function-pythonic

## Introduction

A Crossplane composition function that lets you compose Composites using a set
of python classes enabling an elegant and terse syntax. Here is what the following
example is doing:

* Create an MR named 'vpc' with apiVersion 'ec2.aws.crossplane.io/v1beta1' and kind 'VPC'
* Set the vpc region and cidr from the XR spec values
* Return if the vpc's vpcId is not yet assigned to it
* Set the XR status.vpcId to the just created vpc id
* VPC is ready, create more resources using it

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: create-vpc
spec:
  compositeTypeRef:
    apiVersion: example.crossplane.io/v1
    kind: XR
  mode: Pipeline
  pipeline:
  - step: 
    functionRef:
      name: function-pythonic
    input:
      apiVersion: pythonic.fn.crossplane.io/v1beta1
      kind: Composite
      composite: |
        class Composite(BaseComposite):
          def compose(self):
            vpc = self.resources.vpc('ec2.aws.crossplane.io/v1beta1', 'VPC')
            vpc.spec.forProvider.region = self.spec.region
            vpc.spec.forProvider.cidrBlock = self.spec.cidr
            if not vpc.status.atProvider.vpcId:
              return
            self.status.vpcId = vpc.status.atProvider.vpcId
```

## Single use Composites

function-pythonic configures a `Composite` CompositeResourceDefinition that enables
single purpose Composites. A common use case is a one time initialization task.
```yaml
apiVersion: pythonic.fortra.com/v1alpha1
kind: Composite
metadata:
  name: composite-example
spec:
  composite: |
    class Composite(BaseComposite):
      def compose(self):
        self.status.composite = 'Hello, World!'
```

## Examples

In the [examples](./examples) directory are most of the function-go-templating examples
implemented using function-pythonic. In addition, the [eks-cluster](./examples/eks-cluster/composition.yaml)
example is a complex example composing many resources.

## Pythonic access of Protobuf Messages

All Protobuf messages are wrapped by a set of python classes which enable using
both object attribute names and dictionary key names to traverse the Protobuf
message contents. For example, the following examples obtain the same value
from the RunFunctionRequest message:
```python
region = request.observed.composite.resource.spec.region
region = request['observed']['composite']['resource']['spec']['region']
```
Getting values from free form map and Struct values will not throw
errors for keys that do not exist, but will return an empty placeholder
which evaluates as False. For example, the following will evaluate as False
with a just created RunFunctionResponse message:
```python
vpcId = response.desired.resources.vpc.resource.status.atProvider.vpcId
if vpcId:
    # The vpcId is available
```
Note that maps or lists that do exist but do not have any members will evaluate
as True, contrary to Python dicts and lists. Use the `len` function to test
if the map or list exists and has members.

When setting fields, all empty intermediary placeholders will automatically
be created. For example, this will create all items needed to set the
region on the desired resource:
```python
response.desired.resources.vpc.resource.spec.forProvider.region = 'us-east-1'
```
Calling a message or map will clear it and will set any provided key word
arguments. For example, this will either create or clear the resource
and then set it's apiVersion and kind:
```python
response.desired.resources.vpc.resource(apiVersion='ec2.aws.crossplane.io/v1beta1', kind='VPC')
```
The following functions are provided to create Protobuf structures:
| Function | Description |
| ----- | ----------- |
| Struct | Create a new Protobuf Struct dictionary |
| ListValue | Create a new Protobuf ListValue list |
| Yaml | Create a new Protobuf structure from a yaml string |
| Json | Create a new Protobuf structure from a json string |

The following items are supported in all the Protobuf Message wrapper classes: `bool`,
`len`, `contains`, `iter`, `hash`, `==`, `str`, `format`

To convert a Protobuf message to a string value, use either `str` or `format`.
```python
yaml  = str(request)                # get the request as yaml
yaml  = format(request)             # also get the request as yaml
yaml  = format(request, 'yaml')     # yet another get the request as yaml
json  = format(request, 'json')     # get the request as json
json  = format(request, 'jsonc')    # get the request as json compact
proto = format(request, 'protobuf') # get the request as a protobuf string
```
## Composite Composition

Composite composition is performed from a Composite orientation. A `BaseComposite` class
is subclassed and the `compose` method is implemented.
```python
class Composite(BaseComposite):
    def compose(self):
        # Compose the Composite
```
The compose method can also declare itself as performing async io:
```python
class Composite(BaseComposite):
    async def compose(self):
        # Compose the Composite using async io when needed
```

### BaseComposite

The BaseComposite class provides the following fields for manipulating the Composite itself:

| Field | Description |
| ----- | ----------- |
| self.observed | Low level direct access to the observed composite |
| self.desired | Low level direct access to the desired composite |
| self.apiVersion | The composite observed apiVersion |
| self.kind | The composite observed kind |
| self.metadata | The composite observed metadata |
| self.spec | The composite observed spec |
| self.status | The composite desired and observed status, read from observed if not in desired |
| self.conditions | The composite desired and observed conditions, read from observed if not in desired |
| self.connection | The composite desired and observed connection detials, read from observed if not in desired |
| self.ready | The composite desired ready state |

The BaseComposite also provides access to the following Crossplane Function level features:

| Field | Description |
| ----- | ----------- |
| self.request | Low level direct access to the RunFunctionRequest message |
| self.response | Low level direct access to the RunFunctionResponse message |
| self.logger | Python logger to log messages to the running function stdout |
| self.ttl | Get or set the response TTL, in seconds |
| self.autoReady | Perform auto ready processing after the compose method returns, default True |
| self.credentials | The request credentials |
| self.context | The response context, initialized from the request context |
| self.environment | The response environment, initialized from the request context environment |
| self.requireds | Request and read additional local Kubernetes resources |
| self.resources | Define and process managed resources |
| self.results | Return results on the Composite and optionally on the Claim |

### Managed Resources

Creating and accessing managed resources is performed using the `BaseComposite.resources` field.
`BaseComposite.resources` is a dictionary of the managed resources whose key is the composition
resource name. The value returned when getting a resource from BaseComposite is the following
Resource class:

| Field | Description |
| ----- | ----------- |
| Resource.name | The composition resource name of the managed resource |
| Resource.observed | Low level direct access to the observed managed resource |
| Resource.desired | Low level direct access to the desired managed resource |
| Resource.apiVersion | The managed resource apiVersion |
| Resource.kind | The managed resource kind |
| Resource.metadata | The managed resource desired metadata |
| Resource.externalName | The managed resource external name |
| Resource.spec | The resource spec |
| Resource.status | The resource status |
| Resource.conditions | The resource conditions |
| Resource.connection | The resource connection details |
| Resource.ready | The resource ready state |

### Required Resources (AKA Extra Resources)

Creating and accessing required resources is performed using the `BaseComposite.requireds` field.
`BaseComposite.requireds` is a dictionary of the required resources whose key is the required
resource name. The value returned when getting a required resource from BaseComposite is the
following RequiredResources class:

| Field | Description |
| ----- | ----------- |
| RequiredResources.name | The required resources name |
| RequiredResources.apiVersion | The required resources apiVersion |
| RequiredResources.kind | The required resources kind |
| RequiredResources.matchName | The names to match when returning the required resources |
| RequiredResources.matchLabels | The labels to match when returning the required resources |

RequiredResourcs acts like a Python list to provide access to the found required resources.
Each resource in the list is the following RequiredResource class:

| Field | Description |
| ----- | ----------- |
| RequiredResource.name | The required resource name |
| RequiredResource.observed | Low level direct access to the observed required resource |
| RequiredResource.apiVersion | The required resource apiVersion |
| RequiredResource.kind | The required resource kind |
| RequiredResource.metadata | The required resource metadata |
| RequiredResource.spec | The required resource spec |
| RequiredResource.status | The required resource status |
| RequiredResource.conditions | The required resource conditions |

## Installing Python Packages

function-pythonic supports a `--pip-install` command line option which will run pip install
with the configured pip install command. For example, the following DeploymentRuntimeConfig:
```yaml
apiVersion: pkg.crossplane.io/v1beta1
kind: DeploymentRuntimeConfig
metadata:
  name: function-pythonic
spec:
  deploymentTemplate:
    spec:
      template:
        spec:
          containers:
          - name: package-runtime
            args:
            - --debug
            - --pip-install
            - --quiet aiobotocore==2.23.2
```
