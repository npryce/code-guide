#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from operator import itemgetter as item
from itertools import groupby, islice
import xml.sax
from xml.sax.saxutils import XMLGenerator, XMLFilterBase
from xml.etree.ElementTree import fromstring as etree_from_string
from markdown import markdown
import pygments
import pygments.lexers
from pygments.formatters import HtmlFormatter
import argparse


_parsed_line = namedtuple('_parsed_line', ['group_fn', 'line', 'parts'])

_root = namedtuple('root', ['children', 'intro', 'outro'])
_explanation = namedtuple('explanation', ['text', 'index', 'children'])
line = namedtuple('line', ['text'])
_intro = namedtuple('intro', ['text'])

_start = namedtuple('_start', ['text', 'index'])
_end = namedtuple('_end', [])



def _join_text(lines_with_text):
    return "\n".join(l.parts.get('text') or "" for l in lines_with_text)

def _start_index(line):
    index_str = line.parts.get('index', None)
    return int(index_str) if index_str is not None else None


def _intro_group(lines):
    yield _intro(_join_text(lines))

def _start_group(lines):
    lines = list(lines)
    yield _start(index=_start_index(lines[0]), text=_join_text(lines))

def _end_group(lines):
    for l in lines:
        yield _end()

def _line_group(lines):
    for l in lines:
        yield line(l.line)



def _parse_lines(lines, comment_start):
    comment_start_re = re.escape(comment_start)
    intro_pattern = re.compile(r'^\s*' + comment_start_re + '\|\|( (?P<text>.+?))?$')
    region_start_pattern = re.compile(r'^\s*' + comment_start_re + '\|(( \[(?P<index>[0-9]+)\]\s*)? (?P<text>.*?))?$')
    region_end_pattern = re.compile(r'^\s*' + comment_start_re + '\|\.\s*$')
    
    # The order in which these patterns are checked is important to avoid ambiguity.
    _line_groups = [
        (intro_pattern, _intro_group),
        (region_end_pattern, _end_group),
        (region_start_pattern, _start_group)]
    
    def _parse_line(l):
        for pattern, group_fn in _line_groups:
            m = pattern.match(l)
            if m is not None:
                return _parsed_line(group_fn, l, m.groupdict())
        else:
            return _parsed_line(_line_group, l, {})
    
    return (_parse_line(l) for l in lines)

def _delimited(parsed_lines):
    for group_fn, group_lines in groupby(parsed_lines, item(0)):
        for e in group_fn(group_lines):
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


def lines_to_tagged_tree(lines, comment_start="#"):
    parse = list(_to_tree(_delimited(_parse_lines(lines, comment_start))))
    children = filter(lambda e: type(e) != _intro, parse)
    intros = list(filter(lambda e: type(e) == _intro, parse))
    
    if len(intros) > 0:
        intro_text = intros[0].text
    else:
        intro_text = None
    
    if len(intros) > 1:
        outro_text = intros[-1].text
    else:
        outro_text = None
    
    return _root(intro=intro_text, outro=outro_text, children=children)



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
        intro_etree = etree_from_string('<div class="code-guide-intro">' + markdown_to_xml(root.intro) + '</div>')
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
    
    if root.outro:
        stream_element(out, etree_from_string('<div class="code-guide-outro">' + markdown_to_xml(root.outro) + '</div>'))
    
    stream_html(out, """
       <div class="colophon">
         <p>Generated with <a href="http://github.com/npryce/code-guide">Code Guide</a>.</p>
       </div>
       """);
    
    out.endElement("body")
    out.endElement("html")



def lines(input):
    return [l.rstrip('\n') for l in input]

def cli(argv):
    parser = argparse.ArgumentParser(description="Generate interactive HTML documentation from example code")
    parser.add_argument('-r', '--resource-dir', dest='resource_dir', metavar='DIR', default='resources',
                        help='prepend directory DIR to the relative URLs of scripts and stylesheets')
    parser.add_argument('-l', '--highlight', dest='syntax_highlight', default='python', metavar='LANGUAGE',
                        help='apply syntax highlighting for language LANGUAGE')
    parser.add_argument('-c', '--comment-start', dest='comment_start', default='#',
                        help='the syntax used to start single-line comments')
    parser.add_argument('-o', '--output', dest='output', type=argparse.FileType('w'), default='-',
                        help='output file (default: write to stdout)')
    parser.add_argument('source', type=argparse.FileType('r'), nargs='?', default='-',
                        help='source file of example code (default: read from stdin)')
    
    args = parser.parse_args(argv[1:])
    
    to_html(lines_to_tagged_tree(lines(args.source), args.comment_start),
            resource_dir=args.resource_dir, 
            syntax_highlight=args.syntax_highlight,
            out=XMLGenerator(args.output))
    

if __name__ == '__main__':
    cli(sys.argv)

