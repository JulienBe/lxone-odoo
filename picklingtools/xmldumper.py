#!/bin/env python

"""
   This class convert dictionaries to XML.  This is usually
   an easy mapping, because key-value mappings go easily to XML
   (the other way is more problematic).  A potential issue
   usually is how to handle attributes.... See the options below!

   Examples:

    { 'book' = {
          'chapter' = [ 'text chap 1', 'text chap 2']
          '__attrs__' = { 'attr1':"1", 'attr2':"2" }
    }
    --------dumps as --------------
    <book attr1="1" attr2="2">
       <chapter>text chap 1</chapter>
        <chapter>text chap 2</chapter>
    </book>


   With UNFOLDING on  (attributes are marked with _)

    { 'book' = {
          'chapter' = [ 'text chap 1', 'text chap 2']
          '_attr1':"1",
          '_attr2':"2"
       }
    }
    ---------dumps as --------------
    <book attr1="1" attr2="2">
        <chapter date="1999">text chap 1</chapter>
        <chapter data="2000">text chap 2</chapter>
    </book>
"""

import sys
import pretty
from curses.ascii import isprint

# Not until 2.7, keep as plain dict then
try :
    from collections import OrderedDict
except :
    OrderedDict = dict

# All the arrays we may get when iterating through: if someone gives
# us the data structure (Numeric array or Python array), we still try
# to dump it.
try :
    import array
    array_types.append(type(array.array()))
    from array import array
except :
    pass

from arraydisposition import *
array_types = []
try :
    import Numeric
    array_types.append(type(Numeric.array([]))) # Tag doesn't effect type
    print 'HERE'
    from Numeric import array
except :
    pass

# For converting Numeric typecodes to OC typecodes
NumericToOCMap = {
    '1':'s',
    'b':'S',
    's':'i',
    'w':'I',
    'i':'l',
    'u':'L',
    'l':'x',
    # 'l':'X':'l',
    'f':'f',
    'd':'d',
    'F':'F',
    'D':'D'
    }

try :
    import numpy
    array_types.append(type(numpy.array([],'i')))
    from numpy import array
    NumPyToNumericMap = {
        numpy.dtype('int8'):'1',
        numpy.dtype('uint8'):'b',
        numpy.dtype('int16'):'s',
        numpy.dtype('uint16'):'w',
        numpy.dtype('int32'):'i',
        numpy.dtype('uint32'):'u',
        numpy.dtype('int64'):'l',
        numpy.dtype('uint64'):'l',
        numpy.dtype('float32'):'f',
        numpy.dtype('float64'):'d',
        numpy.dtype('complex64'):'F',
        numpy.dtype('complex128'):'D'
        }
    NumPyToOCMap = {
        numpy.dtype('int8'):'s',
        numpy.dtype('uint8'):'S',
        numpy.dtype('int16'):'i',
        numpy.dtype('uint16'):'I',
        numpy.dtype('int32'):'l',
        numpy.dtype('uint32'):'L',
        numpy.dtype('int64'):'x',
        numpy.dtype('uint64'):'X',
        numpy.dtype('float32'):'f',
        numpy.dtype('float64'):'d',
        numpy.dtype('complex64'):'F',
        numpy.dtype('complex128'):'D'
        }
except :
    pass
import simplearray
array_types.append(type(simplearray.SimpleArray([], 'i')))
try :
    if array == array : pass
except :
    from simplearray import array


import pretty

from xmldumper_defs import *

class XMLDumper(object) :
  """An instance of this will help dump a Python object (made up of lists,
     dictionaries, Numeric/NumPy data and all primitive types as XML"""

  # On error, do you want to throw exception, silently continue or warn
  # on stderr?  Usually errors happens when there are multiple attributes
  # that conflict.
  SILENT_ON_ERROR = 1
  CERR_ON_ERROR   = 2
  THROW_ON_ERROR  = 3

  def __init__ (self, os, options=0,
                array_disposition=ARRAYDISPOSITION_AS_LIST,
                indent_increment=4,
                prepend_char=XML_PREPEND_CHAR,
                mode = 2) : # XMLDumper.CERR_ON_ERROR
      """Create am XML dumper.  Note that options are | together:
      XMLDumper xd(cout, XML_DUMP_PRETTY | XML_STRICT_HDR)
      """
      # Handle
      if array_disposition == ARRAYDISPOSITION_AS_NUMERIC :
          import Numeric # let this throw the exception
      if array_disposition == ARRAYDISPOSITION_AS_NUMERIC_WRAPPER :
          import simplearray # let this throw the exception
      if array_disposition == ARRAYDISPOSITION_AS_PYTHON_ARRAY :
          import array   # let this throw the exception
      if array_disposition == ARRAYDISPOSITION_AS_NUMPY :
          import array   # let this throw the exception

      self.os_ = os
      self.options_ = options
      self.arrDisp_ = array_disposition
      self.indentIncrement_ = indent_increment
      self.prependChar_ = prepend_char
      self.mode_ = mode
      self.specialCharToEscapeSeq_ = { }
      self.NULLKey_ = None  # Has to be non-string meta-value so "is" test won't fail with ""
      self.EMPTYAttrs_ = { }
      self.LISTAttrs_ = { }
      self.DICTTag_ = "dict__"

      self.specialCharToEscapeSeq_['&'] = "&amp;"
      self.specialCharToEscapeSeq_['<'] = "&lt;"
      self.specialCharToEscapeSeq_['>'] = "&gt;"
      self.specialCharToEscapeSeq_['\"'] = "&quot;"
      self.specialCharToEscapeSeq_['\''] = "&apos;"
      self.LISTAttrs_["type__"] = "list"

      # ostream& os_;             // Stream outputting to
      # int options_;             // OR ed options
      # ArrayDisposition_e arrDisp_; // How to handle POD data
      # int indentIncrement_; // How much to up the indent at each nesting level
      # char prependChar_;        // '\0' means NO prepend char
      # XMLDumpErrorMode_e mode_; // How to handle errors: silent, cerr,or throw
      # HashTableT<char, string, 8>
      # specialCharToEscapeSeq_;  // Handle XML escape sequences
      # string NULLKey_;          // Empty key
      # Tab    EMPTYAttrs_;       // Empty Attrs when dumping a primitive
      # Tab    LISTAttrs_;        // { "type__" = 'list' }
      # string DICTTag_;          // "dict__"


  def XMLDumpValue (self, value, indent=0) :
      "Dump without a top-level container (i.e., no containing top-level tag)"
      self.XMLDumpKeyValue(self.NULLKey_, value, indent) # handles header too

  def XMLDumpKeyValue (self, key, value, indent=0) :
      "Dump with the given top-level key as the top-level tag."
      self._XMLHeader()

      # Top level lists suck: you can't "really" have a
      # list at the top level of an XML document, only
      # a table that contains a list!
      if type(value)==list :
          a = value
          p = a        # DO NOT adopt, just sharing reference
          top = { }
          top["list__"] = p
          self._XMLDumpKeyValue(key, top, indent)
      else :
          self._XMLDumpKeyValue(key, value, indent)


  def dump (self, key, value, indent=0) :
      """Dump *WITHOUT REGARD* to top-level container and/or XML header:
      this allows you to compose XML streams if you need to: it just
      dumps XML into the stream."""
      self._XMLDumpKeyValue(key, value, indent)

  def dumpValue (self, value, indent=0) :
      """Dump *WITHOUT REGARD* to top-level container and/or XML header:
      this allows you to compose XML streams if you need to: it just
      dumps XML (value only) into the stream."""
      self._XMLDumpKeyValue(self.NULLKey_, value, indent)

  def mode (self, mode) :
      """If the table is malformed (usually attributes conflicting), throw
      a runtime error if strict.  By default, outputs to cerr"""
      self.mode_ = mode


  # Handle the XML Header, if we want to dump it
  def _XMLHeader (self) :
      if self.options_ & XML_STRICT_HDR :
          self.os_.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")

  # Dump, but allow passage of attributes
  def _XMLDumpKeyValue (self, key, value, indent=0, attrs_ptr=None,
                        was_array_typecode=None):
      t = type(value)
      if t==dict :

          if self.options_ & XML_DUMP_UNNATURAL_ORDER : # may want speed
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=False)
          else : # Natural order (for predictability)
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=True)

      elif t==OrderedDict :

          if self.options_ & XML_DUMP_UNNATURAL_ORDER : # may still want sorted
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=True)
          else : # Natural order of an odict is the order of the odict
              self._XMLDumpTable(key, value, indent, attrs_ptr, sortkeys=False)

      elif t==list or t==tuple :
          self._XMLDumpList(key, value, indent, was_array_typecode)
      elif t in array_types :
          self._XMLDumpPODList(key, value, indent, -1, False)
      else :
          self._XMLDumpPrimitive(key, value, indent, attrs_ptr, was_array_typecode)

  # Dump just the name and make sure it's well-formed tag name
  # (or attribute name): TODO: This may be too restrictive
  def _XMLDumpName (self, tag) :
      if type(tag)!=str: tag = str(tag)

      if len(tag)==0 :
          self._handleProblem("tag cannot be empty (0 length)")

      t = tag
      if t[0].isdigit() :
          if self.options_ & XML_DIGITS_AS_TAGS :
              pass # just output digit
          elif self.options_ & XML_TAGS_ACCEPTS_DIGITS :
              self.os_.write('_')
          else :
              self._handleProblem("tag must start with alphabetic or _, not "+t[0])
      elif not(t[0].isalpha() or t[0]=='_') :
          self._handleProblem("tag must start with alphabetic or _, not "+t[0])

      for ii in xrange(1, len(tag)) :
          if not (t[ii].isalnum() or t[ii]=='_' or t[ii]==':') :
              self._handleProblem("tag must contain alphanumeric or _, not "+t[ii])

      self.os_.write(tag) # All good


  # Dump content: this means handling escape characters
  def _XMLContentFilter (self, content, was_array_typecode=None) :
      result = "" # RVO
      typecode = { float:'d', complex:'D' }
      type_content = type(content)
      if was_array_typecode != None :
          t = pretty.NumericString_(was_array_typecode, content)
      elif type_content in [float, complex] :
          t = pretty.NumericString_(typecode[type_content], content)
      elif type_content in [long, int, bool] :
          t = repr(content)
      else :
          t = content
      for ii in xrange(0,len(t)) :
          c = t[ii]
          if not isprint(c) :
              result += "&#"+hex(ord(c))[1:]+";"
          else :
              if c in self.specialCharToEscapeSeq_ :
                  esc_seq = self.specialCharToEscapeSeq_[t[ii]]
                  result = result + esc_seq
              else :
                  result = result + t[ii]
      return result


  # Dump the start tag, with attention to formatting and options
  def _XMLDumpStartTag (self, tag, attrs, indent,
                        primitive_dump=False, none_dump=False,
                        was_array_typecode=None) :
      if tag is self.NULLKey_ : return

      if self.options_ & XML_DUMP_PRETTY :
          self.os_.write( ' '*indent )
      self.os_.write('<')
      self._XMLDumpName(tag)

      # Attributes  key1="something" key2="somethingelse"
      len_attrs = len(attrs)
      if len_attrs >= 1 : self.os_.write(" ")
      where = 0
      for key, val in sorted(attrs.iteritems()) :
          # String as is
          attr_name = str(key)
          if (len(attr_name)>0 and attr_name[0]==self.prependChar_ and
              ((self.options_ & XML_DUMP_PREPEND_KEYS_AS_TAGS)==0) ) :
              attr_name = attr_name[1:] # strip _

          attr_val = str(val)

          #os_ << attr_name << "=" << attr_val;
          self._XMLDumpName(attr_name)
          self.os_.write("=\"" + self._XMLContentFilter(attr_val, was_array_typecode) + "\"") # TODO: handle '

          where += 1
          if (where!=len_attrs) : # last one, no extra space
              self.os_.write(" ")

      if none_dump: self.os_.write("/")
      self.os_.write(">")
      if ((self.options_ & XML_DUMP_PRETTY)!=0) and (not primitive_dump or none_dump) :
          self.os_.write("\n")



  # Dump the end tag, with attention to output options and formatting
  def _XMLDumpEndTag (self, tag, indent, primitive_dump=False) :
    if tag is self.NULLKey_ :
        return
    if ((self.options_ & XML_DUMP_PRETTY) and not primitive_dump) :
        self.os_.write(' '*indent)
    if type(tag)!= str : tag = str(tag)
    self.os_.write("</"+tag+">") # Note: Already checked that tag is okay!
    if (self.options_ & XML_DUMP_PRETTY) :
        self.os_.write("\n")


  # Does the tag represent a composite object: any container is
  # a composite: Tab, Arr, Tup, OTab
  # primitive data: string, complex, int, float, etc.
  def _IsComposite (self, v) :
      t = type(v)
      return t in [tuple, dict, list, OrderedDict] or t in array_types


  # Find all key-values that could be XML attributes
  def _FindAttributes (self, t) :
      # Collect all things that could be attributes
      attrs = { }   # RVO
      if "__attrs__" in t :  # We want to discover automatically:
          # Attributes all in special key '__attrs__'
          attrs = t["__attrs__"]

      # Attributes may also have to be found
      sorted_keys = sorted(t.keys())
      for key in sorted_keys :
          value = t[key]
      ##for key, value in sorted(t.iteritems()) :
          if type(key) == str :
              if key=="__attrs__": continue  # already processed
              if key=="__content__": continue # special
          else :
              key = str(key)

          # Special character says they *MAY* become attributes
          if (len(key)> 0 and key[0] == self.prependChar_) :
              if key in attrs :
                  self._handleProblem(key+string(" already in ")+str(t))

              key_without_underscore = key[1:]
              if (self.options_ & XML_DUMP_PREPEND_KEYS_AS_TAGS)==0 :
                  attrs[key_without_underscore] = value
                  continue

          # Do All simple values become attributes?
          if (self.options_ & XML_DUMP_SIMPLE_TAGS_AS_ATTRIBUTES) :
              simple = not self._IsComposite(value)
              if key in attrs :
                  self._handleProblem(key+string(" already in ")+str(t))

              if simple :
                  attrs[key] = value
              continue
      # All done
      return attrs


  def _XMLDumpList (self, list_name, l, indent, was_array_typecode=None) :
    # This strange business is to handle lists with no names:
    # either nested within other lists or at the top-level so it will
    # still form well-formed XML: this is pretty rare, but we should
    # still do something useful.
    if list_name is self.NULLKey_ :
        tag = "list__"
    else :
        tag = list_name

    # Empty list
    if len(l)==0 :   # Force list type__ so will unXMLize as an Arr()
        self._XMLDumpPrimitive(tag, None, indent, self.LISTAttrs_)
        return

    # Non-empty list
    for ii in xrange(0, len(l)) :
        key_to_use = self.NULLKey_   # normally NULL RARELY: empty list
        value_ptr = l[ii]

        # This strange bit is because a table is directly inside a
        # list, which means there IS no tag, which normally would be
        # an extra indent with an empty name: this is specifically because
        # of the dict within a list.  A table inside can also mean
        # the __contents__
        table_inside_value = type(value_ptr)==dict or type(value_ptr)==OrderedDict
        indent_inc = self.indentIncrement_
        attrs = { }
        if (table_inside_value) :
            indent_inc = 0
            attrs = self._FindAttributes(value_ptr)
            # Special rare case: contents in special key
            if ("__content__" in value_ptr) :
                value_ptr = value_ptr["__content__"]

            if (type(value_ptr)==dict or type(value_ptr)==OrderedDict) and len(value_ptr)==0 and len(l)==1 :
                # This RARE situation:
                # { 'top': [ {} ] } -> <top type__="list"> <dict__/> </top>
                # Empty table inside a list: Ugh: hard to express in XML
                # without a new tag ... it's basically an anonymous table:
                # Normally, it's easy to detect a table, but an empty
                # dict inside a list is a special case
                indent_inc = self.indentIncrement_
                key_to_use = self.DICTTag_


        elif type(value_ptr) in array_types and \
             self.arrDisp_ != ARRAYDISPOSITION_AS_LIST :
	    #### Array data, well has peculilarities: let it handle it
            self._XMLDumpPODList(tag, value_ptr, indent, ii,
                                 (ii==0 and len(l)==1))
            continue

        primitive_type = not self._IsComposite(value_ptr)
        self._XMLDumpStartTag(tag, attrs, indent, primitive_type, False,
                              was_array_typecode)
        self._XMLDumpKeyValue(key_to_use, value_ptr, indent+indent_inc, None,
                              was_array_typecode)
        self._XMLDumpEndTag(tag, indent, primitive_type)


  def _OC_typecode_(self, a) :
      """Convert the typecode of array a (whether it's NumPy or
      Numeric or NumericWrapper) to the OC types (sSiIlLxXfdFD)"""

      obj_attrs = dir(a)  # hasattr doesn't work in Pyth 2.4
      if "dtype" in obj_attrs : # numpy array
          return NumPyToOCMap[a.dtype]

      elif "typecode" in obj_attrs :
          # This works works with array.array and Numeric.array because
          # the floating point typecodes are essentially the same,
          # and both support typecode and tolist
          was_typecode = a.typecode
          if callable(a.typecode) : was_typecode = a.typecode()
          return NumericToOCMap[was_typecode]
      else :
          raise exception("Unknown array type?")


  # Dump a list of binary data as a tag with one special key:
  # arraytype__ = "<typetag>" which is some typetag (silxfdSILXFD)
  # or, every individual element as a "type__" = <typetag>"
  def _XMLDumpPODList (self, list_name, l,
                       indent, inside_list_number, add_type):
      # tag = str(list_name)
      tag = list_name
      oc_typecode = self._OC_typecode_(l)

      # Check to see if we want to dump this as a LIST or plain POD array
      if self.arrDisp_ == ARRAYDISPOSITION_AS_LIST :

          l = l.tolist()

          # float types: important for -> string to not lose precision
          was_array_typecode = None
          if oc_typecode in ['f','F','d','D'] :
              was_array_typecode = oc_typecode
          else :
              l = [int(x) for x in l]

          self._XMLDumpList(list_name, l, indent, was_array_typecode)
          return

      # The attributes for an Array of POD will the Numeric type tag
      attrs = { }
      bytetag = oc_typecode
      if (self.options_ & XML_DUMP_POD_LIST_AS_XML_LIST) :
          attrs["type__"] = bytetag
      else :
          attrs["arraytype__"] = bytetag

      # There are two ways to dump Array data: either as one tag
      # with a list of numbers, or a tag for for every number.
      # Dumping array data with a tag for every number works better with
      # other tools (spreasheet etc.), but if you annotate EVERY ELEMENT
      # of a long list, the XML becomes much bigger and slow.

      # Dump array with a tag for EVERY element
      primitive_type = True
      temp = None
      inner_tag = tag
      if (self.options_ & XML_DUMP_POD_LIST_AS_XML_LIST) :
          # Rare case when POD array inside list
          if (inside_list_number!=-1) :
              inner_attrs = { }
              if inside_list_number==0 and add_type :
                  inner_attrs["type__"]="list"
              self._XMLDumpStartTag(tag, inner_attrs, indent, False)
              inner_tag = "list"+str(inside_list_number)+"__"
              indent += self.indentIncrement_

          if len(l)==0 :
              # Empty list
              self._XMLDumpStartTag(inner_tag, attrs, indent, primitive_type)
              self._XMLDumpEndTag(inner_tag, indent, primitive_type)
          else :
              # Non-empty list
              for ii in xrange(0, len(l)) :
                  self._XMLDumpStartTag(inner_tag, attrs, indent, primitive_type)
                  temp = pretty.NumericString_(bytetag, l[ii])       #repr(l[ii])  # so prints with full precision of Val for reals, etc.
                  self.os_.write(temp)
                  self._XMLDumpEndTag(inner_tag, indent, primitive_type)

          # Rare case when POD array inside list
          if (inside_list_number!=-1) :
              indent -= self.indentIncrement_
              self._XMLDumpEndTag(tag, indent, False)

      # Dump as a list of numbers with just one tag: the tag, the list of data,
      # then the end tag
      else :
          if (inside_list_number==0 and add_type) : attrs["type__"]="list"
          self._XMLDumpStartTag(tag, attrs, indent, primitive_type)
          for ii in xrange(0, len(l)) :
              temp = pretty.NumericString_(bytetag, l[ii])       #repr(l[ii])  # so prints with full precision of Val for reals, etc.
              self.os_.write(temp)
              if (ii<len(l)-1) : self.os_.write(",")
          # End
          self._XMLDumpEndTag(tag, indent, primitive_type)


  # Dump a table t
  def _XMLDumpTable (self, dict_name, t, indent, attrs_ptr, sortkeys):
      # Rare case: when __content__ there
      if "__content__" in t :
          attrs = self._FindAttributes(t)
          self._XMLDumpKeyValue(dict_name, t["__content__"], indent, attrs)
          return

      # Get attributes, Always dump start tag
      if attrs_ptr == None :
          attrs = self._FindAttributes(t)
      else :
          attrs = attrs_ptr
      self._XMLDumpStartTag(dict_name, attrs, indent)

      # Normally, just iterate over all keys for nested content
      keys = t.keys()
      if sortkeys : keys.sort()
      for key in keys :
          value = t[key]

          # Skip over keys that have already been put in attributes
          k = str(key)
          if key in attrs or k=="__attrs__" or (len(k)>0 and k[0]==self.prependChar_ and k[1:] in attrs) :
              continue # Skip in attrs

          self._XMLDumpKeyValue(key, value, indent+self.indentIncrement_)

      # Always dump end tag
      self._XMLDumpEndTag(dict_name, indent)


  # Dump a primitive type (string, number, real, complex, etc.)
  def _XMLDumpPrimitive (self, key, value, indent, attrs_ptr, was_array_typecode=None) :
      if attrs_ptr is None :
          attrs = self.EMPTYAttrs_
      else :
          attrs = attrs_ptr

      if (self._IsComposite(value)) :
          raise Exception("Trying to dump a composite type as a primitive")

      if value is None :
          self._XMLDumpStartTag(key, attrs, indent, True, True)
          return

      self._XMLDumpStartTag(key, attrs, indent, True)

      # Force all strings into quotes, messy but will always work
      # with XML_LOAD_EVAL_CONTENT on the way back if you have to convert
      if (self.options_ & XML_DUMP_STRINGS_AS_STRINGS) :
          if (type(value) == str) : # make sure pick up quotes
              self.os_.write(self._XMLContentFilter(repr(value), was_array_typecode))
          else :
              self.os_.write(self._XMLContentFilter(value, was_array_typecode)) # Let str pick

      # Most of the time, we can keep all strings as-is (and avoid
      # those nasty '&apos;' quotes in XML around them): those
      # strings that will become something "real values" when Evalled
      # need to have quotes so they will come back as strings
      # when using XML_LOAD_EVAL_CONTENT.  For example: '123' is a string
      # but when evaled, will become a number;  We dump this as
      # "&apos;123&apos;" to preserve the numberness.
      elif (self.options_ & XML_DUMP_STRINGS_BEST_GUESS) :
          if (type(value)==str) :
              s = str(value)    # no quotes on string
              if (len(s)==0 or # always dump empty strings with &apos!
                  ((len(s)>0) and
                   (s[0].isdigit() or s[0]=='(' or s[0]=='-' or s[0]=='+'))) :
                  # If it starts with a number or a sign or '(' (for (1+2j),
                  # probably a number and we WANT to stringize
                  self.os_.write(self._XMLContentFilter(repr(value), was_array_typecode)) # puts quotes on str
              else :
                  self.os_.write(self._XMLContentFilter(value, was_array_typecode)) # no quotes!
          else :
              self.os_.write(self._XMLContentFilter(value, was_array_typecode)) # Let str pick


      # Default, just plop content: still be careful of <empty></empty>:
      # Should that be a {}, None, [], or ""?  With this option, makes it
      # empty string (you don't need this option if you are using
      # XML_DUMP_STRINGS_BEST_GUESS or XML_DUMP_STRINGS_AS_STRINGS
      else :
          if (self.options_ & XML_DUMP_PREFER_EMPTY_STRINGS) :
              if type(value)==str and len(value)==0 :
                  value =  "''"  # Makes <empty></empty> into empty string

          self.os_.write(self._XMLContentFilter(value, was_array_typecode))

      self._XMLDumpEndTag(key, indent, True)


  # Centralize error handling
  def _handleProblem (self, text):
      if (self.mode_==XMLDumper.SILENT_ON_ERROR) : return
      if (self.mode_==XMLDumper.THROW_ON_ERROR) :
          raise Exception, text
      sys.stderr.write(text+"\n")




# ############################# Global Functions

def WriteToXMLStream (v, ofs, top_level_key = 'top',
                      options = XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS, # best options for invertible transforms
                      arr_disp = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                      prepend_char=XML_PREPEND_CHAR) :
    """Write a Python object (usually a dict or list)  as XML to a stream:
    throw a runtime-error if anything bad goes down.
    These default options:
    options=XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS
    are the best options for invertible transforms.
    Array disposition: AS_LIST (0) might be better for dealing with Python,
    but you are much less  likely to lose information by using the default
    AS_NUMERIC_WRAPPER"""
    indent = 2
    xd = XMLDumper(ofs, options, arr_disp, indent, prepend_char,
                   XMLDumper.THROW_ON_ERROR)
    if top_level_key==None:
        xd.XMLDumpValue(v)
    else :
        xd.XMLDumpKeyValue(top_level_key, v)


def WriteToXMLFile (v, filename, top_level_key = 'top',
                    options = XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS, # best options for invertible transforms
                    arr_disp = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                    prepend_char=XML_PREPEND_CHAR) :
    """Write a Python object (usually a dict or list)  as XML to a file:
    throw a runtime-error if anything bad goes down.
    These default options:
    options=XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS
    are the best options for invertible transforms.
    Array disposition: AS_LIST (0) might be better for dealing with Python,
    but you are much less  likely to lose information by using the default
    AS_NUMERIC_WRAPPER"""

    try :
        ofs = open(filename, 'w')
        WriteToXMLStream(v, ofs, top_level_key, options, arr_disp, prepend_char)
    except Exception, e :
        raise Exception, e

import cStringIO
def WriteToXMLString (v, top_level_key = 'top',
                      options = XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS, # best options for invertible transforms
                      arr_disp = ARRAYDISPOSITION_AS_NUMERIC_WRAPPER,
                      prepend_char=XML_PREPEND_CHAR) :
    """Write a Python object (usually a dict or list) as XML to a string:
    throw a runtime-error if anything bad goes down.
    These default options:
    options=XML_DUMP_PRETTY | XML_STRICT_HDR | XML_DUMP_STRINGS_BEST_GUESS
    are the best options for invertible transforms.
    Array disposition: AS_LIST (0) might be better for dealing with Python,
    but you are much less  likely to lose information by using the default
    AS_NUMERIC_WRAPPER"""

    try :
        stream_thing = cStringIO.StringIO()
        WriteToXMLStream(v, stream_thing, top_level_key, options, arr_disp, prepend_char)
        return stream_thing.getvalue()

    except Exception, e :
        raise Exception, e


def ConvertToXML (given_dict) :
    """Convert the given Python dictionary to XML and return the XML
    (a text string).  This uses the most common options that tend to
    make the conversions fully invertible."""
    stream_thing = cStringIO.StringIO()
    WriteToXMLStream(given_dict, stream_thing, 'top')
    return stream_thing.getvalue()


