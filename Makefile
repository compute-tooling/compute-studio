
dist-build:
	cd distributed && \
	docker build -t comp/distributed:$(TAG) ./ -f dockerfiles/Dockerfile && \
	docker build --build-arg TAG=$(TAG) -t comp/flask:$(TAG) --file dockerfiles/Dockerfile.flask ./ && \
	docker build --build-arg TAG=$(TAG) -t comp/celerybase:$(TAG) --file dockerfiles/Dockerfile.celerybase ./ && \

dist-push:
	cd distributed && \
	docker push comp/distributed:$(TAG) && \
	docker push comp/flask:$(TAG) && \
	docker push comp/taxcalc_tasks:$(TAG)

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
