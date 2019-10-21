PROJECT ?= comp-workers
CONFIG ?= worker_config.prod.json
MODE ?= test
NEW_RELIC_TOKEN ?= `cat ~/.newrelic-$(MODE)`
MODELS ?= ""

kube-config:
	cd distributed && \
		python app_writer.py --config $(CONFIG) --project $(PROJECT) --models $(MODELS)

workers:
	cd distributed && \
	    python app_writer.py --config $(CONFIG) --project $(PROJECT) --models $(MODELS)

workers-apply:
	cd distributed && \
		kubectl apply -f kubernetes/ && \
		kubectl apply -f kubernetes/apps/

dist-test:
	cd distributed && \
	docker-compose rm -f && \
	docker-compose run flask py.test -s -v && \
	docker-compose rm -f

webapp-build:
	docker build -t webbase:latest -f Dockerfile.base ./ && \
	docker build --build-arg NEW_RELIC_TOKEN=$(NEW_RELIC_TOKEN) -t web:$(TAG) ./

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
