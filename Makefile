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
#PYTHONWINBIN=/drives/d/Programs/python2.7/python.exe #for my windows machine at work
#PYTHONWINBIN=/c/Program\ Files/Python2.7/python.exe #windows laptop
PYTHONWINBIN=/c/Python27/python.exe #windows laptop
PYTHONVERSION=2.7

PYINSTALLERMAC=/Library/Frameworks/Python.framework/Versions/2.7/bin/pyinstaller
PYINSTALLERWIN=c:/Python27/Scripts/pyinstaller.exe

#MAKENSIS=/cygdrive/d/Programs/NSIS/makensis.exe #windows work
MAKENSIS=c:/Program\ Files/NSIS/makensis.exe #windows laptop

#VERSION is in gmv_cmd.py as GMVAULT_VERSION
GMVVERSION=$(shell python $(BASEDIR)/etc/utils/find_version.py $(BASEDIR)/src/gmv/gmvault_utils.py)
GMVDISTNAME=gmvault-v$(GMVVERSION)


all: gmv-src-dist

version:
	@echo $(GMVVERSION)

init:
	mkdir -p $(GMVDIST)
	mkdir -p $(GMVBUILDDIST)

list:
	@echo "=== Available Make targets:"
	@echo "--- gmv-src-dist, gmv-pypi-dist, gmv-mac-dist, gmv-win-dist, gmv-win-installer" 

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
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)/$(GMVDISTNAME)/bin/RELEASE-NOTE.txt
	cd $(GMVDIST); tar zcvf ./$(GMVDISTNAME)-linux-i686.tar.gz ./$(GMVDISTNAME)
	@echo ""
	@echo "=================================================================="
	@echo ""
	@echo "distribution $(GMVDISTNAME)-linux-i686.tar.gz stored in $(GMVDIST)"
	@echo ""
	@echo "=================================================================="

gmv-mac-dist: clean init
	$(PYINSTALLERMAC) --onefile --name gmvault --distpath=$(GMVDIST)/$(GMVDISTNAME)  $(BASEDIR)/src/gmv_runner.py
	cp -R $(BASEDIR)/README.md $(GMVDIST)/$(GMVDISTNAME)/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)/$(GMVDISTNAME)/RELEASE-NOTE.txt
	cd $(GMVDIST); tar zcvf ./$(GMVDISTNAME)-macosx-intel.tar.gz ./$(GMVDISTNAME)
	@echo ""
	@echo "========================================="
	@echo ""
	@echo "distribution $(GMVDISTNAME)-macosx-intel.tar.gz stored in $(GMVDIST)"
	@echo ""
	@echo "========================================="

gmv-win-dist: clean init
	$(PYINSTALLERWIN) --onefile --name gmv_runner --distpath=$(GMVWINBUILDDIST) $(BASEDIR)/src/gmv_runner.py
	cp $(BASEDIR)/etc/scripts/gmvault.bat $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/scripts/gmvault-shell.bat $(GMVWINBUILDDIST)
	cd .; $(PYTHONWINBIN) $(BASEDIR)/etc/utils/add_version.py $(BASEDIR)/etc/scripts/gmv-msg.bat $(GMVWINBUILDDIST)/gmv-msg.bat $(GMVVERSION)
	cp $(BASEDIR)/README.md $(GMVWINBUILDDIST)/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVWINBUILDDIST)
	#unix2dos $(GMVWINBUILDDIST)/README.txt $(GMVWINBUILDDIST)/RELEASE-NOTE.txt
	echo "distribution available in $(GMVWINBUILDDIST)"

gmv-win-installer: gmv-win-dist
	cp $(BASEDIR)/etc/nsis-install/gmvault_setup.nsi $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/images/*.bmp $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/images/gmv-icon.ico $(GMVWINBUILDDIST)
	cp $(BASEDIR)/etc/nsis-install/License.rtf $(GMVWINBUILDDIST)
	echo "=== call gmvault_setup.nsi in $(GMVWINBUILDDIST) ==="
	ls -la > /tmp/res.txt
	cd $(GMVWINBUILDDIST); $(MAKENSIS) ./gmvault_setup.nsi
	mv $(GMVWINBUILDDIST)/gmvault_installer.exe $(GMVWINBUILDDIST)/gmvault_installer_v$(GMVVERSION).exe
	echo "gmvault_installer_v$(GMVVERSION).exe available in $(GMVWINBUILDDIST)"


clean: clean-build
	mkdir -p $(GMVDIST)
	rm -Rf $(GMVDIST)/*

clean-build:
	mkdir -p $(GMVBUILD)
	rm -Rf $(GMVBUILD)/egg-dist; 
	rm -Rf $(GMVDIST)/$(GMVDISTNAME)
	rm -Rf $(GMVWINBUILDDIST)

