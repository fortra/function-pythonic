# Writing to the Composite or Claim Status

function-pythonic can write to the Composite or Claim Status. See [Communication Between Composition Functions and the Claim](https://github.com/crossplane/crossplane/blob/main/design/one-pager-fn-claim-conditions.md) for more information.

## Testing This Function Locally

You can run your function locally and test it using [`crossplane render`](https://docs.crossplane.io/latest/cli/command-reference/#render)
with these example manifests.

```shell
crossplane render \
  xr.yaml composition.yaml functions.yaml
```

## Debugging This Function

First we need to run the command in debug mode. In a terminal Window Run:

```shell
# Run the function locally
$ go run . --insecure --debug
```

Next, set the python function `render.crossplane.io/runtime: Development` annotation so that
`crossplane render` communicates with the local process instead of downloading an image:

```yaml
apiVersion: pkg.crossplane.io/v1beta1
kind: Function
metadata:
  name: function-pythonic
  annotations: 
    render.crossplane.io/runtime: Development
spec:
  package: xpkg.upbound.io/crossplane-contrib/function-pythonic:v0.1.0
```

While the function is running in one terminal, open another terminal window and run `crossplane render`.
The function should output debug-level logs in the terminal.
