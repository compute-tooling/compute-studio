kube-config:
	cd distributed && \
		python app_writer.py --config worker_config.kube.json

workers:
	cd distributed && \
	    docker-compose -f docker-compose.yml `python app_writer.py --config worker_config.kube.json` build && \
	    python gcr_tag.py --tag $(TAG) --host gcr.io --project comp-workers --config worker_config.kube.json

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
	docker build -t comporg/web:$(TAG) ./

webapp-push:
	docker tag comporg/web:$(TAG) registry.heroku.com/compmodels/web
	docker push registry.heroku.com/compmodels/web

webapp-release:
	heroku container:release web -a compmodels

webapp-test-push:
	docker tag comporg/web:$(TAG) registry.heroku.com/compmodels-test/web
	docker push registry.heroku.com/compmodels-test/web

webapp-test-release:
	heroku container:release web -a compmodels-test
