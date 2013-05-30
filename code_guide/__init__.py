#!/usr/bin/env python

import sys
import re
from collections import namedtuple
from operator import itemgetter as item
from itertools import groupby, islice
import argparse
import os
from shutil import copyfileobj
import urllib
from pkg_resources import resource_listdir, resource_isdir, resource_stream
import xml.sax
from xml.sax.saxutils import XMLGenerator, XMLFilterBase
from xml.etree.ElementTree import fromstring as etree_from_string
import markdown
import pygments
import pygments.lexers
from pygments.formatters import HtmlFormatter

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
    intro_pattern = re.compile(r'^\s*' + comment_start_re + '\|\|(\s*| (?P<text>.+?))$')
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
    out.endElement(e.tag)
    if e.tail is not None:
        out.characters(e.tail)



def _code_tree_to_html(out, e, code_lexer, md):
    t = type(e)
    if t == line:
        stream_html(out, pygments.highlight(" " if e.text == "" else e.text, code_lexer, HtmlFormatter(cssclass="", classprefix="code-guide-syntax-")))
    elif t == _explanation:
        attrs = {
            "class": "bootstro", 
            "data-bootstro-content": md.convert(e.text),
            "data-bootstro-html": "true",
            "data-bootstro-placement": "right",
            "data-bootstro-width": "25%"}
            
        if e.index is not None:
            attrs["data-bootstro-step"] = str(e.index - 1)
                
        out.startElement("div", attrs)
                    
        for c in e.children:
            _code_tree_to_html(out, c, code_lexer, md)
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
            "bootstro{min}.js",
            "code-guide.js"]
    
_stylesheets = ["bootstrap/css/bootstrap{min}.css",
                "bootstro{min}.css",
                "pygments.css",
                "code-guide.css"]


def identity(x):
    return x

def re_subn(regex, subn):
    p = re.compile(regex)
    return lambda s: p.subn(subn, s)[0]



class LinkTransformer(object):
    def __init__(self, link_transform_fn):
        self.link_transform_fn = link_transform_fn
        
    def run(self, tree):
        for link in tree.findall(".//a"):
            href = link.get('href')
            if href is not None:
                link.set('href', self.link_transform_fn(href))
        
        return tree


def to_html(root, out=None, syntax_highlight="python", resource_dir="", minified=True, link_transform_fn=identity):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    code_lexer = pygments.lexers.get_lexer_by_name(syntax_highlight)
    
    md = markdown.Markdown(safe_mode="escape", output_format="xhtml5")
    md.treeprocessors["codelinks"] = LinkTransformer(link_transform_fn)
    
    resource_prefix = resource_dir if resource_dir == "" or resource_dir.endswith("/") else resource_dir + "/"
    min_suffix = ".min" if minified else ""
    
    def resource(r):
        return resource_prefix + r.format(min=min_suffix)
    
    def stylesheet(relpath):
        element(out, "link", {"rel": "stylesheet", "type": "text/css", "href": resource(relpath)})
    
    def script(relpath):
        element(out, "script", {"type": "text/javascript", "src": resource(relpath)})
    
    if root.intro:
        intro_etree = etree_from_string('<div class="code-guide-intro">' + md.convert(root.intro) + '</div>')
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
        _code_tree_to_html(out, e, code_lexer, md)
    out.endElement("div")
    
    if root.outro:
        stream_element(out, etree_from_string('<div class="code-guide-outro">' + md.convert(root.outro) + '</div>'))
    
    stream_html(out, """
       <div class="colophon">
         <p>Generated with <a href="http://github.com/npryce/code-guide">Code Guide</a>.</p>
       </div>
       """);
    
    out.endElement("body")
    out.endElement("html")


def is_html_resource(r):
    return not (r.endswith(".py") or r.endswith(".pyc"))


def resource_names(d="."):
    for n in resource_listdir(__name__, d):
        r = d + "/" + n
        
        if resource_isdir(__name__, r):
            for n2 in resource_names(r):
                yield n2
        elif is_html_resource(r):
            yield r

def extract_resource(r, basedir):
    outf = os.path.join(basedir,r)
    outdir = os.path.dirname(outf)
    
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    
    with resource_stream(__name__, r) as input, open(outf, "w") as output:
        copyfileobj(input, output)



def lines(input):
    return [l.rstrip('\n') for l in input]


def _only_extract_resources(args):
    return args.source is None and args.output is None and args.extract_resources

def extract_resources(output, resource_dir):
    dst_dir = urllib.url2pathname(urllib.basejoin("." if output is None else output, resource_dir))
    extract_resources_to(dst_dir)
    
def extract_resources_to(d):
    for r in resource_names():
        extract_resource(r, d)

def use_stdio(fname):
    return fname is None or fname == "-"

def cli(argv):
    parser = argparse.ArgumentParser(description="Generate interactive HTML documentation from example code",
                                     epilog="If --extract-resources is given but source and output are not, %(prog)s "
                                            "only writes out the resources and does not convert stdin to stdout")

    parser.add_argument('-l', '--highlight', dest='syntax_highlight', default='python', metavar='LANGUAGE',
                        help='apply syntax highlighting for language LANGUAGE (default: %(default)s)')
    parser.add_argument('-c', '--comment-start', dest='comment_start', default='#',
                        help='the syntax used to start single-line comments (default: %(default)s)')
    parser.add_argument('-o', '--output', dest='output', default=None,
                        help='output file (default: write to stdout)')
    parser.add_argument('-t', '--link-transform', dest='link_transform_fn', nargs=2, metavar=('REGEX','SUBSTITUTION'),
                        default=None,
                        help='transform link URLs by regex substitution (default: no transforms are applied)')
    parser.add_argument('-r', '--resource-dir', dest='resource_dir', metavar='RESOURCE_DIR', default='code_guide',
                        help='prepend directory DIR to the relative URLs of scripts and stylesheets')
    parser.add_argument('-x', '--extract-resources', dest='extract_resources', default=False, action='store_true',
                        help="extract resources to RESOURCE_DIR (default=no)")
    parser.add_argument('source', nargs='?', default=None, metavar='file',
                        help='source file of example code (default: read from stdin)')
    
    args = parser.parse_args(argv[1:])
    
    if not _only_extract_resources(args):
        to_html(lines_to_tagged_tree(lines(sys.stdin if use_stdio(args.source) else open(args.source, "r")), args.comment_start),
                resource_dir=args.resource_dir,
                syntax_highlight=args.syntax_highlight,
                link_transform_fn=identity if args.link_transform_fn is None else re_subn(*args.link_transform_fn),
                out=XMLGenerator(sys.stdout if use_stdio(args.output) else open(args.output, "w")))
    
    if args.extract_resources:
        extract_resources(args.output, args.resource_dir)
