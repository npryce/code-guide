#!/usr/bin/env python

import sys
import re
from  xml.sax.saxutils import XMLGenerator


def root(*elts):
    return list(elts)

def highlight(description, *elts):
    return (description, elts)

def line(text):
    return text

def is_line(elt):
    return type(elt) == str

def is_highlight(elt):
    return type(elt) == tuple and len(elt) == 2


def lines_to_tagged_tree(lines):
    return root(*_siblings(iter(lines)))

_tag_start_pattern = re.compile("^\\s*##\\s+(?P<text>.+?)\\s*$")
_tag_end_pattern = re.compile("^\\s*###\\s*$")

def _siblings(line_iter):
    for l in line_iter:
        match = _tag_start_pattern.match(l)
        if match is not None:
            text = match.group("text")
            yield highlight(text, *tuple(_siblings(line_iter)))
        else:
            match = _tag_end_pattern.match(l)
            if match is not None:
                return
            else:
                yield l


def code_lines(f):
    with open(f) as input:
        return [l.rstrip('\n') for l in input]


def to_html(tree, root_attrs={}, out=XMLGenerator(sys.stdout)):
    if out is None:
        out = XMLGenerator(sys.stdout)
    
    def _element_to_html(e):
        if is_line(e):
            out.startElement("pre", {})
            out.characters(e)
            out.endElement("pre")
        elif is_highlight(e):
            description, content = e
            out.startElement("div", {"class": "bootstro", "data-bootstro-content": description})
            for e in content:
                _element_to_html(e)
            out.endElement("div")

    out.startElement("div", root_attrs)
    for e in tree:
        _element_to_html(e)
    out.endElement("div")



if __name__ == '__main__':
    import sys
    to_html(lines_to_tagged_tree(code_lines(sys.argv[1])))

