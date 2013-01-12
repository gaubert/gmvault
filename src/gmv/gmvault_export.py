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

import os
import re
import mailbox

from gmv.imap_utils import GIMAPFetcher
import gmv.log_utils as log_utils
from gmv.gmvault_db import GmailStorer
from gmv.gmvault_utils import Timer

LOG = log_utils.LoggerFactory.get_logger('gmvault_export')

class GMVaultExporter(object):
    PROGRESS_INTERVAL = 200

    CHATS_FOLDER = 'Chats'
    ARCHIVED_FOLDER = 'Archived' # Mails only in 'All Mail'

    GM_ALL = re.sub(r'^\\', '', GIMAPFetcher.GENERIC_GMAIL_ALL)
    GM_INBOX = 'Inbox'
    GM_SEP = '/'

    GM_SEEN = '\\Seen'
    GM_FLAGGED = '\\Flagged'

    def __init__(self, db_dir, mailbox, labels = None):
        self.storer = GmailStorer(db_dir)
        self.mailbox = mailbox
        self.labels = labels

    def want_label(self, label):
        if self.labels:
            return label in self.labels
        return label != self.GM_ALL

    def export(self):
        self.export_ids('emails', self.storer.get_all_existing_gmail_ids(), \
            default_folder = self.GM_ALL, use_labels = True)
        self.export_ids('chats', self.storer.get_all_chats_gmail_ids(), \
            default_folder = self.CHATS_FOLDER, use_labels = False)

    def printable_label_list(self, labels):
        labels = [l.encode('ascii', 'backslashreplace') for l in labels]
        return u'; '.join(labels)

    def export_ids(self, kind, ids, default_folder, use_labels):
        exported_labels = "default labels"
        if self.labels:
            exported_labels = "labels " + self.printable_label_list(self.labels)
        LOG.critical("Start %s export for %s" % (kind, exported_labels))

        timer = Timer()
        timer.start()
        done = 0

        for a_id in ids:
            meta, msg = self.storer.unbury_email(a_id)

            folders = [default_folder]
            if use_labels:
                add_labels = meta[GmailStorer.LABELS_K]
                if not add_labels:
                    add_labels = [GMVaultExporter.ARCHIVED_FOLDER]
                folders.extend(add_labels)
            folders = [re.sub(r'^\\', '', f) for f in folders]
            folders = [f for f in folders if self.want_label(f)]

            LOG.debug("Processing id %s in labels %s" % \
                (a_id, self.printable_label_list(folders)))
            for folder in folders:
                self.mailbox.add(msg, folder, meta[GmailStorer.FLAGS_K])

            done += 1
            left = len(ids) - done
            if done % self.PROGRESS_INTERVAL == 0 and left > 0:
                elapsed = timer.elapsed()
                LOG.critical("== Processed %d %s in %s, %d left (time estimate %s) ==" % \
                    (done, kind, timer.seconds_to_human_time(elapsed), \
                     left, timer.estimate_time_left(done, elapsed, left)))

        LOG.critical("Export complete in %s" % (timer.elapsed_human_time(),))


class Mailbox(object):
    def add(self, msg, folder, flags):
        raise NotImplementedError('implement in subclass')
    def close(self):
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

        # Escape tilde a la listescape
        r = folder.replace('~', '%s%02X' % (self.escape, ord('~')))

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
        segments = label.split(GMVaultExporter.GM_SEP)
        # Safety first: No unusable directory portions
        segments = [s for s in segments if s != '..' and s != '.']
        real_label = GMVaultExporter.GM_SEP.join(segments)
        if real_label in self.open:
            return self.open[real_label]

        cur_path = self.folder
        label_segments = []
        for s in segments:
            label_segments.append(s)
            cur_label = GMVaultExporter.GM_SEP.join(label_segments)
            if cur_label not in self.open:
                # Create an mbox for intermediate folders, to satisfy
                # Thunderbird import
                if not os.path.exists(cur_path):
                    os.makedirs(cur_path)
                mbox_path = os.path.join(cur_path, s)
                self.open[cur_label] = mailbox.mbox(mbox_path)
            # Use .sbd folders a la Thunderbird, to allow nested folders
            cur_path = os.path.join(cur_path, s + '.sbd')

        return self.open[real_label]

    def add(self, msg, folder, flags):
        mmsg = mailbox.mboxMessage(msg)
        if GMVaultExporter.GM_SEEN in flags:
            mmsg.add_flag('R')
        if GMVaultExporter.GM_FLAGGED in flags:
            mmsg.add_flag('F')
        self.subdir(folder).add(mmsg)
