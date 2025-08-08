# Filing System based Composite

This example deploys a Crossplane Composition with the implementation
written in a stand alone python file, which enables using the
IDE of your choice for writing the python.

Deploy using kustomize:
```
$ kubectl apply --kustomize .
```
When run for the first time, the CRD for the composite does not exist
and will fail to deploy just that. Run a second time to also deploy
the composite.