#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from itertools import groupby
from  xml.sax.saxutils import XMLGenerator


root = namedtuple('root', ['children'])
highlight = namedtuple('highlight', ['description', 'children'])
line = namedtuple('line', ['text'])

_start = namedtuple('_start', ['description'])
_end = namedtuple('_end', [])


def is_line(elt):
    return type(elt) == line

def is_highlight(elt):
    return type(elt) == highlight

_tag_start_pattern = re.compile("^\\s*##\\s+(?P<text>.+?)\\s*$")
_tag_end_pattern = re.compile("^\\s*###\\s*$")

def is_tag_start(l):
    return _tag_start_pattern.match(l) is not None

def is_tag_end(l):
    return _tag_end_pattern.match(l)

def _comment_text(tag_start_lines):
    return " ".join(_tag_start_pattern.match(l).group("text") for l in tag_start_lines)

def _delimited(line_iter):
    for is_start, lines in groupby(line_iter, is_tag_start):
        if is_start:
            yield _start(_comment_text(lines))
        else:
            for l in lines:
                if is_tag_end(l):
                    yield _end()
                else:
                    yield line(l)
            
def _to_tree(delimited_lines):
    for e in delimited_lines:
        if type(e) == _start:
            yield highlight(e.description, list(_to_tree(delimited_lines)))
        elif type(e) == _end:
            return
        else:
            yield e

def lines_to_tagged_tree(lines):
    return root(list(_to_tree(_delimited(lines))))

def code_lines(f):
    with open(f) as input:
        return [l.rstrip('\n') for l in input]


def to_html(tree, root_attrs={}, out=XMLGenerator(sys.stdout), resource_prefix=""):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    def _element_to_html(e):
        if is_line(e):
            element("pre", {}, e.text)
        elif is_highlight(e):
            out.startElement("div", {"class": "bootstro", "data-bootstro-content": e.description})
            for c in e.children:
                _element_to_html(c)
            out.endElement("div")
        else:
            raise ValueError("unexpected node: " + repr(e))
    
    def element(name, attrs, text=None):
        out.startElement(name, attrs)
        if text is not None:
            out.characters(text)
        out.endElement(name)
    
    out.startElement("html", {})
    out.startElement("head", {})
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource_prefix + "bootstrap/css/bootstrap.min.css"})
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource_prefix + "bootstro.js/bootstro.min.css"})
    element("script", {"type": "text/javascript", "src": resource_prefix + "jquery-1.9.1.js"})
    element("script", {"type": "text/javascript", "src": resource_prefix + "bootstrap/js/bootstrap.min.js"})
    element("script", {"type": "text/javascript", "src": resource_prefix + "bootstro.js/bootstro.min.js"})
    element("script", {"type": "text/javascript"}, """
        $(document).ready(function(){
            bootstro.start();
        });
    """)
    out.endElement("head")
    out.startElement("body", {})
    out.startElement("div", root_attrs)
    for e in tree.children:
        _element_to_html(e)
    out.endElement("div")
    out.endElement("body")
    out.endElement("html")


if __name__ == '__main__':
    import sys
    to_html(lines_to_tagged_tree(code_lines(sys.argv[1])), resource_prefix="ext/")

