

from code_guide import *
import io
import lxml.etree
from xml.sax.saxutils import XMLGenerator


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
        "###",
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
            "  ###",
            "t1 l2",
            "###"])
    
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
        "###",
        "trailing line"])

    assert tree == root([
        line("leading line"), 
        highlight("some explanatory text more explanatory text", [
            line("tagged line 1"), 
            line("tagged line 2")]), 
        line("trailing line")])
    


def test_tags_to_html():
    tree = root([
        line("l1"),
        highlight("A", [
            line("l2"),
            line("l3"),
            highlight("B", [
                line("l4"),
                line("l5")]),
            line("l6")]),
        highlight("C", [
            line("l7")]),
        line("l8")])
    
    b = io.BytesIO()
    g = XMLGenerator(b)
    
    to_html(tree, {"class": "example"}, g)
    
    assert_html_equal(b.getvalue(),
        """<div class="example">
          <pre>l1</pre>
          <div class="bootstro" data-bootstro-content="A">
            <pre>l2</pre>
            <pre>l3</pre>
            <div class="bootstro" data-bootstro-content="B">
              <pre>l4</pre>
              <pre>l5</pre>
            </div>
            <pre>l6</pre>
          </div>
          <div class="bootstro" data-bootstro-content="C">
            <pre>l7</pre>
          </div>
          <pre>l8</pre>
        </div>""")
    

def assert_html_equal(h1, h2):
    n1 = normalised(h1)
    print n1
    n2 = normalised(h2)
    print n2
    assert n1 == n2
    
def normalised(xml_str):
    e = lxml.etree.fromstring(xml_str, parser=lxml.etree.XMLParser(remove_blank_text=True))
    return lxml.etree.tostring(e, method="c14n", pretty_print=True)
