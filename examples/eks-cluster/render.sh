#!/usr/bin/env bash
cd $(dirname $(realpath $0))
exec crossplane render composite.yaml composition.yaml functions.yaml
