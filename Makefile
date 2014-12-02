all: pylint test

pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=route

.PHONY: pylint test
