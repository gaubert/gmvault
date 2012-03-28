# Gmvault: Backup and restore your gmail account

Gmvault is a tool for backing up your gmail account and never loose email correspondence.
Gmvault is open source and under GPLv3.

# Quick Start

## Installation

You can download one of the "binary" distribution from (github.com/download) for the platform of your choice.
You can also install the software from the source from (github.com/gaubert/gmvault).

## Windows install

Once installed launch gmvault-shell.bat (there should be a shortcut on your desktop).
The shell sets for you the environement to launch seamlessly gmvault.

Go to the gmvault 2 mins start to learn how to pilot gmvault.

## Linux and Mac OS X install

Untar the binary tarball distribution and go to the GMVAULT_HOME/bin dir to launch gmvault.

## Install from the sources

python setup.py blahhhh.

## gmvault 2 mins start 

Gmvault is a user-frendly command-line tool. It tries to set all the necessary defaults to be self explanatory.

### Authentication

Gmvault allow users to use a XOAuth token or your gmail login password. The XOAuth authentication is the recommended way to access your account. 
This method is activated by default. After the first authentication for a given account, the XOAuth token is stored in $HOME/.gmvault and will be used for consequent authentications. 

The following example uses XOAuth to access foo.bar@gmail.com
$>gmvault sync foo.bar@gmail.com

With the --passwd option, you can use your gmail login and password for a quick test or if you cannot use XOAuth. 
You will then enter in an interactive session to enter your password. By default you password is not saved, but you can use the option to do it. Your password will be stored encrypted but please avoid to use this option if possible.






