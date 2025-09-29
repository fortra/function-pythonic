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


## Architecture

```mermaid
graph TD
    A[User] -->|Orders a cluster| B[AzureKubernetesCluster XR]
    
    subgraph "Crossplane Control Plane"
        B -->|Processed by| C[Crossplane]
        C -->|Uses| D[Composition]
        D -->|Translates to| E[Managed Resources]
    end
    
    subgraph "Azure Providers"
        P1[Azure Provider]
        P2[provider-azure-containerservice]
    end
    
    E -->|ResourceGroup| P1
    E -->|KubernetesCluster| P2
    
    P1 -->|Creates| R1[Azure Resource Group]
    P2 -->|Creates| R2[Azure AKS Cluster]
    


    classDef crossplane fill:#326ce5,stroke:#fff,stroke-width:2px,color:#fff;
    classDef provider fill:#ff6b6b,stroke:#fff,stroke-width:2px,color:#fff;
    classDef azure fill:#0072C6,stroke:#fff,stroke-width:2px,color:#fff;
    classDef config fill:#ddd,stroke:#333,stroke-width:1px;
    
    class B,C,D,E crossplane;
    class P1,P2 provider;
    class R1,R2 azure;
    class N1,N2,N3,N4 config;
```

## Technical Architecture

### Implementation Flow

1. **Python Functions**
   - Python code defines the resource configuration logic
   - Functions are packaged into ConfigMaps
   - ConfigMaps are labeled with ```function-pythonic.package: ''```

2. **Crossplane Integration**
   - XR Definition describes the custom resource structure
   - Composition references the Python functions
   - Function pipeline executes the Python code

3. **Resource Management**
   - Python functions generate Managed Resources
   - Managed Resources create actual cloud resources
   - Resources are managed through provider controllers

### Diagram

```mermaid
graph TD
    subgraph "Python Function Components"
        PY[Python Functions]
        CM[ConfigMap]
        PY -->|Packaged into| CM
        CM -->|Label: python-module| K8S[Kubernetes]
    end

    subgraph "Crossplane Components"
        XR[XR Definition]
        COMP[Composition]
        FN[Function Pipeline]
        
        XR -->|References| COMP
        COMP -->|Uses| FN
        FN -->|Imports| CM
    end

    subgraph "Resource Creation"
        FN -->|Generates| MR[Managed Resources]
        MR -->|Creates| AKS[AKS Cluster]
    end

    subgraph "Legend"
        L1[Python Code]
        L2[Kubernetes Resources]
        L3[Generated Resources]
    end

    classDef python fill:#306998,stroke:#fff,stroke-width:2px,color:#fff;
    classDef k8s fill:#326ce5,stroke:#fff,stroke-width:2px,color:#fff;
    classDef generated fill:#ff6b6b,stroke:#fff,stroke-width:2px,color:#fff;
    
    class PY,L1 python;
    class CM,XR,COMP,FN,K8S,L2 k8s;
    class MR,AKS,L3 generated;
```
