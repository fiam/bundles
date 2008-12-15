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
import re
import yaml
from base64 import urlsafe_b64encode
import hashlib

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

BUNDLE_TYPES = {}

YUIC_VERSION = '2.3.6'
YUIC_NAME = 'yuicompressor'
YUIC = '%s-%s' % (YUIC_NAME, YUIC_VERSION)
YUIC_JAR = '%s.jar' % YUIC
YUIC_URL = 'http://www.julienlecomte.net/yuicompressor/%s.zip' % YUIC

RHINO_VERSION = '1_7R1'
RHINO_JAR = 'js.jar'
RHINO_NAME = 'rhino'
RHINO = '%s%s' % (RHINO_NAME, RHINO_VERSION)
RHINO_URL = 'ftp://ftp.mozilla.org/pub/mozilla.org/js/%s.zip' % RHINO

JSLINT = 'jslint.js'
JSLINT_URL = 'http://www.jslint.com/rhino/%s' % JSLINT

if hasattr(settings, 'BUNDLES_URL'):
    BUNDLES_URL = settings.BUNDLES_URL
else:
    BUNDLES_URL = settings.MEDIA_URL

def is_debug_mode():
    return settings.DEBUG and not getattr(settings, 'BUNDLES_NO_DEBUG', False)

class BundleError(RuntimeError):
    pass

class InvalidBundleType(BundleError):
    pass

class NoBundlesError(BundleError):
    pass

class BundleParserError(BundleError):
    pass

class BundleDoesNotExist(BundleError):
    pass

def get_bundle_type(bundle_name, bundle_dct):
    if bundle_dct and 'type' in bundle_dct:
        return bundle_dct['type']

    return bundle_name.rsplit('.', 1)[1].lower()

def get_bundle_cls(bundle_name, bundle_dct):
    try:
        return BUNDLE_TYPES[get_bundle_type(bundle_name, bundle_dct)]
    except KeyError:
        raise InvalidBundleType('No handler registered for "%s" bundles'  \
            % get_bundle_type(bundle_name, bundle_dct))

def create_bundle(bundle_name, bundle_dct):
    return get_bundle_cls(bundle_name, bundle_dct)(bundle_name, bundle_dct)

class BundleType(type):
    def __init__(cls, name, bases, dct):
        super(BundleType, cls).__init__(name, bases, dct)
        if cls.bundle_type:
            if hasattr(cls.bundle_type, '__iter__'):
                for t in cls.bundle_type:
                    BUNDLE_TYPES[t] = cls
            else:
                BUNDLE_TYPES[cls.bundle_type] = cls

class BaseBundle(object):
    bundle_type = None
    def __init__(self, name, dct):
        self.name = name
        self._hash = None
        if dct and dct.get('files'):
            self.files = dct['files']
        else:
            self.files = [self.name]

        self.bundle_name = self.get_bundle_name()
        self.validate()

    def validate(self):
        for fname in self.files:
            try:
                os.stat(self.get_source_name(fname))
            except OSError:
                raise ImproperlyConfigured('File %s in bundle %s does not exist' % \
                    (fname, self.name))

    def hash(self):
        m = hashlib.sha1()
        for fname in self.files:
            fp = open(self.get_source_name(fname))
            m.update(fp.read())
            fp.close()

        return urlsafe_b64encode(m.digest()).strip('=')

    def rebuild(self):
        self.bundle_name = self.get_bundle_name()
        self.build()

    def get_source_name(self, fname):
        return os.path.join(settings.MEDIA_ROOT, fname)

    def get_bundle_name(self):
        name_parts = self.name.rsplit('.', 1)
        if len(name_parts) == 1:
            return '%s.%s' % (self.name, self.hash())

        return '%s.%s.%s' % (name_parts[0], self.hash(), name_parts[1])

    @property
    def url(self):
        return '%s/%s' % (BUNDLES_URL, self.get_bundle_name())

    def get_bundle_path(self):
        return os.path.join(settings.MEDIA_ROOT, 'bundles', self.bundle_name)

    def add_file(self, b_fp, s_fp):
        data = s_fp.read(256)
        while data:
            b_fp.write(data)
            data = s_fp.read(256)
        s_fp.close()

    def build(self, verbose=False):
        if os.path.exists(self.get_bundle_path()):
            return False

        bundle_dir = os.path.dirname(self.get_bundle_path())
        if not os.path.exists(bundle_dir):
            os.makedirs(bundle_dir)
        else:
            if not os.path.isdir(bundle_dir):
                raise OSError('"%s" exists but is not a directory' % bundles_dir)
        bundle = open(self.get_bundle_path(), 'w')
        for fname in self.files:
            source = open(self.get_source_name(fname))
            self.add_file(bundle, source)
        bundle.close()
        return True

    def include_debug(self, base_url=''):
        markup = []
        for file_name in self.files:
            markup.append(self.include_file(base_url + settings.MEDIA_URL + file_name))

        return u'\n'.join(markup)

    def include_release(self, base_url=''):
        return self.include_file(base_url + BUNDLES_URL + self.bundle_name)

    def include_external(self):
        return self.include(base_url='http://' + settings.SITE_NAME)

    def compress(self, verbose=False):
        pass

    def get_contents(self):
        fp = open(self.get_bundle_path())
        contents = fp.read()
        fp.close()
        return contents

    def set_contents(self, contents):
        fp = open(self.get_bundle_path(), 'w')
        fp.write(contents)
        fp.close()

    def rereference(self, other_bundles):
        pass


if is_debug_mode():
    BaseBundle.include = BaseBundle.include_debug
else:
    BaseBundle.include = BaseBundle.include_release

class Bundle(BaseBundle):
    __metaclass__ = BundleType

class YUIBundle(Bundle):
    reference_delimiters = []
    def add_file(self, b_fp, s_fp):
        super(YUIBundle, self).add_file(b_fp, s_fp)
        b_fp.write('\n\n')

    def compress(self, verbose=False):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        yuic_jar = os.path.join(this_dir, YUIC_JAR)
        if not os.path.exists(yuic_jar):
            print 'Cannot find "%s"' % yuic_jar
            return
        fname = self.get_bundle_path()
        p = os.popen('java -jar %s --type %s -v %s -o %s 2>&1' %
            (yuic_jar, self.file_type, fname, fname))
        out = p.read()
        if verbose:
            print out

    def escape(self, value):
        return value.replace('(', '\(').replace(')', '\)')

    def rereference(self, other_bundles):
        contents = self.get_contents()
        for dlm in self.reference_delimiters:
            for bundle in other_bundles.values():
                if bundle == self:
                    continue
                r = re.compile('%s(.*?)%s%s' % (self.escape(dlm[0]), bundle.name, self.escape(dlm[1])))
                contents = r.sub('%s\g<1>%s%s' % (dlm[0], 'bundles/' + bundle.bundle_name, dlm[1]), contents)
        self.set_contents(contents.replace('../bundles/', ''))

class JSBundle(YUIBundle):
    reference_delimiters = [ ('\'', '\''), ('"', '"') ]
    bundle_type = 'js'
    file_type = 'js'
    def include_file(self, url):
        return u'<script type="text/javascript" src="%s"></script>' % url

class CSSBundle(YUIBundle):
    reference_delimiters = [ ('url(', ')') ]
    bundle_type = 'css'
    file_type = 'css'
    media = 'screen'
    def __init__(self, name, dct):
        super(CSSBundle, self).__init__(name, dct)
        self.media = dct.get('media', self.media)

    def include_file(self, url):
        return u'<link href="%s" media="%s" rel="stylesheet" type="text/css" />' % \
            (url, self.media)

class ImageBundle(Bundle):
    file_type = 'img'
    bundle_type = ['gif', 'jpg', 'png', 'svg', 'ico']
    def validate(self):
        super(ImageBundle, self).validate()
        if len(self.files) > 1:
            raise ImproperlyConfigured('This type of bundle can only contain one file (%s)' % self.name)

    def include_file(self, url):
        return u'<img alt="" src="%s" />' % url

class IconBundle(Bundle):
    file_type = 'ico'
    bundle_type = 'ico'
    def include_file(self, url):
        return u'<link rel="icon shortcut" href="%s" type="image/x-icon" />' % url

def get_bundles(base_dir):
    bundles = {}
    try:
        fp = open(os.path.join(base_dir, 'bundles.yaml'))
        raw_bundles = yaml.load(fp.read())
    except OSError:
        raise NoBundlesError('Cannot open bundles.yaml')

    fp.close()
    for key, value in raw_bundles.iteritems():
        bundles[key] = create_bundle(key, value)

    return bundles

def rereference_bundles(bundles):
    for bundle in bundles.values():
        bundle.rereference(bundles)

