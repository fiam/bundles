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

from django import template

from bundles.libbundler import BUNDLES_URL
from bundles.manager import BundleManager

register = template.Library()

MANAGER = BundleManager.manager()

@register.simple_tag
def bundle(value):
    return MANAGER.get(value).include()

@register.simple_tag
def bundle_url_path(value):
    return BUNDLES_URL + MANAGER.get(value).bundle_name

@register.simple_tag
def bundle_url(value):
    return MANAGER.get(value).include_release()

@register.simple_tag
def external_bundle(value):
    return MANAGER.get(value).include_external()

@register.tag
def bundles(parser, token):
    return BundleNode(*token.split_contents()[1:])

class BundleNode(template.Node):
    def __init__(self, *args):
        self.bundles = []
        for arg in args:
            self.bundles.append(template.Variable(arg))

    def render(self, context):
        markup = []
        for bndl in self.bundles:
            markup.append(bundle(bndl.resolve(context)))

        return u''.join(markup)
