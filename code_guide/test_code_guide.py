

from code_guide import *
from code_guide import _root, _explanation
import io
import lxml.etree
from lxml.etree import XPathElementEvaluator
from lxml.sax import ElementTreeContentHandler
from xml.sax.saxutils import XMLGenerator

def root(children, intro=None, outro=None):
    return _root(intro=intro, outro=outro, children=children)

def explanation(text, children, index=None):
    return _explanation(text=text, children=children, index=index)

def test_vanilla_lines_to_tree():
    tree = lines_to_tagged_tree(["one", "two", "three"])
    assert tree == root([
        line("one"), 
        line("two"), 
        line("three")])

def test_tagged_lines_to_simple_tree():
    tree = lines_to_tagged_tree([
        "leading line",
        "#| some explanatory text",
        "tagged line 1",
        "tagged line 2",
        "#|.",
        "trailing line"])
    
    assert tree == root([
        line("leading line"), 
        explanation("some explanatory text", [
            line("tagged line 1"), 
            line("tagged line 2")]), 
        line("trailing line")])

def test_can_specify_comment_start_syntax():
    tree = lines_to_tagged_tree(comment_start=">>", lines=[
        "leading line",
        ">>| some explanatory text",
        "tagged line 1",
        "tagged line 2",
        ">>|.",
        "trailing line"])
    
    assert tree == root([
        line("leading line"), 
        explanation("some explanatory text", [
            line("tagged line 1"), 
            line("tagged line 2")]), 
        line("trailing line")])
    

def test_nested_tags():
    tree = lines_to_tagged_tree([
            "l1",
            "#| t1",
            "t1 l1",
            "  #| t1a",
            "  t1a l1",
            "  #|.",
            "t1 l2",
            "#|."])
    
    assert tree == root([
        line("l1"),
        explanation("t1", [
            line("t1 l1"),
            explanation("t1a", [
                line("  t1a l1")]),
            line("t1 l2")])])


def test_explicit_ordering():
    tree = lines_to_tagged_tree([
            "l1",
            "#| [2] step 2",
            "l2",
            "    #| [1] step 1",
            "    l3",
            "    #|.",
            "#|."])
    
    assert tree == root([
            line("l1"),
            explanation("step 2", index=2, children=[
                    line("l2"),
                    explanation("step 1", index=1, children=[
                            line("    l3")])])])


def test_multiple_lines_of_description():
    tree = lines_to_tagged_tree([
        "leading line",
        "#| some explanatory text",
        "#| more explanatory text",
        "tagged line 1",
        "tagged line 2",
        "#|.",
        "trailing line"])

    assert tree == root([
        line("leading line"), 
        explanation("some explanatory text\nmore explanatory text", [
            line("tagged line 1"), 
            line("tagged line 2")]), 
        line("trailing line")])

def test_blank_lines_in_description():
    tree = lines_to_tagged_tree([
            "line 1",
            "#| explanation line 1",
            "#|",
            "#| explanation line 2",
            "line 2",
            "#|."])
    
    assert tree == root([
            line("line 1"),
            explanation("explanation line 1\n\nexplanation line 2", [
                    line("line 2")])])
    

def test_intro_with_title():
    tree = lines_to_tagged_tree([
            "#|| The Title",
            "#|| =========",
            "#|| first line of intro",
            "#|| another line of intro",
            "",
            "#| some explanatory text",
            "a line",
            "#|."])
    
    assert tree == root(intro="The Title\n=========\nfirst line of intro\nanother line of intro", children=[
            line(""),
            explanation("some explanatory text", [
                    line("a line")])])


def test_intro_without_title():
    tree = lines_to_tagged_tree([
            "#|| first line of intro",
            "#|| another line of intro",
            "",
            "a line"])
    
    assert tree == root(intro="first line of intro\nanother line of intro", children=[
            line(""), 
            line("a line")])


def test_intro_with_blank_lines():
    tree = lines_to_tagged_tree([
            "#|| line 1",
            "#||",
            "#|| line 2",
            "#|| ",
            "#|| line 3",
            "",
            "a line"])
    
    assert tree == root(intro="line 1\n\nline 2\n\nline 3", children=[
            line(""), 
            line("a line")])


def test_outro_with_title():
    tree = lines_to_tagged_tree([
            "#|| intro",
            "",
            "#| some explanatory text",
            "a line",
            "#|.",
            "another line",
            "#|| outro"])
    
    assert tree == root(
        intro="intro", 
        children=[
            line(""),
            explanation("some explanatory text", [
                    line("a line")]),
            line("another line")], 
        outro="outro")


tree = root(
    intro="Example Code\n============\nIntro Text", 
    children=[
        line("l1"),
        explanation("A", [
                line("l2"),
                line(""),
                line("l3"),
                explanation("B", [
                        line("l4"),
                        line("l5")]),
                line("l6")]),
        explanation("C", [
                line("l7")]),
        line("l8")],
    outro="That's all, folks!")


scripts = ["bootstrap/js/bootstrap.min.js",
           "bootstro.min.js",
           "jquery-1.9.1.min.js",
           "code-guide.js"]
    
stylesheets = ["bootstrap/css/bootstrap.min.css",
               "bootstro.min.css",
               "pygments.css",
               "code-guide.css"]

def test_code_translated_to_html_div():
    generated = code_to_html(tree)
    
    for e in generated("//@data-bootstro-content"):
        print e

    assert generated("string(//*[@class='code-guide-code'])") == "l1\nl2\n \nl3\nl4\nl5\nl6\nl7\nl8\n"
    
    assert generated("string((//@data-bootstro-content)[1])") == "<p>A</p>"
    assert generated("string((//*[@data-bootstro-content])[1])") == "l2\n \nl3\nl4\nl5\nl6\n"
    
    assert generated("string((//@data-bootstro-content)[2])") == "<p>B</p>"
    assert generated("string((//*[@data-bootstro-content])[2])") == "l4\nl5\n"
    
    assert generated("string((//@data-bootstro-content)[3])") == "<p>C</p>"
    assert generated("string((//*[@data-bootstro-content])[3])") == "l7\n"


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
    
    assert generated("string(/html/body//h1)").rstrip() == "Example Code"
    assert generated("string(/html/head/title)") == "Example Code"


def test_intro():
    generated = code_to_html(tree)
    
    assert generated("/html/body//div[@class='code-guide-intro']/p[text() = 'Intro Text']")


def test_outro():
    generated = code_to_html(tree)
    
    assert generated("string(/html/body//div[@class='code-guide-outro'])") == "That's all, folks!"
    

def test_explicit_ordering_as_html():
    tree = root([
            explanation("e2", index=2, children=[line("l1")]),
            explanation("e1", index=1, children=[line("l2")])])
    
    generated = code_to_html(tree)
    
    assert generated("string(//*[@data-bootstro-step='0'])") == "l2\n"
    assert generated("string(//*[@data-bootstro-step='1'])") == "l1\n"


def test_code_link_translation():
    tree = root(
        intro = "There is [example code](example2.py) here...",
        children = [],
        outro = "And [more example code](example3.py) there...")
    
    generated = code_to_html(tree, link_transform_fn=re_subn(r"(.*)\.py", r"\1.html"))
    
    print lxml.etree.tostring(generated(".")[0], pretty_print=True)
    
    assert generated("string(//a[@href='example2.html'])") == "example code"
    assert generated("string(//a[@href='example3.html'])") == "more example code"


def code_to_html(tree, **kwargs):
    b = io.BytesIO()
    to_html(tree, XMLGenerator(b), **kwargs)
    return XPathElementEvaluator(lxml.etree.fromstring(b.getvalue()))

def assert_html_equals(actual, expected_as_str):
    actual_norm = normalised(lxml.etree.tostring(actual, method="c14n", pretty_print=False))
    expected_norm = normalised(expected_as_str)
    assert actual_norm == expected_norm
    
def normalised(xml_str):
    e = lxml.etree.fromstring(xml_str, parser=lxml.etree.XMLParser(remove_blank_text=True))
    return lxml.etree.tostring(e, method="c14n", pretty_print=False)
