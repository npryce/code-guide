

from code_guide import *
from code_guide import _root
import io
import lxml.etree
from lxml.etree import XPathElementEvaluator
from lxml.sax import ElementTreeContentHandler
from xml.sax.saxutils import XMLGenerator

def root(children, title=None, intro=None):
    return _root(title=title, intro=intro, children=children)

def test_vanilla_lines_to_tree():
    tree = lines_to_tagged_tree(["one", "two", "three"])
    assert tree == root([
        line("one"), 
        line("two"), 
        line("three")])

def test_tagged_lines_to_simple_tree():
    tree = lines_to_tagged_tree([
        "leading line",
        "## some explanatory text",
        "tagged line 1",
        "tagged line 2",
        "##.",
        "trailing line"])
    
    assert tree == root([
        line("leading line"), 
        highlight("some explanatory text", [
            line("tagged line 1"), 
            line("tagged line 2")]), 
        line("trailing line")])
    

def test_nested_tags():
    tree = lines_to_tagged_tree([
            "l1",
            "## t1",
            "t1 l1",
            "  ## t1a",
            "  t1a l1",
            "  ##.",
            "t1 l2",
            "##."])
    
    assert tree == root([
        line("l1"),
        highlight("t1", [
            line("t1 l1"),
            highlight("t1a", [
                line("  t1a l1")]),
            line("t1 l2")])])


def test_multiple_lines_of_description():
    tree = lines_to_tagged_tree([
        "leading line",
        "## some explanatory text",
        "## more explanatory text",
        "tagged line 1",
        "tagged line 2",
        "##.",
        "trailing line"])

    assert tree == root([
        line("leading line"), 
        highlight("some explanatory text\nmore explanatory text", [
            line("tagged line 1"), 
            line("tagged line 2")]), 
        line("trailing line")])


def test_title():
    tree = lines_to_tagged_tree([
            "#### The Title ####",
            "",
            "## some explanatory text",
            "a line"])
    
    assert tree == root(title="The Title", children=[
            line(""),
            highlight("some explanatory text", [
                    line("a line")])])




tree = root(title="Example Code", intro="Intro Text", children=[
        line("l1"),
        highlight("A", [
                line("l2"),
                line(""),
                line("l3"),
                highlight("B", [
                        line("l4"),
                        line("l5")]),
                line("l6")]),
        highlight("C", [
                line("l7")]),
        line("l8")])


scripts = ["bootstrap/js/bootstrap.min.js",
           "bootstro/bootstro.min.js",
           "jquery-1.9.1.min.js",
           "code-guide.js"]
    
stylesheets = ["bootstrap/css/bootstrap.min.css",
               "bootstro/bootstro.min.css",
               "code-guide.css"]

def code_to_html(tree, **kwargs):
    b = io.BytesIO()
    to_html(tree, XMLGenerator(b), **kwargs)
    return XPathElementEvaluator(lxml.etree.fromstring(b.getvalue()))


def test_code_translated_to_html_div():    
    generated = code_to_html(tree)
    
    assert_html_equals(generated("//div[@class='code-guide-code']")[0], """
        <div class="code-guide-code">
          <pre>l1</pre>
          <div class="bootstro" data-bootstro-content="A" data-bootstro-placement="right" data-bootstro-width="25%">
            <pre>l2</pre>
            <pre> </pre>
            <pre>l3</pre>
            <div class="bootstro" data-bootstro-content="B" data-bootstro-placement="right" data-bootstro-width="25%">
              <pre>l4</pre>
              <pre>l5</pre>
            </div>
            <pre>l6</pre>
          </div>
          <div class="bootstro" data-bootstro-content="C" data-bootstro-placement="right" data-bootstro-width="25%">
            <pre>l7</pre>
          </div>
          <pre>l8</pre>
        </div>
        """)

def test_script_and_stylesheet_links_in_head():
    generated = code_to_html(tree)
        
    for s in scripts:
        assert generated("/html/head/script[@src=$src][@type='text/javascript']", src=s)
    
    for s in stylesheets:
        assert generated("/html/head/link[@href=$href][@rel='stylesheet'][@type='text/css']", href=s)


def test_script_and_stylesheet_links_can_be_prefixed_with_resource_directory():
    generated = code_to_html(tree, resource_dir="over/here")
        
    for s in scripts:
        assert generated("/html/head/script[@src=$src][@type='text/javascript']", src="over/here/"+s)
    
    for s in stylesheets:
        assert generated("/html/head/link[@href=$href][@rel='stylesheet'][@type='text/css']", href="over/here/"+s)


def test_explain_button():
    generated = code_to_html(tree)
    
    assert generated("/html/body//button[text() = 'Explain!'][@class = 'btn btn-primary'][@type='button']")


def test_title():
    generated = code_to_html(tree)
    
    assert generated("/html/body//h1[text() = 'Example Code']")
    assert generated("/html/head/title[text() = 'Example Code']")


def test_intro():
    generated = code_to_html(tree)
    
    assert generated("/html/body//p[@class='code-guide-intro'][text() = 'Intro Text']")

def assert_html_equals(actual, expected_as_str):
    actual_norm = normalised(lxml.etree.tostring(actual, method="c14n", pretty_print=False))
    expected_norm = normalised(expected_as_str)
    assert actual_norm == expected_norm
    
def normalised(xml_str):
    e = lxml.etree.fromstring(xml_str, parser=lxml.etree.XMLParser(remove_blank_text=True))
    return lxml.etree.tostring(e, method="c14n", pretty_print=False)
