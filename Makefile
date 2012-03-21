#
#============================================================================
# File: Simple Makefile for gmvault project
# author: guillaume.aubert@gmail.com
#=============================================================================
BASEDIR=.
# internal dirs
DISTS=$(BASEDIR)/dists

#GMVDist info
GMVDIST=$(BASEDIR)/dist
GMVBUILD=$(BASEDIR)/build
GMVBUILDDIST=$(GMVDIST)/build/egg-dist
GMVWINBUILDDIST=$(GMVDIST)/inst

BUILD=$(BASEDIR)/build
BUILDDIST=$(BUILD)/egg-dist
ETC=$(BASEDIR)/etc

#PYTHONBIN=/homespace/gaubert/python2.7/bin/python #TCE machine
#PYTHONWINBIN=python
#PYTHONWINBIN=/cygdrive/d/Programs/python2.7/python.exe #for my machine at work
PYTHONWINBIN=/c/Program\ Files/Python2.7/python.exe #windows laptop
PYTHONVERSION=2.7

#MAKENSIS=/cygdrive/d/Programs/NSIS/makensis.exe #windows work
MAKENSIS=/c/Program\ Files/NSIS/makensis.exe #windows laptop

GMVVERSION=0.5
GMVDISTNAME=gmvault-$(GMVVERSION)

all: gmv-linux-dist

init:
	mkdir -p $(GMVDIST)
	mkdir -p $(GMVBUILDDIST)

gmv-egg-dist: init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)
	cp $(BASEDIR)/src/setup.py $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py bdist_egg -b /tmp/build -p $(GMVDISTNAME) -d ../../$(GMVBUILDDIST) 
	echo "distribution stored in $(GMVBUILDDIST)"

gmv-src-dist: clean init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)
	cp $(BASEDIR)/src/setup.py $(GMVDIST)
	# copy scripts in dist
	#cp -R $(BASEDIR)/etc/scripts $(GMVDIST)
	#cp -R $(BASEDIR)/etc/conf $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py sdist -d ../$(GMVBUILD) 
	echo "distribution stored in $(GMVBUILD)"

gmv-linux-dist: clean init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)
	#add GMVault sources
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)/lib/gmv
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)/$(GMVDISTNAME)/lib
	#add python interpreter with virtualenv
	cd $(GMVDIST)/$(GMVDISTNAME)/lib; virtualenv --no-site-packages python-lib
	# copy local version of atom to avoid compilation problems
	cp $(BASEDIR)/etc/libs/atom.tar.gz $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/lib/python2.7/site-packages/
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/lib/python2.7/site-packages; tar zxvf atom.tar.gz; rm -f atom.tar.gz
	# install rest of the packages normally
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/bin; ./pip install logbook
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/bin; ./pip install IMAPClient
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/bin; ./pip install gdata
	# copy shell scripts in dist/bin
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)/bin
	cp -R $(BASEDIR)/etc/scripts/gmvault $(GMVDIST)/$(GMVDISTNAME)/bin
	cd $(GMVDIST); tar zcvf ./$(GMVDISTNAME).tar.gz ./$(GMVDISTNAME)
	echo "distribution stored in $(GMVDISTNAME)"

gmv-win-dist: init 
	mkdir -p $(GMVWINBUILDDIST)
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)
	cp $(BASEDIR)/src/setup_win.py $(GMVDIST)/gmv
	cd $(GMVDIST)/gmv; $(PYTHONWINBIN) setup_win.py py2exe -d ../../$(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/scripts/gmvault.bat $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/scripts/gmvault-shell.bat $(GMVWINBUILDDIST)
	echo "distribution available in $(GMVWINBUILDDIST)"

gmv-make-win-installer: gmv-win-dist
	cp $(BASEDIR)/etc/nsis-install/gmvault_setup.nsi $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/images/*.bmp $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/images/*.ico $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/License.rtf $(GMVWINBUILDDIST)
	echo "=== call gmvault_setup.nsi in $(GMVWINBUILDDIST) ==="
	ls -la > /tmp/res.txt
	cd $(GMVWINBUILDDIST); $(MAKENSIS) ./gmvault_setup.nsi
	echo "gmvault_setup.exe available in $(GMVWINBUILDDIST)"


clean: clean-build
	cd $(GMVDIST); rm -Rf build; rm -Rf gmvault.egg-info; rm -f *.py; rm -Rf GMVault.egg-info; rm -Rf gmv; rm -Rf scripts; rm -f *.tar.gz

clean-build:
	cd $(GMVBUILD); rm -Rf egg-dist; 
	rm -Rf $(GMVDIST)/$(GMVDISTNAME)
	rm -Rf $(GMVWINBUILDDIST)

    
