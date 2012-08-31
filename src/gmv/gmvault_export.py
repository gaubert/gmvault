'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2012>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# TODO
# Allow syncing, aka resumability after a partial or complete export
# Test other OSes that might not like colon in Maildir filenames
# Use hard-links to save space?

import os
import re
import mailbox

from imap_utils import GIMAPFetcher
import log_utils
from gmvault import GmailStorer
from gmvault_utils import Timer

LOG = log_utils.LoggerFactory.get_logger('gmvault_export')

class GMVaultExporter(object):
    PROGRESS_INTERVAL = 200

    CHATS_FOLDER = 'Chats'

    GM_INBOX = '\\Inbox'
    GM_SEP = '/'

    GM_SEEN = '\\Seen'
    GM_FLAGGED = '\\Flagged'

    def __init__(self, db_dir, mailbox):
        self.storer = GmailStorer(db_dir)
        self.mailbox = mailbox

    def export(self):
        self.export_ids('emails', self.storer.get_all_existing_gmail_ids(), \
            default_folder = GIMAPFetcher.GENERIC_GMAIL_ALL, use_labels = True)
        self.export_ids('chats', self.storer.get_all_chats_gmail_ids(), \
            default_folder = self.CHATS_FOLDER, use_labels = False)

    def export_ids(self, kind, ids, default_folder, use_labels):
        timer = Timer()
        timer.start()
        LOG.critical("Start %s export" % (kind,))
        done = 0

        for a_id in ids:
            meta, msg = self.storer.unbury_email(a_id)

            folders = [default_folder]
            if use_labels:
                folders.extend(meta[GmailStorer.LABELS_K])
            for folder in folders:
                self.mailbox.add(msg, folder, meta[GmailStorer.FLAGS_K])

            done += 1
            left = len(ids) - done
            if done % self.PROGRESS_INTERVAL == 0 and left > 0:
                elapsed = timer.elapsed()
                LOG.critical("== Exported %d %s in %s, %d left (time estimate %s) ==" % \
                    (done, kind, timer.seconds_to_human_time(elapsed), \
                     left, timer.estimate_time_left(done, elapsed, left)))

        LOG.critical("Export complete in %s" % (timer.elapsed_human_time(),))


class Mailbox(object):
    def add(self, msg, folder, flags):
        raise NotImplementedError('implement in subclass')
    def close():
        pass

class Maildir(Mailbox):
    SEPARATOR = '.'

    def __init__(self, path, esc = '\\', sep_esc = "*'"):
        self.mailbox = mailbox.Maildir(path, create = True)
        self.escape = esc
        self.sep_escape = sep_esc

    def maildir_name(self, folder):
        if folder == GMVaultExporter.GM_INBOX:
            return None

        # Get rid of initial \\ on mailboxes
        r = re.sub(r'^\\', '', folder)

        # Escape tilde a la listescape
        r = r.replace('~', '%s%02X' % (self.escape, ord('~')))

        # listescape can't handle SEPARATOR, escape otherwise instead. Ewwww!!!
        se = self.sep_escape[0]
        r = r.replace(se, se * 2)
        r = r.replace(self.SEPARATOR, self.sep_escape)

        # Replace GMail's directory separator with ours
        return r.replace(GMVaultExporter.GM_SEP, self.SEPARATOR)

    def subdir(self, folder):
        name = self.maildir_name(folder)
        if name:
            return self.mailbox.add_folder(name)
        return self.mailbox

    def add(self, msg, folder, flags):
        mmsg = mailbox.MaildirMessage(msg)

        if GMVaultExporter.GM_SEEN in flags:
            mmsg.set_subdir('cur')
            mmsg.add_flag('S')
        if mmsg.get_subdir() == 'cur' and GMVaultExporter.GM_FLAGGED in flags:
            mmsg.add_flag('F')

        self.subdir(folder).add(mmsg)

class MBox(Mailbox):
    def __init__(self, folder):
        self.folder = folder
        self.open = dict()

    def close(self):
        for k, m in self.open.items():
            m.close()

    def subdir(self, label):
        label = re.sub(r'^\\', '', label)

        segments = label.split(GMVaultExporter.GM_SEP)
        segments = [s for s in segments if s != '..'] # safety first!
        fname = segments.pop()

        # Use .sbd folders a la Thunderbird, to allow nested folders
        segments = [s + '.sbd' for s in segments]
        mdir = os.path.join(self.folder, *segments)
        if not os.path.exists(mdir):
            os.makedirs(mdir)

        path = os.path.normpath(os.path.join(mdir, fname))
        if path in self.open:
            return self.open[path]
        mb = mailbox.mbox(path)
        self.open[path] = mb
        return mb

    def add(self, msg, folder, flags):
        mmsg = mailbox.mboxMessage(msg)
        if GMVaultExporter.GM_SEEN in flags:
            mmsg.add_flag('R')
        if GMVaultExporter.GM_FLAGGED in flags:
            mmsg.add_flag('F')
        self.subdir(folder).add(mmsg)
