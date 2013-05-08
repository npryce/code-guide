#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from itertools import groupby
import xml.sax
from xml.sax.saxutils import XMLGenerator, XMLFilterBase
from xml.sax.xmlreader import AttributesImpl
from markdown import markdown

_title_pattern = re.compile("^\\s*####\\s*(?P<text>.+?)\\s*####\\s*$")
_intro_pattern = re.compile("^\\s*### (?P<text>.+?)\\s*$")
_tag_start_pattern = re.compile("^\\s*##\\s*((?P<step>\[[:digit:]+\])\\s*)?(?P<text>.*?)\\s*$")
_tag_end_pattern = re.compile("^\\s*##\\.\\s*$")

_root = namedtuple('root', ['children', 'title', 'intro'])
highlight = namedtuple('highlight', ['description', 'children'])
line = namedtuple('line', ['text'])
_title = namedtuple('title', ['text'])
_intro = namedtuple('intro', ['text'])

_start = namedtuple('_start', ['description'])
_end = namedtuple('_end', [])

def _join_text(tag_start_lines, pattern):
    return "\n".join(_significant_text(l, pattern) for l in tag_start_lines)

def _significant_text(line, pattern):
    return pattern.match(line).group("text")

def _start_group(lines):
    yield _start(_join_text(lines, _tag_start_pattern))

def _end_group(lines):
    for l in lines:
        yield _end()

def _intro_group(lines):
    yield _intro(_join_text(lines, _intro_pattern))

def _line_group(lines):
    for l in lines:
        yield line(l)

def _title_group(lines):
    for l in lines:
        yield _title(_significant_text(l, _title_pattern))

# The order in which these patterns are checked is important to avoid ambiguity.
def line_group_type(l):
    if _title_pattern.match(l) is not None:
        return _title_group
    elif _intro_pattern.match(l) is not None:
        return _intro_group
    elif _tag_end_pattern.match(l) is not None:
        return _end_group
    elif _tag_start_pattern.match(l) is not None:
        return _start_group
    else:
        return _line_group

def _delimited(line_iter):
    for group_type, lines in groupby(line_iter, line_group_type):
        for e in group_type(lines):
            yield e
            
def _to_tree(delimited_lines):
    for e in delimited_lines:
        t = type(e)
        if t == _start:
            yield highlight(e.description, list(filter(valid_subtree_node, _to_tree(delimited_lines))))
        elif t == _end:
            return
        else:
            yield e

def valid_subtree_node(e):
    t = type(e)
    return t not in (_title, _intro)

def lines_to_tagged_tree(lines):
    parse = list(_to_tree(_delimited(lines)))
    children = filter(valid_subtree_node, parse)
    titles = filter(lambda e: type(e) == _title, parse)
    intros = filter(lambda e: type(e) == _intro, parse)
    
    return _root(title=to_text("title", titles), intro=to_text("intro",intros), children=children)


def to_text(name, es):
    n = len(es)
    if n == 1:
        return es[0].text
    elif n == 0:
        return None
    else:
        raise ValueError("too many "+what+": there must be zero or one.")


def code_lines(f):
    with open(f) as input:
        return [l.rstrip('\n') for l in input]


class ElementOnlyFilter(XMLFilterBase):
    def startDocument(self):
        pass
    
    def endDocument(self):
        pass

def stream_markdown_as_html(markdown_str, out):
    xhtml_str = markdown(markdown_str, safe_mode=True, output_format="xhtml5")
    filter = ElementOnlyFilter()
    filter.setContentHandler(out)
    xml.sax.parseString(xhtml_str, filter)

def to_html(root, out=None, resource_dir="", minified=True):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    resource_prefix = resource_dir if resource_dir == "" or resource_dir.endswith("/") else resource_dir + "/"
    min_suffix = ".min" if minified else ""
    
    def resource(r):
        return resource_prefix + r.format(min=min_suffix)
    
    def element_to_html(e):
        t = type(e)
        if t == line:
            element("pre", {}, e.text if e.text != "" else " ")
        elif t == highlight:
            out.startElement("div", {
                    "class": "bootstro", 
                    "data-bootstro-content": e.description,
                    "data-bootstro-placement": "right",
                    "data-bootstro-width": "25%"})
            for c in e.children:
                element_to_html(c)
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
    if root.title is not None:
        element("title", {}, text=root.title)
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource("bootstrap/css/bootstrap{min}.css")})
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource("bootstro/bootstro{min}.css")})
    element("link", {"rel": "stylesheet", "type": "text/css", "href": resource("code-guide.css")})
    element("script", {"type": "text/javascript", "src": resource("jquery-1.9.1{min}.js")})
    element("script", {"type": "text/javascript", "src": resource("bootstrap/js/bootstrap{min}.js")})
    element("script", {"type": "text/javascript", "src": resource("bootstro/bootstro{min}.js")})
    element("script", {"type": "text/javascript", "src": resource("code-guide.js")})
    out.endElement("head")
    out.startElement("body", {})

    if root.title is not None:
        element("h1", {}, text=root.title)
    
    if root.intro is not None:
        out.startElement("div", {"class": "code-guide-intro"})
        stream_markdown_as_html(root.intro, out)
        out.endElement("div")
    
    out.startElement("p", {})
    element("button", 
            {"class": "btn btn-primary",
             "type": "button",
             "onclick": "code_guide.start()"},
            text="Explain!")
    out.endElement("p")
    out.startElement("div", {"class": "code-guide-code"})
    for e in root.children:
        element_to_html(e)
    out.endElement("div")
    out.endElement("body")
    out.endElement("html")
    
    return out


if __name__ == '__main__':
    import sys
    code = lines_to_tagged_tree(code_lines(sys.argv[1]))
    to_html(code, resource_dir="resources")

