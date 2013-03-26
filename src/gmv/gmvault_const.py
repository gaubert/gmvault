# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

# Gmvault constants

GMAIL_UNLOCAL_CHATS = [
                     u'[Gmail]/Chats', u'[Google Mail]/Chats', #en, es, ger, portuguese
                     u'[Gmail]/Chat', u'[Google Mail]/Chat', #it
                     u'[Google Mail]/Tous les chats', u'[Gmail]/Tous les chats', # french
                     u'[Gmail]/Чаты', u'[Google Mail]/Чаты', # russian
                     u'[Google Mail]/Czat', u'[Gmail]/Czat', # polish
                     u'[Google Mail]/Bate-papos', u'[Gmail]/Bate-papos', #portuguese brazil
                    ]   # unlocalised Chats names

#The default conf file
DEFAULT_CONF_FILE = """#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Gmvault Configuration file containing Gmvault defaults.
#  DO NOT CHANGE IT IF YOU ARE NOT AN ADVANCED USER
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

[Sync]
quick_days=10

[Restore]
# it is 10 days but currently it will always be the current month or the last 2 months
# the notion of days is not yet apparent in restore (only months).
quick_days=10
reserved_labels_map = { u'migrated' : u'gmv-migrated', u'\muted' : u'gmv-muted' }

[General]
limit_per_chat_dir=2000
errors_if_chat_not_visible=False
nb_messages_per_batch=500
nb_messages_per_restore_batch=80
restore_default_location=DRAFTS
keep_in_bin=False
enable_imap_compression=True

[Localisation]
#example with Russian
chat_folder=[ u'[Google Mail]/Чаты', u'[Gmail]/Чаты' ]
#uncomment if you need to force the term_encoding
#term_encoding='utf-8'

#Do not touch any parameters below as it could force an overwrite of this file
[VERSION]
conf_version=1.8.1

#set environment variables for the program locally
#they will be read only once the conf file has been loaded
[ENV]
#by default it is ~/.gmvault
GMV_IMAP_DEBUG=0

"""
