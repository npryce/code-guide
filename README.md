Code Guide
==========

A tool that generates an interactive HTML explanation of how code works from unobtrusive markup of comments in the code. 
The explanation is readable in the source, as well as in the generated documentation.


Installation
============

Currently completely manual.  You can install dependencies with `pip install -r requirements.txt`.

Run with: `python src/code_guide.py <input-file> > <output-file>`.   Then copy shared resources (JavaScript and CSS) from resources/ to wherever you are saving generated documents.

Installation via PyPI coming soon... 


Very Brief Documentation
========================

Mark up regions of code to be explained by adding line comments that immediately start with a "|" character at the start of the region, 
and a line comment that starts with "|." at the end of the region.

E.g., in Python:

    #| This is the start
    some_code()
    #|.
    
    
In Java:

    //| This is the start
    SomeCodeFactoryFactoryImpl.getSomeCodeFactory().getSomeCode().callIt();
    //|.
    
The rest of this document describes using the tool with a language that has line comments starting with "#", 
but the documentation applies to just as well languages with a different line-comment syntax.

Adjacent #| comments are treated as a single block of Markdown syntax.  Regions can be nested but not overlap.

    #| This if statement compares two numbers.
    #|
    #| It copes with floating point _NaN_ values.
    if a > b:
        print "larger"
    elif a < b:
        print "smaller"
    elif a == b:
        print "the same"
    else:
        #| _NaN_ is never equal to another floating point value, not even to _NaN_.
        print "NaN"
        #|.
    #|.


The order in which explanations are presented to the reader can be controlled by adding 
indices in square brackets at the start of each #| comment block.  Indices start at 1.  
Either all or none of the explanations must have an index.  If no explanations have an index, 
they are shown in the order they appear in the source code.


    #| [2] This statement will be explained second.
    print "goodbye, cruel world."
    #|.

    #| [1] This statement will be explained first.
    sys.exit(1)
    #|.

The generated document can be given an introduction in markdown format.  
Introduction text is a block of adjacent lines that start with #||.  
If the introduction has a top-level heading, the text of the heading is 
used as the title of the generated HTML.

Only the first block of introduction text will be used.  Any later ones 
will be silently ignored (and may cause an error in future versions of the tool).


    #|| Hello World
    #|| ===========
    #||
    #|| Hello world is traditionally used to illustrate to beginners 
    #|| the most basic syntax of a programming language, or to verify 
    #|| that a language or system is operating correctly.
    
    #| This is all that is required in Python
    print "hello, world"
    #|.

