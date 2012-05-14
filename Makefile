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
GMVMACBUILDDIST=$(GMVDIST)/inst

BUILD=$(BASEDIR)/build
BUILDDIST=$(BUILD)/egg-dist
ETC=$(BASEDIR)/etc

#PYTHONBIN=/homespace/gaubert/python2.7/bin/python #TCE machine
PYTHONBIN=python #MacOSX machine
#PYTHONWINBIN=python
PYTHONWINBIN=/cygdrive/d/Programs/python2.7/python.exe #for my windows machine at work
#PYTHONWINBIN=/c/Program\ Files/Python2.7/python.exe #windows laptop
PYTHONVERSION=2.7

MAKENSIS=/cygdrive/d/Programs/NSIS/makensis.exe #windows work
#MAKENSIS=/c/Program\ Files/NSIS/makensis.exe #windows laptop

#VERSION is in gmv_cmd.py as GMVAULT_VERSION
GMVVERSION=$(shell python $(BASEDIR)/etc/utils/find_version.py $(BASEDIR)/src/gmv/gmv_cmd.py)
GMVDISTNAME=gmvault-v$(GMVVERSION)


all: gmv-linux-dist

version:
	@echo $(GMVVERSION)

init:
	mkdir -p $(GMVDIST)
	mkdir -p $(GMVBUILDDIST)

gmv-egg-dist: init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/src $(GMVDIST)
	cp -R $(BASEDIR)/setup.py $(GMVDIST)
	cp -R $(BASEDIR)/README.md $(GMVDIST)
	cp -R $(BASEDIR)/README.md $(GMVDIST)/README.txt
	cp $(BASEDIR)/setup.py $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py bdist_egg -b /tmp/build -p $(GMVDISTNAME) -d ../../$(GMVBUILDDIST) 
	echo "distribution stored in $(GMVBUILDDIST)"

gmv-src-dist: clean init
	# make src dist that can be downloaded
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/src $(GMVDIST)
	cp $(BASEDIR)/setup.py $(GMVDIST)
	cp $(BASEDIR)/MANIFEST.in $(GMVDIST)
	cp $(BASEDIR)/README.md $(GMVDIST)/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)/RELEASE-NOTE.txt
	# copy scripts in dist
	cp -R $(BASEDIR)/etc $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py sdist -d ../$(GMVBUILD) 
	@echo ""
	@echo "=================================================================="
	@echo ""
	@echo "Distribution stored in $(GMVBUILD)"
	@echo ""
	@echo "=================================================================="

gmv-pypi-dist: clean init
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	cp -R $(BASEDIR)/src $(GMVDIST)
	cp $(BASEDIR)/setup.py $(GMVDIST)
	cp $(BASEDIR)/MANIFEST.in $(GMVDIST)
	cp -R $(BASEDIR)/README.md $(GMVDIST)/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)/RELEASE-NOTE.txt
	# copy scripts in dist
	cp -R $(BASEDIR)/etc $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup.py sdist -d ../$(GMVBUILD) 
	@echo ""
	@echo "=================================================================="
	@echo ""
	@echo "Distribution stored in $(GMVBUILD)"
	@echo "To register on pypi cd ./build; tar zxvf gmvault-1.0-beta.tar.gz; cd gmvault-1.0-beta ; python setup.py register sdist upload"
	@echo "If you do not change the version number, you will have to delete the release from the pypi website http://pypi.python.org and register it again"
	@echo ""
	@echo "=================================================================="

gmv-linux-dist: clean init 
	# need to copy sources in distributions as distutils does not always support symbolic links (pity)
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)
	#add GMVault sources
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)/lib/gmv
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)/$(GMVDISTNAME)/lib
	#add python interpreter with virtualenv
	cd $(GMVDIST)/$(GMVDISTNAME)/lib; virtualenv --no-site-packages python-lib
	# copy local version of atom to avoid compilation problems
	cp $(BASEDIR)/etc/libs/atom.tar.gz $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/lib/python$(PYTHONVERSION)/site-packages/
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/lib/python$(PYTHONVERSION)/site-packages; tar zxvf atom.tar.gz; rm -f atom.tar.gz
	# install rest of the packages normally
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/bin; ./pip install logbook
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/bin; ./pip install IMAPClient
	cd $(GMVDIST)/$(GMVDISTNAME)/lib/python-lib/bin; ./pip install gdata
	# copy shell scripts in dist/bin
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)/bin
	cp -R $(BASEDIR)/etc/scripts/gmvault $(GMVDIST)/$(GMVDISTNAME)/bin
	cp -R $(BASEDIR)/README.md $(GMVDIST)/$(GMVDISTNAME)/bin/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)$(GMVDISTNAME)/bin/RELEASE-NOTE.txt
	cd $(GMVDIST); tar zcvf ./$(GMVDISTNAME)-linux-i686.tar.gz ./$(GMVDISTNAME)
	@echo ""
	@echo "=================================================================="
	@echo ""
	@echo "distribution $(GMVDISTNAME)-linux-i686.tar.gz stored in $(GMVDIST)"
	@echo ""
	@echo "=================================================================="

gmv-mac-dist: clean init
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)
	cp $(BASEDIR)/src/setup_mac.py $(GMVDIST)
	cd $(GMVDIST); $(PYTHONBIN) setup_mac.py py2app
	mkdir -p $(GMVDIST)/$(GMVDISTNAME)/bin ; mkdir -p $(GMVDIST)/$(GMVDISTNAME)/lib
	cp $(BASEDIR)/etc/scripts/gmvault_mac $(GMVDIST)/$(GMVDISTNAME)/bin/gmvault
	cp -R $(BASEDIR)/README.md $(GMVDIST)/$(GMVDISTNAME)/bin/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)/$(GMVDISTNAME)/bin/RELEASE-NOTE.txt
	cp -R $(GMVDIST)/dist/gmv_cmd.app $(GMVDIST)/$(GMVDISTNAME)/lib
	cd $(GMVDIST); tar zcvf ./$(GMVDISTNAME)-macosx-intel.tar.gz ./$(GMVDISTNAME)
	@echo ""
	@echo "========================================="
	@echo ""
	@echo "distribution $(GMVDISTNAME)-macosx-intel.tar.gz stored in $(GMVDIST)"
	@echo ""
	@echo "========================================="

gmv-win-dist: init 
	mkdir -p $(GMVWINBUILDDIST)
	cp -R $(BASEDIR)/src/gmv $(GMVDIST)
	cp $(BASEDIR)/src/setup_win.py $(GMVDIST)/gmv
	cd $(GMVDIST)/gmv; $(PYTHONWINBIN) setup_win.py py2exe -d ../../$(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/scripts/gmvault.bat $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/scripts/gmvault-shell.bat $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/scripts/gmv-msg.bat $(GMVWINBUILDDIST)
	cp -R $(BASEDIR)/README.md $(GMVDIST)/$(GMVDISTNAME)/bin/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)$(GMVDISTNAME)/bin/RELEASE-NOTE.txt
	echo "distribution available in $(GMVWINBUILDDIST)"

gmv-make-win-installer: gmv-win-dist
	cp $(BASEDIR)/etc/nsis-install/gmvault_setup.nsi $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/images/*.bmp $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/images/*.ico $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/License.rtf $(GMVWINBUILDDIST)
	echo "=== call gmvault_setup.nsi in $(GMVWINBUILDDIST) ==="
	ls -la > /tmp/res.txt
	cd $(GMVWINBUILDDIST); $(MAKENSIS) ./gmvault_setup.nsi
	mv $(GMVWINBUILDDIST)/gmvault_setup.exe $(GMVWINBUILDDIST)/gmvault_setup_v$(GMVVERSION).exe
	echo "gmvault_setup_v$(GMVVERSION).exe available in $(GMVWINBUILDDIST)"


clean: clean-build
	cd $(GMVDIST); rm -Rf build; rm -Rf gmvault.egg-info; rm -f setup*.py ; rm -Rf dist ; rm -Rf src; rm -f README* ;rm -Rf GMVault.egg-info; rm -Rf gmv; rm -Rf scripts; rm -f *.tar.gz

clean-build:
	cd $(GMVBUILD); rm -Rf egg-dist; 
	rm -Rf $(GMVDIST)/$(GMVDISTNAME)
	rm -Rf $(GMVWINBUILDDIST)

    
