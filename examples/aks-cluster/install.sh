#!/usr/bin/env bash

# Install function-pythonic and azure providers
kubectl apply -f cluster-function-pythonic.yaml
kubectl apply -f providers.yaml

# Install AKS Crossplane XRDs and Compositions
kubectl apply -f definition.yaml
# Wait for the generated CRDs to be created
sleep 5

# Create the AKS cluster
kubectl apply -k .
