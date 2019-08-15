PROJECT ?= comp-workers
CONFIG ?= worker_config.prod.json
MODE ?= test
NEW_RELIC_TOKEN ?= `cat ~/.newrelic-$(MODE)`

kube-config:
	cd distributed && \
		python app_writer.py --config $(CONFIG) --project $(PROJECT)

workers:
	cd distributed && \
	    docker-compose -f docker-compose.yml `python app_writer.py --config $(CONFIG) --project $(PROJECT)` build && \
	    python gcr_tag.py --tag $(TAG) --host gcr.io --project $(PROJECT) --config $(CONFIG)

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
	docker tag web:$(TAG) registry.heroku.com/compmodels/web
	docker push registry.heroku.com/compmodels/web

webapp-release:
	heroku container:release web -a compmodels

webapp-test-push:
	docker tag web:$(TAG) registry.heroku.com/compmodels-test/web
	docker push registry.heroku.com/compmodels-test/web

webapp-test-release:
	heroku container:release web -a compmodels-test
