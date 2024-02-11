#!/usr/bin/env bash

# kubectl config use-context kind-cs &&

    source env.sh && \
    export TAG=$1 && \
    kubectl create namespace web && \
    kubectl create secret generic web-db-secret \
        --from-literal=username=postgres \
        --from-literal=password=$(cs secrets get HDOUPE_POSTGRES_PASSWORD) \
        --from-literal=database=postgres \
        --from-literal=host=db \
        --namespace web && \


    cs webapp build --dev && \
    cs webapp push --use-kind && \
    cs webapp config -o - --update-db --dev | kubectl apply --namespace web -f -

