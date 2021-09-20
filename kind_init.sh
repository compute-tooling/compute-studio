#!/usr/bin/env bash

kind create cluster --name cs --config kind-config.yaml
kubectl config use-context kind-cs
kubectl label nodes cs-worker component=api
kubectl label nodes cs-worker2 component=model
kubectl label nodes cs-worker3 component=web
