
FILES = README.md bundle.json route.py __init__.py requirements.txt
DIRS = data ip

all: pylint test

pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=route

deb:
	mkdir -p deb
	cp -a debian deb/
	cp -a debian.mk deb/Makefile
	cp -a README.md $(FILES) $(DIRS) deb/
	(cd deb; \
		dpkg-buildpackage -us -uc -rfakeroot;)

clean:
	rm -rf deb

.PHONY: pylint test
