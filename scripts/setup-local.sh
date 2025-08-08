#!/usr/bin/env bash

helm upgrade --install crossplane --namespace crossplane-system --create-namespace crossplane-preview/crossplane --version v2.0.0-preview.1

kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1beta1
kind: DeploymentRuntimeConfig
metadata:
  name: provider-incluster
spec:
  deploymentTemplate:
    spec:
      selector: {}
      template:
        spec:
          containers:
          - name: package-runtime
            args:
            - --debug
          serviceAccountName: provider-incluster
  serviceAccountTemplate:
    metadata:
      name: provider-incluster
EOF

kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: provider-incluster
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: provider-incluster
  namespace: crossplane-system
EOF

kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-helm
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-helm:v0.21.0
  runtimeConfigRef:
    apiVersion: pkg.crossplane.io/v1beta1
    kind: DeploymentRuntimeConfig
    name: provider-incluster
EOF

kubectl apply -f - <<EOF
apiVersion: helm.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: InjectedIdentity
EOF

kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-kubernetes
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-kubernetes:v0.18.0
  runtimeConfigRef:
    apiVersion: pkg.crossplane.io/v1beta1
    kind: DeploymentRuntimeConfig
    name: provider-incluster
EOF

kubectl apply -f - <<EOF
apiVersion: kubernetes.crossplane.io/v1alpha1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: InjectedIdentity
EOF

#  package: ghcr.io/fortra/function-pythonic:v0.0.3

kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-pythonic
spec:
  package: ghcr.io/iciclespider/function-pythonic:v0.0.0-20250811193238-f8d5c82deb9b
  runtimeConfigRef:
    apiVersion: pkg.crossplane.io/v1beta1
    kind: DeploymentRuntimeConfig
    name: provider-incluster
EOF
