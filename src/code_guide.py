#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from itertools import groupby, islice
import xml.sax
from xml.sax.saxutils import XMLGenerator, XMLFilterBase
from markdown import markdown

_title_pattern = re.compile("^\\s*####\\s*(?P<text>.+?)\\s*####\\s*$")
_intro_pattern = re.compile("^\\s*### (?P<text>.+?)\\s*$")
_region_start_pattern = re.compile("^\\s*##\\s*(\\[(?P<index>[0-9]+)\\]\\s*)?(?P<text>.*?)\\s*$")
_region_end_pattern = re.compile("^\\s*##\\.\\s*$")

_root = namedtuple('root', ['children', 'title', 'intro'])
_explanation = namedtuple('explanation', ['text', 'index', 'children'])
line = namedtuple('line', ['text'])
_title = namedtuple('title', ['text'])
_intro = namedtuple('intro', ['text'])

_start = namedtuple('_start', ['text', 'index'])
_end = namedtuple('_end', [])

def _significant_text(line, pattern):
    return pattern.match(line).group("text")

def _join_text(tag_start_lines, pattern):
    return "\n".join(_significant_text(l, pattern) for l in tag_start_lines)

def _map_or_none(f, v):
    return None if v is None else f(v)

def _start_index(line, pattern):
    return _map_or_none(int, pattern.match(line).groupdict().get('index', None))

def _start_group(lines):
    lines = list(lines)
    yield _start(index=_start_index(lines[0], _region_start_pattern),
                 text=_join_text(lines, _region_start_pattern))

def _end_group(lines):
    for l in lines:
        yield _end()

def _intro_group(lines):
    yield _intro(_join_text(lines, _intro_pattern))

def _title_group(lines):
    for l in lines:
        yield _title(_significant_text(l, _title_pattern))

def _line_group(lines):
    for l in lines:
        yield line(l)

_line_groups = [
    (_title_pattern, _title_group),
    (_intro_pattern, _intro_group),
    (_region_end_pattern, _end_group),
    (_region_start_pattern, _start_group)]


# The order in which these patterns are checked is important to avoid ambiguity.
def line_group_type(l):
    for pattern, group in _line_groups:
        if pattern.match(l) is not None:
            return group
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
            yield _explanation(text=e.text, index=e.index, children=list(filter(valid_subtree_node, _to_tree(delimited_lines))))
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

def stream_html(out, html_str):
    filter = ElementOnlyFilter()
    filter.setContentHandler(out)
    xml.sax.parseString(html_str, filter)

def stream_markdown_as_html(out, markdown_str):
    stream_html(out, markdown(markdown_str, safe_mode=True, output_format="xhtml5"))


def _element_to_html(out, e):
    t = type(e)
    if t == line:
        element(out, "pre", {}, e.text if e.text != "" else " ")
    elif t == _explanation:
        attrs = {
            "class": "bootstro", 
            "data-bootstro-content": markdown(e.text),
            "data-bootstro-html": "true",
            "data-bootstro-placement": "right",
            "data-bootstro-width": "25%"}
            
        if e.index is not None:
            attrs["data-bootstro-step"] = str(e.index - 1)
                
        out.startElement("div", attrs)
                    
        for c in e.children:
            _element_to_html(out, c)
        out.endElement("div")
    else:
        raise ValueError("unexpected node: " + repr(e))


def element(out, name, attrs, text=None):
    out.startElement(name, attrs)
    if text is not None:
        out.characters(text)
    out.endElement(name)
    

def to_html(root, out=None, language="python", resource_dir="", minified=True):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    resource_prefix = resource_dir if resource_dir == "" or resource_dir.endswith("/") else resource_dir + "/"
    min_suffix = ".min" if minified else ""
    
    def resource(r):
        return resource_prefix + r.format(min=min_suffix)
    
    out.startElement("html", {})
    out.startElement("head", {})
    if root.title is not None:
        element(out, "title", {}, text=root.title)
    element(out, "link", {"rel": "stylesheet", "type": "text/css", "href": resource("bootstrap/css/bootstrap{min}.css")})
    element(out, "link", {"rel": "stylesheet", "type": "text/css", "href": resource("bootstro/bootstro{min}.css")})
    element(out, "link", {"rel": "stylesheet", "type": "text/css", "href": resource("code-guide.css")})
    element(out, "script", {"type": "text/javascript", "src": resource("jquery-1.9.1{min}.js")})
    element(out, "script", {"type": "text/javascript", "src": resource("bootstrap/js/bootstrap{min}.js")})
    element(out, "script", {"type": "text/javascript", "src": resource("bootstro/bootstro{min}.js")})
    element(out, "script", {"type": "text/javascript", "src": resource("code-guide.js")})
    out.endElement("head")
    out.startElement("body", {})
    
    if root.title is not None:
        element(out, "h1", {}, text=root.title)
    
    if root.intro is not None:
        out.startElement("div", {"class": "code-guide-intro"})
        stream_markdown_as_html(out, root.intro)
        out.endElement("div")
    
    out.startElement("p", {})
    element(out, "button", 
            {"class": "btn btn-primary",
             "type": "button",
             "onclick": "code_guide.start()"},
            text="Explain!")
    out.endElement("p")
    out.startElement("div", {"class": "code-guide-code"})
    for e in root.children:
        _element_to_html(out, e)
    out.endElement("div")
    
    stream_html(out, """
       <div class="colophon">
         <p>Generated with <a href="http://github.com/npryce/code-guide">Code Guide</a>.</p>
       </div>
       """);
    
    out.endElement("body")
    out.endElement("html")


if __name__ == '__main__':
    code = lines_to_tagged_tree(code_lines(sys.argv[1]))
    to_html(code, resource_dir="resources", language="python")

