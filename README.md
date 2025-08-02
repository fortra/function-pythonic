# function-pythonic

## Introduction

A Crossplane composition function that lets you compose Composites using a set
of python classes enabling an elegant and terse syntax. Here is what the following
example is doing:

* Create an MR named 'vpc' with apiVersion 'ec2.aws.crossplane.io/v1beta1' and kind 'VPC'
* Set the vpc region and cidr from the XR spec values
* Set the XR status.vpcId to the created vpc id

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
            self.status.vpcId = vpc.status.atProvider.vpcId
```

## Examples

In the [examples](./examples) directory are many exemples, including all of the
function-go-templating examples implemented using function-pythonic.
The [eks-cluster](./examples/eks-cluster/composition.yaml) example is a good
complex example creating the entire vpc structure needed for an EKS cluster.

## Managed Resource Dependencies

function-pythonic automatically handles dependencies between managed resources.

Just compose everything as if it is immediately created and the framework will delay
the creation of any resources which depend on other resources which do not exist yet.
In other words, it accomplishes what [function-sequencer](https://github.com/crossplane-contrib/function-sequencer)
provides, but it automatically detects the dependencies.

If a resource has been composed and a dependency no longer exists due to some unexpected
condition, the observed value for that field will automatically be used.

Take the following example:
```yaml
vpc = self.resources.VPC('ec2.aws.crossplane.io/v1beta1', 'VPC')
vpc.spec.forProvider.region = 'us-east-1
vpc.spec.forProvider.cidrBlock = '10.0.0.0/16'

subnet = self.resources.SubnetA('ec2.aws.crossplane.io/v1beta1', 'Subnet')
subnet.spec.forProvider.region = 'us-east-1'
subnet.spec.forProvider.vpcId = vpc.status.atProvider.vpcId
subnet.spec.forProvider.availabilityZone = 'us-east-1a'
subnet.spec.forProvider.cidrBlock = '10.0.0.0/20'
```
If the Subnet does not yet exist, the framework will detect if the vpcId set
in the Subnet is unknown, and will delay the creation of the subnet.

Once the Subnet has been created, if for some mysterious reason the vpcId passed
to the Subnet is unknown, the framework will automatically use the vpcId in the
observed Subnet.

## Pythonic access of Protobuf Messages

All Protobuf messages are wrapped by a set of python classes which enable using
both object attribute names and dictionary key names to traverse the Protobuf
message contents. For example, the following examples obtain the same value
from the RunFunctionRequest message:
```python
region = request.observed.composite.resource.spec.region
region = request['observed']['composite']['resource']['spec']['region']
```
Getting values from free form map and list values will not throw
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
and then set its apiVersion and kind:
```python
response.desired.resources.vpc.resource(apiVersion='ec2.aws.crossplane.io/v1beta1', kind='VPC')
```
The following functions are provided to create Protobuf structures:
| Function | Description |
| ----- | ----------- |
| Map | Create a new Protobuf map |
| List | Create a new Protobuf list |
| Yaml | Create a new Protobuf structure from a yaml string |
| Json | Create a new Protobuf structure from a json string |
| Base64Encode | Encode a string into base 64 |
| Base64Decode | Decode a string from base 64 |

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
| self.results | Returned results on the Composite and optionally on the Claim |

### Managed Resources

Creating and accessing managed resources is performed using the `BaseComposite.resources` field.
`BaseComposite.resources` is a dictionary of the managed resources whose key is the composition
resource name. The value returned when getting a resource from BaseComposite is the following
Resource class:

| Field | Description |
| ----- | ----------- |
| Resource(apiVersion,kind,namespace,name) | Reset the resource and set the optional parameters |
| Resource.name | The composition resource name of the managed resource |
| Resource.observed | Low level direct access to the observed managed resource |
| Resource.desired | Low level direct access to the desired managed resource |
| Resource.apiVersion | The managed resource apiVersion |
| Resource.kind | The managed resource kind |
| Resource.externalName | The managed resource external name |
| Resource.metadata | The managed resource desired metadata |
| Resource.spec | The resource spec |
| Resource.data | The resource data |
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
| RequiredResource(apiVersion,kind,namespace,name,labels) | Reset the required resource and set the optional parameters |
| RequiredResources.name | The required resources name |
| RequiredResources.apiVersion | The required resources apiVersion |
| RequiredResources.kind | The required resources kind |
| RequiredResources.namespace | The namespace to match when returning the required resources, see note below |
| RequiredResources.matchName | The names to match when returning the required resources |
| RequiredResources.matchLabels | The labels to match when returning the required resources |

The current version of crossplane-sdk-python used by function-pythonic does not support namespace
selection. For now, use matchLabels and filter the results if required.

RequiredResources acts like a Python list to provide access to the found required resources.
Each resource in the list is the following RequiredResource class:

| Field | Description |
| ----- | ----------- |
| RequiredResource.name | The required resource name |
| RequiredResource.observed | Low level direct access to the observed required resource |
| RequiredResource.apiVersion | The required resource apiVersion |
| RequiredResource.kind | The required resource kind |
| RequiredResource.metadata | The required resource metadata |
| RequiredResource.spec | The required resource spec |
| RequiredResource.data | The required resource data |
| RequiredResource.status | The required resource status |
| RequiredResource.conditions | The required resource conditions |

## Single use Composites

Tired of creating a CompositeResourceDefinition, a Composition, and a Composite
just to run that Composition once in a single use or initialize task?

function-pythonic installs a `Composite` CompositeResourceDefinition that enables
creating such tasks using a single Composite resource:
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
