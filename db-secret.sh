kubectl create secret generic web-db-secret \
  --from-literal=username=postgres \
  --from-literal=password=$(cs secrets get HDOUPE_POSTGRES_PASSWORD) \
  --from-literal=database=postgres \
  --from-literal=host=db \
  --namespace web

