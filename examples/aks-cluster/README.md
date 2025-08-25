# AKS Cluster Example

This example demonstrates how to provision an AKS cluster using Crossplane v1.

## Prerequisites

- Kubernetes cluster (v1.31+)
- Helm v3.x

## Install Crossplane v1 via Helm

1. **Add the Crossplane Helm repository:**
    ```sh
    helm repo add crossplane-stable https://charts.crossplane.io/stable
    helm repo update
    ```

2. **Install Crossplane v1:**
    ```sh
    helm install crossplane --namespace crossplane-system --create-namespace crossplane-stable/crossplane --version 1.x.x
    ```
    Replace `1.x.x` with the desired Crossplane v1 release.

3. **Verify installation:**
    ```sh
    kubectl get pods -n crossplane-system
    ```

4. **Apply the manifests:**
    ```sh
    ./install.sh
    ```