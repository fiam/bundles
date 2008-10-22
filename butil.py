#!/usr/bin/python

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
from os.path import dirname, abspath, basename
import sys
from optparse import OptionParser

def build_bundles(bundles, options):
    from bundles import libbundler
    for name, bundle in bundles.iteritems():
        print 'Bulding bundle "%s"' % name
        bundle.build()

    libbundler.rereference_bundles(bundles)

    if options.compress:
        for name, bundle in bundles.iteritems():
            print 'Compressing bundle "%s"' % name
            bundle.compress(options.verbose)

def get_bundles(options):
    from bundles import libbundler
    bundles = libbundler.get_bundles(options.dir)
    if not options.bundles:
        return bundles

    bundles = dict((k, bundles[k]) for k in bundles if k in options.bundles)
    for bname in options.bundles:
        if not bname in bundles:
            print 'Cannot find bundle "%s"' % bname

    return bundles

def print_bundles(bundles, options):
    for k, v in bundles.iteritems():
        print 'Bundle: %s (type %s)' % (v.name, v.file_type)
        for f in v.files:
            print '\t%s' % f

def download_file(url, destdir, verbose=True):
    from urllib2 import urlopen
    from cStringIO import StringIO

    if verbose:
        print 'Fetching %s' % url
        print 'Storing it in %s' % destdir

    outname = basename(url)
    try:
        out_fp = open(os.path.join(destdir, outname), 'wb')
    except (OSError, IOError):
        print 'Cannot create "%s"' % os.path.join(destdir, outname)
        return False

    try:
        url_fp = urlopen(url)
        print '%s opened. Reading...' % url
        data = url_fp.read(50)
        i = 0
        while data:
            out_fp.write(data)
            data = url_fp.read(50)
            print '\r-\\|/'[i % 4],
            i += 1
        url_fp.close()
        out_fp.close()
        return True
    except Exception, e:
        print 'Error downloading %s' % url
        print e
        return False

def extract_from_zip(zip_file, file_name):
    from zipfile import ZipFile

    out_path = os.path.join(dirname(abspath(zip_file)), basename(file_name))
    try:
        out_fp = open(out_path, 'wb')
    except (OSError, IOError):
        print 'Cannot create "%s"' % out_path
        return False

    zfile = ZipFile(open(zip_file))
    out_fp.write(zfile.read(file_name))
    out_fp.close()
    return True

def install_from_zip_url(zip_url, file_name, destdir):
    download_file(zip_url, destdir)
    zip_path = os.path.join(destdir, basename(zip_url))
    extract_from_zip(zip_path, file_name)
    os.unlink(zip_path)

def install_deps(destdir):
    from libbundler import YUIC, YUIC_URL, YUIC_JAR, RHINO, RHINO_URL, RHINO_JAR, JSLINT_URL
    print 'Installing YUI Compressor'
    install_from_zip_url(YUIC_URL, '%s/build/%s' % (YUIC, YUIC_JAR), destdir)
    print 'Installing Rhino'
    install_from_zip_url(RHINO_URL, '%s/%s' % (RHINO, RHINO_JAR), destdir)
    print 'Installing jslint'
    download_file(JSLINT_URL, destdir)

def jslint_file(file_name):
    from django.conf import settings
    from libbundler import RHINO_JAR, JSLINT
    this_dir = os.path.dirname(os.path.abspath(__file__))
    rhino_jar = os.path.join(this_dir, RHINO_JAR)
    if not os.path.exists(rhino_jar):
        print 'Cannot find "%s"' % rhino_jar
        return
    jslint = os.path.join(this_dir, JSLINT)
    if not os.path.exists(jslint):
        print 'Cannot find "%s"' % jslint
        return

    print 'JSLinting %s' % file_name
    os.system('java -jar %s %s %s' %
        (rhino_jar, jslint, os.path.join(settings.MEDIA_ROOT, file_name)))

def jslint(bundles, options):
    for bundle in bundles.values():
        if bundle.file_type == 'js':
            for fname in bundle.files:
                jslint_file(fname)

def main():
    proj_dir = dirname(dirname(abspath(sys.argv[0])))

    usage = 'usage: %prog [options] [bundles or files]\n' \
        'Bundles should be specified by their name\n' \
        'Files should be specified by their relative name from settings.MEDIA_ROOT\n' \
        'The only command accepting files is --jslint\n' \
        'If no bundles nor files are specified, all bundles are processed'
    parser = OptionParser(usage=usage, version='%prog 0.1')
    parser.add_option('-s', '--settings', action='store', type='string', dest='settings', default='settings',
        help='Name of your settings name without .py (defaults to settings')
    parser.add_option('-b', '--build', action='store_true', dest='build', default=False,
        help='Build bundles')
    parser.add_option('-c', '--compress', action='store_true', dest='compress', default=False,
        help='When building bundles, also compress them (requires YUI Compressor and Java)')
    parser.add_option('-d', '--dir', action='store', type='string', dest='dir', default=None,
        help='Directory where bundles.yaml is located (defaults to %s)' % proj_dir)
    parser.add_option('-l', '--list', action='store_true', dest='list_bundles', default=False,
        help='List bundles')
    parser.add_option('-i', '--install', action='store_true', dest='install', default=False,
        help='Install YUI Compressor, Rhino and JSLint (Java is required for them)')
    parser.add_option('-j', '--jslint', action='store_true', dest='jslint', default=False,
        help='JSLint files or bundles passed in the command line (requires Rhino, JSLint and Java)')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False,
        help='Prints more information while compressing files')

    (options, args) = parser.parse_args(sys.argv)
    sys.path.append(proj_dir)
    proj_settings = __import__(options.settings)
    from django.core.management import setup_environ
    setup_environ(proj_settings)

    if options.install:
        install_deps(dirname(abspath(sys.argv[0])))
        sys.exit(0)

    options.bundles = []
    for name in args[1:]:
        options.bundles.append(name)

    if not options.dir:
        options.dir = proj_dir

    bundles = get_bundles(options)

    if options.list_bundles:
        print_bundles(bundles, options)
        sys.exit(0)

    if options.jslint:
        jslint(bundles, options)
        for arg in args[1:]:
            if arg not in bundles:
                jslint_file(arg)
        sys.exit(0)

    if options.build:
        build_bundles(bundles, options)
        sys.exit(0)

    print 'Tell me something to do!'
    parser.parse_args([sys.argv[0], '-h'])

if __name__ == '__main__':
    main()
