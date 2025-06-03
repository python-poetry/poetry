# #!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2021> Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import io
import types
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from urllib.parse import parse_qs
from urllib.parse import quote
from urllib.parse import quote_plus
from urllib.parse import unquote
from urllib.parse import urlencode
from http.server import BaseHTTPRequestHandler

unquote_utf8 = unquote


def encode_obj(in_obj):
    return in_obj


class BaseClass(object):
    def __repr__(self):
        return self.__str__()


__all__ = [
    'BaseClass',
    'BaseHTTPRequestHandler',
    'quote',
    'quote_plus',
    'urlencode',
    'urlunsplit',
    'urlsplit',
    'parse_qs',
]
