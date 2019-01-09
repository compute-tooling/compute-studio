
dist-build:
	# template command:
	# docker build --no-cache --build-arg TAG=$(TAG) -t comporg/{project_name}_tasks:$(TAG) --file dockerfiles/projects/Dockerfile.{project_name}_tasks ./

	cd distributed && \
	docker build -t comporg/distributed:$(TAG) ./ -f dockerfiles/Dockerfile && \
	docker build --build-arg TAG=$(TAG) -t comporg/flask:$(TAG) --file dockerfiles/Dockerfile.flask ./ && \
	docker build --build-arg TAG=$(TAG) -t comporg/celerybase:$(TAG) --file dockerfiles/Dockerfile.celerybase ./ && \
	docker build --no-cache --build-arg TAG=$(TAG) -t comporg/compbaseball_tasks:$(TAG) --file dockerfiles/projects/Dockerfile.compbaseball_tasks ./

dist-push:
	cd distributed && \
	docker push comporg/distributed:$(TAG) && \
	docker push comporg/flask:$(TAG) && \
	docker push comporg/celerybase:$(TAG) && \
	docker push comporg/compbaseball_tasks:$(TAG)

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
