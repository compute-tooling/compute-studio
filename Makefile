
dist-build:
	# template command:
	# docker build --no-cache --build-arg TAG=$(TAG) -t comp/{project_name}_tasks:$(TAG) --file dockerfiles/projects/Dockerfile.{project_name}_tasks ./

	cd distributed && \
	docker build -t comp/distributed:$(TAG) ./ -f dockerfiles/Dockerfile && \
	docker build --build-arg TAG=$(TAG) -t comp/flask:$(TAG) --file dockerfiles/Dockerfile.flask ./ && \
	docker build --build-arg TAG=$(TAG) -t comp/celerybase:$(TAG) --file dockerfiles/Dockerfile.celerybase ./ && \
	docker build --no-cache --build-arg TAG=$(TAG) -t comp/compbaseball_tasks:$(TAG) --file dockerfiles/projects/Dockerfile.compbaseball_tasks ./

dist-push:
	cd distributed && \
	docker push comp/distributed:$(TAG) && \
	docker push comp/flask:$(TAG) && \

dist-test:
	cd distributed && \
	docker-compose rm -f && \
	docker-compose run flask py.test -s -v && \
	docker-compose rm -f

webapp-build:
	docker build -t comp/web:$(TAG) ./

webapp-push:
	docker tag comp/web:$(TAG) registry.heroku.com/compmodels/web
	docker push registry.heroku.com/compmodels/web

webapp-release:
	heroku container:release web -a compmodels
