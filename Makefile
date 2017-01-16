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

PYINSTALLERMAC=/usr/local/bin/pyinstaller
PYINSTALLERLIN=pyinstaller
PYINSTALLERWIN=c:/Python27/Scripts/pyinstaller.exe

#MAKENSIS=/cygdrive/d/Programs/NSIS/makensis.exe #windows work
MAKENSIS=c:/Program\ Files/NSIS/makensis.exe #windows laptop
MAKENSIS=c:/Program\ Files\ \(x86\)/NSIS/makensis.exe #windows 10 version

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

gmv-lin-dist: clean init
	$(PYINSTALLERLIN) --onefile --clean --name gmvault --distpath=$(GMVDIST)/$(GMVDISTNAME)  $(BASEDIR)/gmvault-pyinstaller.spec
	cp -R $(BASEDIR)/README.md $(GMVDIST)/$(GMVDISTNAME)/README.txt
	cp $(BASEDIR)/RELEASE-NOTE.txt $(GMVDIST)/$(GMVDISTNAME)/RELEASE-NOTE.txt
	cd $(GMVDIST); tar zcvf ./$(GMVDISTNAME)-lin64.tar.gz ./$(GMVDISTNAME)
	@echo ""
	@echo "========================================="
	@echo ""
	@echo "distribution $(GMVDISTNAME)-lin64.tar.gz stored in $(GMVDIST)"
	@echo ""
	@echo "========================================="

gmv-mac-dist: clean init
	$(PYINSTALLERMAC) --onefile --clean --name gmvault --distpath=$(GMVDIST)/$(GMVDISTNAME)  $(BASEDIR)/gmvault-pyinstaller.spec
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
	#$(PYINSTALLERWIN) --onefile --clean --name gmv_runner --distpath=$(GMVWINBUILDDIST) $(BASEDIR)/src/gmv_runner.py
	$(PYINSTALLERWIN) --name gmv_runner --distpath=$(GMVWINBUILDDIST) $(BASEDIR)/gmvault-win-pyinstaller.spec
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

