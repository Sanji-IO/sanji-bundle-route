
# Where to put executable commands/icons/conf on 'make install'?
SANJI_VER   = 1.0
RESOURCE    = network/route
LIBDIR      = $(DESTDIR)/usr/lib/sanji-$(SANJI_VER)/$(RESOURCE)
TMPDIR      = $(DESTDIR)/tmp

FILES       = bundle.json route.py
DIRS        = data ip


all:
	mkdir -p $(CURDIR)/packages
	pip install -r $(CURDIR)/packages/requirements.txt --download \
		$(CURDIR)/packages || true
	cp -a $(CURDIR)/requirements.txt \
		$(CURDIR)/packages/bundle-requirements.txt

clean:
	# do nothing

distclean: clean


install: all
	install -d $(LIBDIR)
	install -d $(TMPDIR)
	install $(FILES) $(LIBDIR)
	cp -a $(DIRS) $(LIBDIR)
	cp -a packages $(TMPDIR)

uninstall:
	-rm $(addprefix $(LIBDIR)/,$(FILES))
