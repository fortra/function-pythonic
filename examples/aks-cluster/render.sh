#!/usr/bin/env bash

# In one terminal
# PYTHONPATH=. function-pythonic --insecure --debug

# In another terminal:

cd $(dirname $(realpath $0))
exec crossplane render xr.yaml composition.yaml functions.yaml
