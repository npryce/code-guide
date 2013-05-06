#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from itertools import groupby
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl


_tag_start_pattern = re.compile("^\\s*##\\s+(?P<text>.+?)\\s*$")
_tag_end_pattern = re.compile("^\\s*###\\s*$")

root = namedtuple('root', ['children'])
highlight = namedtuple('highlight', ['description', 'children'])
line = namedtuple('line', ['text'])

_start = namedtuple('_start', ['description'])
_end = namedtuple('_end', [])


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
        t = type(e)
        if t == _start:
            yield highlight(e.description, list(_to_tree(delimited_lines)))
        elif t == _end:
            return
        else:
            yield e

def lines_to_tagged_tree(lines):
    return root(list(_to_tree(_delimited(lines))))

def code_lines(f):
    with open(f) as input:
        return [l.rstrip('\n') for l in input]


def to_html(tree, out=XMLGenerator(sys.stdout), title=None, resource_dir="", minified=True):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    resource_prefix = resource_dir if resource_dir == "" or resource_dir.endswith("/") else resource_dir + "/"
    min_suffix = ".min" if minified else ""
    
    def resource(r):
        return resource_prefix + r.format(min=min_suffix)
    
    def _element_to_html(e):
        t = type(e)
        if t == line:
            element("pre", {}, e.text)
        elif t == highlight:
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
    if title is not None:
        element("title", {}, text=title)
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource("bootstrap/css/bootstrap{min}.css")})
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource("bootstro/bootstro{min}.css")})
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource("code-guide.css")})
    element("script", {"type": "text/javascript", "src": resource("jquery-1.9.1{min}.js")})
    element("script", {"type": "text/javascript", "src": resource("bootstrap/js/bootstrap{min}.js")})
    element("script", {"type": "text/javascript", "src": resource("bootstro/bootstro{min}.js")})
    element("script", {"type": "text/javascript", "src": resource("code-guide.js")})
    out.endElement("head")
    out.startElement("body", {})
    if title is not None:
        element("h1", {}, text=title)
    
    out.startElement("p", {})
    element("button", {"class": "btn btn-primary",
                       "type": "button",
                       "onclick": "code_guide.start()"},
            text="Explain!")
    out.endElement("p")
    out.startElement("div", {"class": "code-guide-code"})
    for e in tree.children:
        _element_to_html(e)
    out.endElement("div")
    out.endElement("body")
    out.endElement("html")
    
    return out


if __name__ == '__main__':
    import sys
    code = lines_to_tagged_tree(code_lines(sys.argv[1]))
    to_html(code, title=sys.argv[2] if len(sys.argv) > 2 else None, resource_dir="resources")

