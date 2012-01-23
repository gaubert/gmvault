import os
from setuptools import setup, find_packages
version = '0.5'
README = os.path.join(os.path.dirname(__file__), '../README')
print(README)
long_description = open(README).read() + 'nn'
setup(name='gmvault',
      version=version,
      description=("gmvault - Backup and restore your Gmail emails"),
      long_description=long_description,
      classifiers=[
        "Programming Language :: Python",
        ("Topic :: Util :: Libraries :: Python Modules"),
        ],
      keywords='configuration, resources',
      author='Guillaume Aubert',
      author_email='guillaume.aubert@gmail.com',
      url='www.gmvault.org',
      license='Apache 2.0',
      packages=find_packages(),
      package_data=dict(gmvault=['src/*.py']),
      #package_data={'org.ctbto.conf': ['tests/test.config','tests/foo.config','tests/rn.par','tests/rn1.par']},
      #data_files=[('/tmp/py-tests',['/home/aubert/dev/src-reps/java-balivernes/RNpicker/dists/conf-dist/tests/foo.config','/home/aubert/dev/src-reps/java-balivernes/RNpicker/dists/conf-dist/tests/test.config'])],
      install_requires=['Logbook>=0.3', 'IMAPClient']
      )
