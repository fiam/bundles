# -*- coding: utf-8 -*-

# Copyright (c) 2008 Alberto García Hierro <fiam@rm-fr.net>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import time
from threading import Thread

from django.conf import settings

from bundles.libbundler import get_bundles, BundleDoesNotExist

class BundleManager(object):
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.build()
        if settings.DEBUG:
            BundleChecker(self).start()

    def build(self):
        self.bundles = get_bundles(self.base_dir)
        rebuilt = []
        for bundle in self.bundles.values():
            if bundle.build():
                rebuilt.append(bundle)
        for bundle in rebuilt:
            bundle.rereference(self.bundles)
            bundle.compress()


    def get(self, bundle):
        try:
            return self.bundles[bundle]
        except KeyError:
            raise BundleDoesNotExist('Bundle %s not found' % bundle)

    @classmethod
    def manager(cls):
        return cls._SHARED_MANAGER

class BundleChecker(Thread):
    def __init__(self, manager):
        super(BundleChecker, self).__init__()
        self.mtimes = {}
        self.manager = manager
        self.full_names = {}
        self.conf_path = os.path.join(manager.base_dir, 'bundles.yaml')
        for bundle in self.manager.bundles.values():
            for fname in bundle.files:
                full_name = settings.MEDIA_ROOT + fname
                self.full_names[full_name] = fname
                self.mtimes[full_name] = os.stat(full_name).st_mtime
        self.conf_mtime = os.stat(self.conf_path)

    def run(self):
        while True:
            for fname, value in self.mtimes.iteritems():
                try:
                    mtime = os.stat(fname).st_mtime
                except OSError:
                    continue
                if value != mtime:
                    self.mtimes[fname] = mtime
                    for bundle in self.manager.bundles.values():
                        if self.full_names[fname] in bundle.files:
                            print 'Rebuilding bundle "%s"' % bundle.name
                            bundle.rebuild()
            try:
                mtime = os.stat(self.conf_path).st_mtime
            except OSError:
                continue
            if mtime != self.conf_mtime:
                print 'Reloading bundles'
                self.conf_mtime = mtime
                self.manager.build()
            time.sleep(1)

# Move to top project dir
proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BundleManager._SHARED_MANAGER = BundleManager(proj_dir)
