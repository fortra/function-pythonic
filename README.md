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

## Pythonic Protobuf access

All Protobuf messages are wrapped by a set of python classes which enables using
both object attribute names and dictionary key names to traverse the Protobuf
message contents. For example, the following examples obtain the same value
from the RunFunctionRequest message:
```python
    region = request.observed.composite.resource.spec.region
    region = request['observed']['composite']['resource']['spec']['region']
```
Getting values from free form map and Struct values will not throw
errors for keys that do not exist, but will return None. The following will
return None when used with a just created RunFunctionResponse message:
```python
    isnone = response.desired.resources.vpc.resource.spec.forProvider.region
```
All the intermediary items have empty placeholders created then enable traversing
such non yet existing structures to be able to return None on the final field access.



Provide a Python script that implements a Composite class that implements
a compose method.

```python
class Composite(BaseComposite):
  def compose(self):
```

The `function-pythonic` BaseComposite class provides the following fields:

| Field | Description |
| ----- | ----------- |
| self.context | The composition context |
| self.environment | The composition environment |
| self.requireds | Access to required resources |
| self.credentials | Access to the composite's credentials |
| self.apiVersion | The composite apiVersion |
| self.kind | The composite kind |
| self.metadata | The composite metadata |
| self.spec | The composite spec |
| self.resources | The composite manageed resources |
| self.status | The composite status |
| self.conditions | The composite conditions |
| self.connection | The composite connection details |
| self.ready | The composite ready state |
| self.logger | A logger to emit log messages in the function pod's log |

Creating and accessing resources using `self.resources` returns a python
object with the following fields:

| Field | Description |
| ----- | ----------- |
| resource.name | The managed resource name within the composite |
| resource.apiVersion | The resource apiVersion |
| resource.kind | The resource kind |
| resource.externalName | The resource external name |
| resource.metadata | The resource metadata |
| resource.spec | The resource spec |
| resource.status | The resource status |
| resource.conditions | The resource conditions |
| resource.connection | The resource connection details |
| resource.ready | The resource ready state |

The following example creates an AWS EC2 VPC:

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
            vpc.spec.forProvider.region = 'us-east-1'
            vpc.spec.forProvider.cidrBlock = '10.0.0.0/16'
            if not vpc.status.atProvider.vpcId:
              return
            # VPC is ready, create resources in it.
            self.status.vpcId = vpc.status.atProvider.vpcId
```

In the `examples` directory are most of the function-go-templating examples
implemented using function-pythonic. In addition, the eks-cluster example is
a complex example composing many resources.
