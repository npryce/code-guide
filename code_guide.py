#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from itertools import groupby, islice
import xml.sax
from xml.sax.saxutils import XMLGenerator, XMLFilterBase
from xml.etree.ElementTree import fromstring as etree_from_string
from markdown import markdown
import pygments
import pygments.lexers
from pygments.formatters import HtmlFormatter

_intro_pattern = re.compile(r'^\s*#\|\|( (?P<text>.+?))?$')
_region_start_pattern = re.compile(r'^\s*#\|(( \[(?P<index>[0-9]+)\]\s*)? (?P<text>.*?))?$')
_region_end_pattern = re.compile(r'^\s*#\|\.\s*$')

_root = namedtuple('root', ['children', 'intro'])
_explanation = namedtuple('explanation', ['text', 'index', 'children'])
line = namedtuple('line', ['text'])
_title = namedtuple('title', ['text'])
_intro = namedtuple('intro', ['text'])

_start = namedtuple('_start', ['text', 'index'])
_end = namedtuple('_end', [])

def _significant_text(line, pattern):
    return pattern.match(line).group("text") or ""

def _join_text(tag_start_lines, pattern):
    return "\n".join(_significant_text(l, pattern) for l in tag_start_lines)

def _map_or_none(f, v):
    return None if v is None else f(v)


def _start_index(line, pattern):
    return _map_or_none(int, pattern.match(line).groupdict().get('index', None))

def _intro_group(lines):
    yield _intro(_join_text(lines, _intro_pattern))

def _start_group(lines):
    lines = list(lines)
    yield _start(index=_start_index(lines[0], _region_start_pattern),
                 text=_join_text(lines, _region_start_pattern))

def _end_group(lines):
    for l in lines:
        yield _end()

def _line_group(lines):
    for l in lines:
        yield line(l)


# The order in which these patterns are checked is important to avoid ambiguity.
_line_groups = [
    (_intro_pattern, _intro_group),
    (_region_end_pattern, _end_group),
    (_region_start_pattern, _start_group)]

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
            yield _explanation(text=e.text, index=e.index, children=list(_to_tree(delimited_lines)))
        elif t == _end:
            return
        else:
            yield e


def lines_to_tagged_tree(lines):
    parse = list(_to_tree(_delimited(lines)))
    children = filter(lambda e: type(e) != _intro, parse)
    intros = list(filter(lambda e: type(e) == _intro, parse))
    
    if intros:
        intro_text = intros[0].text
    else:
        intro_text = None

    return _root(intro=intro_text, children=children)


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

def stream_element(out, e):
    out.startElement(e.tag, e.attrib)
    if e.text is not None:
        out.characters(e.text)
    for c in e:
        stream_element(out, c)
    if e.tail is not None:
        out.characters(e.tail)
    out.endElement(e.tag)


def markdown_to_xml(markdown_str):
    return markdown(markdown_str, safe_mode="escape", output_format="xhtml5")


def _code_tree_to_html(out, e, code_lexer):
    t = type(e)
    if t == line:
        stream_html(out, pygments.highlight(" " if e.text == "" else e.text, code_lexer, HtmlFormatter(cssclass="", classprefix="code-guide-syntax-")))
    elif t == _explanation:
        attrs = {
            "class": "bootstro", 
            "data-bootstro-content": markdown_to_xml(e.text),
            "data-bootstro-html": "true",
            "data-bootstro-placement": "right",
            "data-bootstro-width": "25%"}
            
        if e.index is not None:
            attrs["data-bootstro-step"] = str(e.index - 1)
                
        out.startElement("div", attrs)
                    
        for c in e.children:
            _code_tree_to_html(out, c, code_lexer)
        out.endElement("div")
    else:
        raise ValueError("unexpected node: " + repr(e))


def element(out, name, attrs, text=None):
    out.startElement(name, attrs)
    if text is not None:
        out.characters(text)
    out.endElement(name)


_scripts = ["jquery-1.9.1{min}.js",
            "bootstrap/js/bootstrap{min}.js",
           "bootstro/bootstro{min}.js",
           "code-guide.js"]
    
_stylesheets = ["bootstrap/css/bootstrap{min}.css",
                "bootstro/bootstro{min}.css",
                "pygments.css",
                "code-guide.css"]



def to_html(root, out=None, syntax_highlight="python", resource_dir="", minified=True):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    code_lexer = pygments.lexers.get_lexer_by_name(syntax_highlight)
    
    resource_prefix = resource_dir if resource_dir == "" or resource_dir.endswith("/") else resource_dir + "/"
    min_suffix = ".min" if minified else ""
    
    def resource(r):
        return resource_prefix + r.format(min=min_suffix)
    
    def stylesheet(relpath):
        element(out, "link", {"rel": "stylesheet", "type": "text/css", "href": resource(relpath)})
    
    def script(relpath):
        element(out, "script", {"type": "text/javascript", "src": resource(relpath)})
    
    if root.intro:
        intro_etree = etree_from_string('<div class="code-guide-intro">' + markdown_to_xml(root.intro) + "</div>")
        h1 = intro_etree.find("h1")
        title = None if h1 is None else "".join(h1.itertext())
    else:
        intro_etree = None
        title = None
    
    out.startElement("html", {})
    
    out.startElement("head", {})
    if title is not None:
        element(out, "title", {}, text=title)
    for s in _stylesheets:
        stylesheet(s)
    for s in _scripts:
        script(s)
    out.endElement("head")
    
    out.startElement("body", {})
    
    if intro_etree is not None:
        stream_element(out, intro_etree)
    
    out.startElement("p", {})
    element(out, "button", 
            {"class": "btn btn-primary",
             "type": "button",
             "onclick": "code_guide.start()"},
            text="Explain!")
    out.endElement("p")
    
    out.startElement("div", {"class": "code-guide-code"})
    for e in root.children:
        _code_tree_to_html(out, e, code_lexer)
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
    to_html(code, resource_dir="resources", syntax_highlight="python")

