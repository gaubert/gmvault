# Gmvault: Backup and restore your gmail account



Gmvault is a tool for backing up your gmail account and never lose email correspondence.
Gmvault is open source and under GNU-AGPL-3.0.

For further info go to [gmvault.org] (http://gmvault.org)

# Contribute

[![Bountysource](https://www.bountysource.com/badge/tracker?tracker_id=56851)](https://www.bountysource.com/trackers/56851-gaubert-gmvault?utm_source=56851&utm_medium=shield&utm_campaign=TRACKER_BADGE)

1. Check for open issues or open a fresh issue to start a discussion around a feature idea or a bug. There will be a Contributor Friendly tag for issues that should be ideal for people who are not very familiar with the codebase yet.
2. Fork the repository on Github to start making your changes to the **master** branch (or branch off of it).
3. Write a test which shows that the bug was fixed or that the feature works as expected.
4. Send a pull request and bug the maintainer until it gets merged and published. :) Make sure to add yourself to AUTHOR.

# Quick Start

## Installation

You can download one of the "binary" distribution from (http://gmvault.org/download.html) for the platform of your choice.
You can also install the software from the source from (http://github.com/gaubert/gmvault).

## Windows install

Once installed, launch gmvault-shell.bat (there should be a shortcut on your desktop).
The shell sets the environment so you can seamlessly launch gmvault.

Go to the [gmvault 2 mins start](#gmvault-2-mins-start) to learn how to pilot gmvault.

## Linux and Mac OS X install

Untar the binary tarball distribution and go to the GMVAULT_HOME/bin dir to launch gmvault.

## Install from the sources

    python setup.py install

## Install from PyPi

    pip install gmvault

or

    easy_install gmvault

## gmvault 2 mins start 

Gmvault is a user-frendly command-line tool. It tries to set all the necessary defaults to be self explanatory.

### Authentication

Gmvault allow users to use a XOAuth token or your gmail login password. The XOAuth authentication is the recommended way to access your account. 
This method is activated by default. After the first authentication for a given account, the XOAuth token is stored in $HOME/.gmvault and will be used for subsequent authentications. 

The following example uses XOAuth to access `foo.bar@gmail.com`:

    $>gmvault sync foo.bar@gmail.com

With the `--passwd` option, you can use your gmail login and password for a quick test or if you cannot use XOAuth. 
You will then enter an interactive session to enter your password. By default your password is not saved, but you can use the option to do it. Your password will be stored encrypted but please avoid using this option if possible.

### Backup your emails

Full sync:

    $>gmvault sync foo.bar@gmail.com

Incremental sync:

    $>gmvault sync -t quick foo.bar@gmail.com

Emails are backed up in $HOME/gmvault-db (or %HOME%/gmvault-db for Win) by default. Use `-d DB_DIR`, `--db-dir DB_DIR` to change the location of your local email repository

### Restore your emails in a Gmail account

    $>gmvault restore newfoo.bar@gmail.com

Will restore $HOME/gmvault-db (or %HOME%/gmvault-db for Win) in newfoo.bar@gmail.com

    $>gmvault restore newfoo.bar@gmail.com -d /backup/emails-db

Will restore /backup/emails-db in newfoo.bar@gmail.com

Use `--resume` or `--restart` to restart from the last fatal error and not reupload once more the already treated emails.

    $>gmvault restore newfoo.bar@gmail.com --restart






