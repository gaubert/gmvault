#=============================================================================
# File: Simple Makefile for gmvault project
# author: guillaume.aubert@gmail.com
#=============================================================================
BASEDIR=.
# internal dirs
DISTS=$(BASEDIR)/dists

#GMVDist info
GMVDIST=$(DISTS)
GMVBUILD=$(GMVDIST)/build
GMVBUILDDIST=$(GMVDIST)/build/egg-dist

BUILD=$(BASEDIR)/build
BUILDDIST=$(BUILD)/egg-dist
ETC=$(BASEDIR)/etc

PYTHONBIN=/usr/bin/python
PYTHONVERSION=2.6

GMVVERSION=0.5
GMVDISTNAME=gmvault-$(GMVVERSION)

all: gmv-src-dist

init:
	mkdir -p $(GMVDIST)
	mkdir -p $(GMVBUILDDIST)

gmv-egg-dist: init 
	cp -R $(BASEDIR)/src/ctbto $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py bdist_egg -b /tmp/build -p $(GMVDISTNAME) -d ../../$(GMVBUILDDIST) 
	echo "distribution stored in $(GMVBUILDDIST)"

gmv-src-dist: clean init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)
	# copy scripts in dist
	#cp -R $(BASEDIR)/etc/scripts $(GMVDIST)
	#cp -R $(BASEDIR)/etc/conf $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py sdist -d ../../$(GMVBUILD) 
	echo "distribution stored in $(GMVBUILD)"

gmv-ppath-dist: clean init conf-src-egg-dist 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	mkdir -p $(GMVDIST)/GMVault-$(GMVVERSION)
	#add GMVault sources
	mkdir -p $(GMVDIST)/GMVault-$(GMVVERSION)/lib/gmv
	cp -R $(BASEDIR)/src/gmv $(RNDIST)/GMVault-$(GMVVERSION)/lib
	# copy shell scripts in dist/bin
	mkdir -p $(GMVDIST)/RNPicker-$(GMVVERSION)/bin
	cp -R $(BASEDIR)/etc/scripts/generate_NG_arr_with_python_path $(RNDIST)/RNPicker-$(RNVERSION)/bin/generate_NG_arr
	cp -R $(BASEDIR)/etc/scripts/generate_products_and_email $(RNDIST)/RNPicker-$(RNVERSION)/bin/generate_products_and_email
	# copy conf files
	cp -R $(BASEDIR)/etc/conf $(RNDIST)/RNPicker-$(RNVERSION)
	#add dependency: conf-egg-dist 
	#cp $(CONFDIST)/build/conf-1.1-py$(PYTHONVERSION).egg $(RNDIST)/RNPicker-$(RNVERSION)/lib
	#cd $(RNDIST); tar zcvf ./RNPicker-$(RNVERSION).tar.gz ./RNPicker-$(RNVERSION)
	#echo "distribution stored in $(RNDIST)"
	#add dependency: conf-src-egg-dist 
	cp -R $(CONFBUILDDIST)/org $(RNDIST)/RNPicker-$(RNVERSION)/lib
	cd $(RNDIST); tar zcvf ./RNPicker-$(RNVERSION).tar.gz ./RNPicker-$(RNVERSION)
	echo "distribution stored in $(RNDIST)"

conf-src-dist: clean init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/conf-src/org $(CONFDIST)
	cd $(CONFDIST); $(PYTHONBIN) setup.py sdist -d ../../$(CONFBUILD) 
	echo "distribution stored in $(CONFBUILD)"

conf-src-egg-dist: init
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	mkdir -p $(CONFBUILDDIST)
	cp -R $(BASEDIR)/conf-src/org $(CONFBUILDDIST)
	echo "distribution stored in $(CONFBUILDDIST)"

conf-egg-dist: init 
	cp -R $(BASEDIR)/conf-src/org $(CONFDIST)
	cd $(CONFDIST); $(PYTHONBIN) setup.py bdist_egg -b /tmp/build -p $(CONFDISTNAME) -d ../../$(CONFBUILDDIST) 
	echo "distribution stored in $(CONFBUILDDIST)"

clean: clean-build
	cd $(GMVDIST); rm -Rf build; rm -Rf GMVault.egg-info; rm -Rf ctbto; rm -Rf conf; rm -Rf scripts

clean-build:
	cd $(GMVBUILD); rm -Rf egg-dist; 
	rm -Rf $(GMVDIST)/GMVault-*

    
