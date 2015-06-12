PROJ_DIR    = $(abspath ..)

NAME        = $(shell cat $(PROJ_DIR)/bundle.json | sed -n 's/"name"//p' | tr -d '", :')
VERSION     = $(shell cat $(PROJ_DIR)/bundle.json | sed -n 's/"version"//p' | tr -d '", :')

PROJECT     = sanji-bundle-$(NAME)
DEBVERSION  = 1
DIST        ?= unstable

STAGING_DIR = $(abspath $(PROJECT)-$(VERSION))
UPSTREAM_ARCHIVE = $(PROJECT)-$(VERSION).tar.gz

FILES = \
	$(STAGING_DIR)/debian/changelog \
	$(STAGING_DIR)/debian/compat \
	$(STAGING_DIR)/debian/control \
	$(STAGING_DIR)/debian/copyright \
	$(STAGING_DIR)/debian/docs \
	$(STAGING_DIR)/debian/postinst \
	$(STAGING_DIR)/debian/README \
	$(STAGING_DIR)/debian/rules \
	$(STAGING_DIR)/debian/source/format

.PHONY: all build

all: build

build: extract-upstream $(FILES)
	cd $(STAGING_DIR) && \
	dpkg-buildpackage -us -uc -rfakeroot

$(STAGING_DIR)/debian/%: $(PROJ_DIR)/build-deb/debian/%
	mkdir -p $(dir $@)
	cp $< $@

extract-upstream:
	tar zxf $(PROJ_DIR)/$(UPSTREAM_ARCHIVE)

changelog:
	dch -v $(VERSION)-$(DEBVERSION) -D $(DIST) -M -u low \
		--release-heuristic log

clean:
	rm -rf $(STAGING_DIR) $(PROJECT)-* $(PROJECT)_*
