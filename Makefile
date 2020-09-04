PROJECT ?= cs-workers-dev
CONFIG ?= worker_config.dev.yaml
MODE ?= test
MODELS ?= ""

kube-config:
	cd distributed && \
	    python cs_cluster.py --config $(CONFIG) --project $(PROJECT) --models $(MODELS) --dry-run

workers:
	cd distributed && \
	    python cs_cluster.py --config $(CONFIG) --project $(PROJECT) --models $(MODELS) --build

workers-base-only:
	cd distributed && \
	    python cs_cluster.py --config $(CONFIG) --project $(PROJECT) --models $(MODELS) --build-base-only

workers-apply:
	cd distributed && \
		kubectl apply -f kubernetes/ && \
		kubectl apply -f kubernetes/apps/

webapp-build:
	docker build -t webbase:latest -f Dockerfile.base ./ && \
	docker build -t web:$(TAG) ./

webapp-push:
	docker tag web:$(TAG) registry.heroku.com/compute-studio/web
	docker push registry.heroku.com/compute-studio/web

webapp-release:
	heroku container:release web -a compute-studio

webapp-test-push:
	docker tag web:$(TAG) registry.heroku.com/compute-studio-test/web
	docker push registry.heroku.com/compute-studio-test/web

webapp-test-release:
	heroku container:release web -a compute-studio-test
