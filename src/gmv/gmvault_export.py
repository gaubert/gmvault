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

import imapclient.imap_utf7 as imap_utf7

import gmv.imap_utils as imap_utils
import gmv.log_utils as log_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.gmvault_db as gmvault_db

LOG = log_utils.LoggerFactory.get_logger('gmvault_export')

class GMVaultExporter(object):
    PROGRESS_INTERVAL = 200

    CHATS_FOLDER = 'Chats'
    ARCHIVED_FOLDER = 'Archived' # Mails only in 'All Mail'

    GM_ALL = re.sub(r'^\\', '', imap_utils.GIMAPFetcher.GENERIC_GMAIL_ALL)
    GM_INBOX = 'Inbox'
    GM_SEP = '/'

    GM_SEEN = '\\Seen'
    GM_FLAGGED = '\\Flagged'

    def __init__(self, db_dir, mailbox, labels = None):
        self.storer = gmvault_db.GmailStorer(db_dir)
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
        LOG.critical("Start %s export for %s." % (kind, exported_labels))

        timer = gmvault_utils.Timer()
        timer.start()
        done = 0

        for a_id in ids:
            meta, msg = self.storer.unbury_email(a_id)

            folders = [default_folder]
            if use_labels:
                add_labels = meta[gmvault_db.GmailStorer.LABELS_K]
                if not add_labels:
                    add_labels = [GMVaultExporter.ARCHIVED_FOLDER]
                folders.extend(add_labels)
            folders = [re.sub(r'^\\', '', f) for f in folders]
            folders = [f for f in folders if self.want_label(f)]

            LOG.debug("Processing id %s in labels %s." % \
                (a_id, self.printable_label_list(folders)))
            for folder in folders:
                self.mailbox.add(msg, folder, meta[gmvault_db.GmailStorer.FLAGS_K])

            done += 1
            left = len(ids) - done
            if done % self.PROGRESS_INTERVAL == 0 and left > 0:
                elapsed = timer.elapsed()
                LOG.critical("== Processed %d %s in %s, %d left (time estimate %s). ==\n" % \
                    (done, kind, timer.seconds_to_human_time(elapsed), \
                     left, timer.estimate_time_left(done, elapsed, left)))

        LOG.critical("Export complete in %s." % (timer.elapsed_human_time(),))


class Mailbox(object):
    def add(self, msg, folder, flags):
        raise NotImplementedError('implement in subclass')
    def close(self):
        pass

class Maildir(Mailbox):
    def __init__(self, path, separator = '/'):
        self.path = path
        self.subdirs = {}
        self.separator = separator
        if not self.root_is_maildir() and not os.path.exists(self.path):
            os.makedirs(self.path)

    @staticmethod
    def separate(folder, sep):
        return folder.replace(GMVaultExporter.GM_SEP, sep)

    def subdir_name(self, folder):
        return self.separate(folder, self.separator)

    def root_is_maildir(self):
        return False;

    def subdir(self, folder):
        if folder in self.subdirs:
            return self.subdirs[folder]

        if folder:
            parts = folder.split(GMVaultExporter.GM_SEP)
            parent = GMVaultExporter.GM_SEP.join(parts[:-1])
            self.subdir(parent)
            path = self.subdir_name(folder)
            path = imap_utf7.encode(path)
        else:
            if not self.root_is_maildir():
                return
            path = ''

        abspath = os.path.join(self.path, path)
        sub = mailbox.Maildir(abspath, create = True)
        self.subdirs[folder] = sub
        return sub

    def add(self, msg, folder, flags):
        mmsg = mailbox.MaildirMessage(msg)

        if GMVaultExporter.GM_SEEN in flags:
            mmsg.set_subdir('cur')
            mmsg.add_flag('S')
        if mmsg.get_subdir() == 'cur' and GMVaultExporter.GM_FLAGGED in flags:
            mmsg.add_flag('F')

        self.subdir(folder).add(mmsg)

class OfflineIMAP(Maildir):
    DEFAULT_SEPARATOR = '.'
    def __init__(self, path, separator = DEFAULT_SEPARATOR):
        super(OfflineIMAP, self).__init__(path, separator = separator)

class Dovecot(Maildir):
    # See http://wiki2.dovecot.org/Namespaces
    class Layout(object):
        def join(self, parts):
            return self.SEPARATOR.join(parts)
    class FSLayout(Layout):
        SEPARATOR = '/'
    class MaildirPlusPlusLayout(Layout):
        SEPARATOR = '.'
        def join(self, parts):
            return '.' + super(Dovecot.MaildirPlusPlusLayout, self).join(parts)

    DEFAULT_NS_SEP = '.'
    DEFAULT_LISTESCAPE = '\\'

    # The namespace separator cannot be escaped with listescape.
    # Replace it with a two-character escape code.
    DEFAULT_SEP_ESCAPE = "*'"

    def __init__(self, path,
                 layout = MaildirPlusPlusLayout(),
                 ns_sep = DEFAULT_NS_SEP,
                 listescape = DEFAULT_LISTESCAPE,
                 sep_escape = DEFAULT_SEP_ESCAPE):
        super(Dovecot, self).__init__(path, separator = layout.SEPARATOR)
        self.layout = layout
        self.ns_sep = ns_sep
        self.listescape = listescape
        self.sep_escape = sep_escape

    # Escape one character
    def _listescape(self, s, char = None, pattern = None):
        pattern = pattern or re.escape(char)
        esc = "%s%02x" % (self.listescape, ord(char))
        return re.sub(pattern, lambda m: esc, s)

    def _munge_name(self, s):
        # Escape namespace separator: . => *', * => **
        esc = self.sep_escape[0]
        s = re.sub(re.escape(esc), esc * 2, s)
        s = re.sub(re.escape(self.ns_sep), self.sep_escape, s)

        if self.listescape:
            # See http://wiki2.dovecot.org/Plugins/Listescape
            if self.layout.SEPARATOR == '.':
                s = self._listescape(s, '.')
            s = self._listescape(s, '/')
            s = self._listescape(s, '~', r'^~')
        return s

    def subdir_name(self, folder):
        if folder == GMVaultExporter.GM_INBOX:
            return ''

        parts = folder.split(GMVaultExporter.GM_SEP)
        parts = [self._munge_name(n) for n in parts]
        return self.layout.join(parts)

    def root_is_maildir(self):
        return True

class MBox(Mailbox):
    def __init__(self, folder):
        self.folder = folder
        self.open = dict()

    def close(self):
        for _, m in self.open.items():
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
