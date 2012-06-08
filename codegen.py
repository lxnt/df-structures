#!/usr/bin/python3.2
# -*- encoding: utf-8 -*-
"""
https://github.com/lxnt/df-structures
Copyright (c) 2012-2012 Alexander Sabourenkov (screwdriver@lxnt.info)
Copyright (c) 2009-2011 Petr Mrázek (peterix@gmail.com)

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any
damages arising from the use of this software.

Permission is granted to anyone to use this software for any
purpose, including commercial applications, and to alter it and
redistribute it freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must
not claim that you wrote the original software. If you use this
software in a product, an acknowledgment in the product documentation
would be appreciated but is not required.

2. Altered source versions must be plainly marked as such, and
must not be misrepresented as being the original software.

3. This notice may not be removed or altered from any source
distribution.

Based on work of Alexander Gavrilov (https://github.com/angavrilov/df-structures)
"""

import os, os.path, glob, sys, argparse, io
from lxml import etree
from lxml.etree import XPath as etx, XMLSyntaxError, Element
from textwrap import dedent
from pprint import pformat

import static
static_crap = []
class Error(Exception): pass

def unknown(prefix):
    i = 0
    while True:
        yield "{}{:03x}".format(prefix, i)
        i += 1

unk = unknown('gunk_')
tag_tab = {     'uint16_t':         'uint16_t',
                'uint8_t':          'uint8_t',
                'uint32_t':         'uint32_t',
                'int32_t':          'int32_t',
                'int8_t':           'int8_t',
                'int16_t':          'int16_t',
                'bool':             'bool',
                's-float':          'float',
                'stl-string':       'std::string',
                'stl-bit-vector':   'std::vector<bool>',
                'df-flagarray':     'df::flagarray',
                'df-array':         'df::array' }

df_type_tab = {}  

def dispatch(e, def_type_name = '~none~'):
    global tag_tab, df_type_tab, implidef_tab
    type_decl = []
    deps = set()
    if len(e) == 0:
        type_t = e.get('type-name')
        if type_t is None:
            type_t = def_type_name
        elif type_t == 'pointer':
            type_t = 'void *'
        elif type_t in tag_tab:
            type_t = tag_tab[type_t]
        elif type_t in df_type_tab:
            type_t = df_type_tab[type_t]
        elif not type_t.endswith('_t'):
            #print("dispatch(): using kludge on {}".format(type_t))
            type_t = 'df::' + type_t
    elif len(e) == 1:
        if e[0].tag == 'pointer':
            type_t, type_decl, deps = pointer_t(e[0])
        elif e[0].tag in tag_tab:
            type_t = tag_tab[e[0].tag]
        elif e[0].tag in implidef_tab:
            type_t, type_decl, deps = implidef_tab[e[0].tag](e[0])
            type_t = df_type_tab.get(type_t, type_t)
        elif e[0].tag == 'static-array':
            type_t, type_decl, deps = staticarray_t(e[0])
    else: # not encountered yet
        type_t, type_decl, deps = struct_t(e)
    try:
        return type_t, type_decl, deps
    except NameError:
        mess = pformat(e.tag, e.attrib)
        if len(e):
            mess += pformat(e[0].tag, e[0].attrib)
        raise Error(mess)

def stdvector_t(e):
    type_t, type_decl, dependencies = dispatch(e, 'void *')
    return 'std::vector<{}>'.format(type_t), type_decl, dependencies
    
def stddeque_t(e):
    type_t, type_decl, dependencies = dispatch(e, 'void *')
    return 'std::deque<{}>'.format(type_t), type_decl, dependencies

def pointer_t(e):
    global unk
    type_t, type_decl, dependencies = dispatch(e, 'void')
    if '{name}' in type_t: # pointer to a static-array, needs typedef.
        td_t = next(unk) + '_t'
        type_decl.append('typedef {};'.format(type_t.format(name=td_t)))
        type_t = td_t
    return type_t + '*', type_decl, dependencies

def staticarray_t(e):
    cseq = '[{}]'.format(e.get('count'))   
    while len(e) == 1 and e[0].tag == 'static-array':
        cseq += '[{}]'.format(e[0].get('count'))
        e = e[0]

    type_t, type_decl, dependencies = dispatch(e)
    type_t += ' {name}' + cseq
    return type_t, type_decl, dependencies 

def bitfield_t(e):
    global unk, df_type_tab
    if e.tag == 'bitfield' and 'type-name' in e.attrib:
        return e.get('type-name'), [], set()
    
    rv = []
    struct_indent = " " * 4
    field_indent  = " " * 8
    type_t = e.get('type-name')
    if type_t is None: # implicit/inline def
        type_t = e.get('name', next(unk)) + '_t'    
        implicit_def = True
    else:
        implicit_def = False
    base_type = e.get('base-type', 'uint32_t')
    rv.append("union {type_t} {{".format(type_t = type_t))
    rv.append("{indent}{base_type} whole;".format(
                base_type = base_type,
                indent = struct_indent ))
    rv.append("{indent}struct {{".format(indent = struct_indent))
    for ei in e.iter(tag = 'flag-bit'):
        rv.append("{indent}{tname} {name}: {count};".format(
            count = ei.attrib.get('count', 1),
            tname = base_type,
            indent = field_indent,
            name = ei.get('name', next(unk)) ))
    rv.append("{indent}}} bits;".format(indent = struct_indent))
    rv.append("};")
    if not implicit_def:
        df_type_tab[type_t] = 'df::' + type_t    
    return type_t, rv, set()

enum_tab = {} # defined enums and their basetypes
def enum_t(e):
    global unk, df_type_tab, enum_tab
    funattrs = "__attribute__ ((const, unused))"
    if e.tag == 'enum' and 'type-name' in e.attrib:
        fqtn = 'df::enums::{0}::{0}'.format(e.get('type-name'))
        if e.get('base-type') and e.get('base-type') != enum_tab[e.get('type-name')]:
            return 'df::enums::enum_field<{},{}>'.format(fqtn, e.get('base-type')), [], set()
        else:
            return fqtn, [], set()
    rv = []
    kdef = []
    item_indent = " " * 4
    type_t = e.get('type-name')
    if type_t is None: # implicit/inline def (skip namespace part)
        type_t = e.get('name', next(unk)) + '_t'
        implicit_def = True
    else:
        implicit_def = False
    base_type = e.get('base-type', 'int32_t')
    enum_tab[type_t] = base_type
    kdef.append("static const char * const key({0} k) {1};".format(type_t, funattrs))
    kdef.append("static const char * const key({0} k) {{".format(type_t))
    kdef.append(item_indent + "switch(k) {")
    _min = 1<<31
    _max = -1<<31
    _count = 0
    value = -1
    rv.append("enum {type_t} : {base_type} {{".format(type_t = type_t, base_type = base_type ))
    for ei in e.iter(tag = 'enum-item'):
        _count += 1
        if 'value' in ei.attrib:
            value = int(ei.get('value'))
            value_s = ' = {}'.format(value)
        else:
            value += 1
            value_s = ''
        if value < _min: _min = value
        if value > _max: _max = value
        name = ei.get('name', next(unk))
        rv.append("{indent}{ei_name}{ei_value},".format(
            ei_name = name,
            ei_value = value_s,
            indent = item_indent ))
        kdef.append(item_indent*2 + 'case {0}: return "{0}";'.format(name))
    rv.append("};")
    if not implicit_def:
        rv.insert(0, "namespace enums {{ namespace {} {{".format(type_t))
        rv.append("static const int32_t _min = {};".format(_min))
        rv.append("static const int32_t _max = {};".format(_max))
        rv.append("static const int32_t _count = {};".format(_count))
        kdef.append(item_indent*2 + "default: return NULL;")
        kdef.append(item_indent + "}")
        kdef.append("}")
        rv.extend(kdef)
        rv.append("}} }} using enums::{name}::{name};\n".format(name = type_t))
        df_type_tab[type_t] = "df::{name}".format(name = type_t)
    return type_t, rv, set()

def struct_t(e):
    global unk, tag_tab, df_type_tab, implidef_tab, static_crap
    
    if e.tag == 'compound' and 'type-name' in e.attrib:
        type_t = e.get('type-name') 
        return df_type_tab.get(type_t, type_t), [], set([type_t])
    
    def padding(e):
        return "uint8_t {name}[{size}]".format(size = e.get('size'), name = e.get('name', next(unk)))
    def staticstring(e):
        return "char {name}[{size}]".format(size = e.get('size'), name = e.get('name', next(unk)))
    def vmethod(e, classtype_t):
        """ special case, returns strings, do not confuse with other functions """
        if bool(e.get('is-destructor')):
            return "virtual ~{}();".format(classtype_t), []
        params = []
        deps = set()
        rettype_t = e.get('ret-type', 'void')
        for vmp in e:
            if vmp.tag == 'pointer': # no implicit compounds here (in vmeth params). and skip types ftb
                try:
                    name = vmp[0].get('comment', next(unk))
                except IndexError:
                    name = vmp.get('comment', next(unk))
                params.append("void *" + str(name))
            elif vmp.tag in tag_tab:
                params.append(tag_tab[vmp.tag].format(vmp.tag) + " " + vmp.get('name', next(unk)))
            elif vmp.tag == 'ret-type':
                assert len(vmp) == 1
                if vmp[0].tag in tag_tab:
                    rettype_t = tag_tab[vmp[0].tag]
                elif vmp[0].tag in implidef_tab:
                    rettype_t, unused_def, deps = implidef_tab[vmp[0].tag](vmp[0])
                    if rettype_t in df_type_tab:
                        deps.add(rettype_t)
                        rettype_t = df_type_tab[rettype_t]
                    if len(unused_def) != 0:
                        raise Error(pformat((vmp.tag, vmp.attrib, vmp[0].tag, vmp[0].attrib, unused)))
                else:
                    raise Error(pformat((vmp.tag, vmp.attrib, vmp[0].tag, vmp[0].attrib)))
            elif vmp.tag == 'enum':
                params.append(vmp.get('base-type'))
            else:
                raise Error(pformat((e.tag, e.attrib, vmp.tag, vmp.attrib)))
                
        return "virtual {rettype_t} {name}({params});".format(
            rettype_t = rettype_t,
            name = e.get('name', next(unk)),
            params = ", ".join(params)), deps

    indent = " " * 4
    rv = []
    dependencies = set() 
    pt = e.get('inherits-from', None)
    type_t = e.get('type-name')
    if type_t is None: # implicit def
        type_t = e.get('name', next(unk)) + '_t'
    
    if pt is not None:
        dependencies.add(pt)
    
    rv.append("struct {type_t}{parent_t} {{".format(
        type_t = type_t,
        parent_t = "" if pt is None else " : {}".format(pt) ) )
    
    if len(e) == 0: # empty top-level def
        rv[0] += "};"
        return type_t, rv, dependencies
    
    for field in e:
        f_type_t = field.get('type-name')
        f_name = " " + field.get('name', next(unk))
        if field.tag in tag_tab:
            rv.append(indent + tag_tab[field.tag].format(f_type_t) + f_name + ';')
        elif field.tag == 'vmethod':
            vm, deps = vmethod(field, type_t)
            rv.append(indent + vm)
            dependencies.update(deps)
        elif field.tag == 'padding':
            rv.append(indent + padding(field) + ';')
        elif field.tag == 'static-string':
            rv.append(indent + staticstring(field) + ';')
        elif field.tag == 'pointer':
            t, decls, deps = pointer_t(field)
            rv.extend(map(lambda l: indent + l, decls))
            rv.append(indent + t + f_name + ';')
            dependencies.update(deps)
        elif field.tag == 'stl-vector':
            t, decls, deps = stdvector_t(field)
            rv.extend(map(lambda l: indent + l, decls))
            rv.append(indent + t + f_name + ';')
            dependencies.update(deps)
        elif field.tag == 'stl-deque':
            t, decls, deps = stddeque_t(field)
            rv.extend(map(lambda l: indent + l, decls))
            rv.append(indent + t + f_name + ';')
            dependencies.update(deps)
        elif field.tag == 'static-array':
            t, decls, deps = staticarray_t(field)
            rv.extend(map(lambda l: indent + l, decls))
            rv.append(indent + t.format(name = f_name) + ';')
            dependencies.update(deps)
        elif field.tag in implidef_tab:
            f_type_t, lines, deps = implidef_tab[field.tag](field)
            rv.extend(map(lambda l: indent + l, lines))
            if f_type_t in df_type_tab:
                rv.append(indent + df_type_tab[f_type_t] + f_name + ';')
            else:
                if f_type_t.startswith('df::') or f_type_t.endswith('_t'):
                    rv.append(indent + f_type_t + f_name + ';')
                else:
                    rv.append(indent + 'df::' + f_type_t + f_name + ';')
            dependencies.update(deps)
        else:
            raise Error(pformat(field.tag, f_type_t))
    rv.extend(static.methods.get(type_t, []))
    iv = e.get('instance-vector')
    if iv is not None:
        rv.append(indent + "static std::vector<{}*> &get_vector(); ".format(type_t))
        iv = iv.replace('$global.world.', 'df::global::world->')
        iv = iv.replace('$global.ui.', 'df::global::ui->')
        iv = iv.replace("world_data.", "world_data->")
        static_crap.append("std::vector<df::{0}*> &df::{0}::get_vector() {{ return {1}; }}".format(
            type_t, iv  ))
    try:
        dependencies.update(static.dependencies[type_t])
    except KeyError:
        pass
    rv.append("};")
    return type_t, rv, dependencies

implidef_tab = { # whatever tags emit typedefs when w/o type-name attr.
    'static-array': staticarray_t,
    'pointer': pointer_t,
    'compound': struct_t,
    'df-linked-list': struct_t,
    'enum': enum_t,
    'bitfield': bitfield_t,
    'stl-vector': stdvector_t,
    'stl-deque': stddeque_t,
    }

class cxxheader(object):
    def __init__(self, fname, includes, namespaces):
        self.f = open(fname, "w")
        self.fname = fname
        nsopens = ' '.join(map(lambda ns: 'namespace {} {{'.format(ns), namespaces)) + "\n"
        nscloses = '} ' * len(namespaces) + "\n"
        defname = "OOK_OOK_{}".format(os.path.basename(fname).upper().replace('.', '_'))
        self.hdr = "#ifndef {0}\n#define {0}\n".format(defname) + includes + nsopens
        self.ftr = nscloses + "#endif /* {} */\n".format(defname)

    def __enter__(self):
        self.f.write(self.hdr)
        return self
    
    def __exit__(self, et, ev, tb):
        if et is None:
            self.f.write(self.ftr)
        else: # unlink incomplete file
            if False:
                os.unlink(self.fname)
            # or at least don't write the footer.
            
        self.f.close()
        return False

    def write(self, *args, **kwargs):
        self.f.write(*args, **kwargs)

class xD(object):
    hdr_structs_h = dedent("""
        #include <stdint.h>
        #include <string>
        #include <vector>
        #include <deque>
        #include "enums.h"
        #include "bitfields.h"
        """)
    hdr_bitfields_h = dedent("""
        #include <stdint.h>
        """)
    hdr_enums_h = dedent("""
        #include <stdint.h>
        namespace df { namespace enums {
        /* dfhack::library/include/DataDefs.h */
        template<class EnumType, class IntType = int32_t>
        struct enum_field {
            IntType value;

            enum_field() {}
            enum_field(EnumType ev) : value(IntType(ev)) {}
            template<class T>
            enum_field(enum_field<EnumType,T> ev) : value(IntType(ev.value)) {}

            operator EnumType () { return EnumType(value); }
            enum_field<EnumType,IntType> &operator=(EnumType ev) {
                value = IntType(ev); return *this;
            }
        };

        template<class EnumType, class IntType1, class IntType2>
        inline bool operator== (enum_field<EnumType,IntType1> a, enum_field<EnumType,IntType2> b)
        {
            return EnumType(a) == EnumType(b);
        }

        template<class EnumType, class IntType1, class IntType2>
        inline bool operator!= (enum_field<EnumType,IntType1> a, enum_field<EnumType,IntType2> b)
        {
            return EnumType(a) != EnumType(b);
        }
            
        } }
        """)
        
    hdr_globals_h = hdr_structs_h + '#include "structs.h"\n'
    indent = " " * 4
    df_helper_defs = dedent("""
        struct array {
            void *data;
            unsigned short size;
        }; 
        struct flagarray {
            uint8_t * bits;
            uint32_t size;
        };    
        """).splitlines(True)
    
    def __init__(self, version='v0.34.11 linux', prefix=''):
        self.woot = etree.Element('data-definition')
        self._p = etree.XMLParser(remove_blank_text = True)
        self._version = version
        self.emitted = set()

    def eat(self, fname):
        t = etree.parse(fname, self._p).getroot()
        etree.strip_elements(t, "comment", "code-helper")
        etree.strip_tags(t, "virtual-methods")
        for e in t.iter():
            if isinstance(e, etree._Comment):
                e.getparent().remove(e)
            else:
                e.tail = e.text = None
        self.woot.extend( etx('*')(t) )
            
    def vomit(self, fname):
        with open(fname, 'wb') as f: 
            f.write(etree.tostring(self.woot, pretty_print = True))

    def emit(self, prefix, verify = False):
        self._enum_types(os.path.join(prefix, "enums.h"))
        self._bitfield_types(os.path.join(prefix, "bitfields.h"))
        self._compound_types(os.path.join(prefix, "structs.h"))
        self._globals(os.path.join(prefix, "globals.h"),
                os.path.join(prefix, "globals.cc"))
        if verify:
            from subprocess import call
            if not call("g++ -std=c++0x -c -o /dev/null {0}/globals.cc -I{0}".format(prefix).split()):
                print("compiled ok.")

    def _enum_types(self, fname):
        with cxxheader(fname, self.hdr_enums_h, ['df']) as f:
            for e in etx('enum-type')(self.woot):
                type_t, lines, unused = enum_t(e)
                self.emitted.add(type_t)
                for l in lines:
                    f.write(self.indent + l + "\n");
        
    def _bitfield_types(self, fname):
        with cxxheader(fname, self.hdr_bitfields_h, ['df']) as f:
            for e in etx('bitfield-type')(self.woot):
                type_t, lines, unused = bitfield_t(e)
                self.emitted.add(type_t)
                for l in lines:
                    f.write(self.indent + l + "\n");
        
    def _compound_types(self, fname):
        global df_type_tab
        els = etx("struct-type")(self.woot) + etx("class-type")(self.woot)       
        types = {}
        for e in els:
            type_t, lines, deps = struct_t(e)
            df_type_tab[e.get('type-name')] = 'df::' + type_t
            types[e.get('type-name')] = (lines, deps)
        all = set(types.keys())
        
        with cxxheader(fname, self.hdr_structs_h, ['df']) as f, io.StringIO() as stuff:
            f.write(self.indent.join(self.df_helper_defs))
            for tname in all: # emit forward decls for all 
                f.write(self.indent + 'struct ' + tname + ";\n")
            while len(all) > 0:
                for tname in all:
                    #print("{} :{}".format(tname, types[tname][1]))
                    if len(types[tname][1]) == 0:
                        for l in types[tname][0]:
                            stuff.write(self.indent + l + "\n")
                        self.emitted.add(tname)
                _a = len(all)
                _e = len(self.emitted)
                all.difference_update(self.emitted)
                if _a == len(all):
                    print("error: type dependency loop.")
                    for tn in all:
                        deps = types[tn][1]
                        aid = all.intersection(deps)
                        if len(aid) == 0: # deps of type can't be fullfilled by any in all
                            print("{}: {}".format(tn, deps))
                            for d in deps:
                                print (d, types[d][1])
                    raise Error
                for tname in all:
                    types[tname][1].difference_update(self.emitted)
            f.write(stuff.getvalue())

    def _globals(self, hfname, ccfname):
        global df_type_tab, static_crap
        def getaddr(name):
            xpa = "symbol-table[@name='{version}']/global-address[@name='{global_name}']".format(
                version = self._version, global_name = name)
            el =  etx(xpa)(self.woot)
            try:
                return el[0].get('value')
            except IndexError:
                return None

        gcode = open(ccfname, "w")
        gcode.write(self.hdr_globals_h)
        gcode.write('#include "globals.h"\n\n')

        with cxxheader(hfname, self.hdr_globals_h, ['df', 'global']) as ghead:
            for e in etx("global-object")(self.woot):
                name = e.get('name')
                type_t, decl, deps = pointer_t(e)
                if decl:
                    for l in decl:
                        ghead.write(self.indent + l + "\n")
                    df_type_tab[type_t] = 'df::global::' + type_t
                ghead.write("{indent}extern {type_t} const {name};\n".format(
                    type_t = type_t, name = name, indent = self.indent))
                address = getaddr(name)
                name = 'df::global::' + name
                if address is None:
                    print("warning: no address for ``{} {}'', assuming NULL.".format(type_t, name))
                    address = 'NULL'
                gcode.write("{type_t} const {name} = ({type_t}) {value};\n".format(
                    type_t = df_type_tab.get(type_t, type_t),
                    name = name, 
                    value = address))
        for l in static_crap:
            gcode.write(l + "\n")
        gcode.close()

def main():
    ap = argparse.ArgumentParser(description = 'a simpler code generator')
    ap.add_argument('-src', metavar='srcdir', default='.', help='source (xml) dir')
    ap.add_argument('-dst', metavar='dstdir', help='destination prefix', required = True)
    ap.add_argument('-tdump', metavar='all.xml', help='dump working xml tree here')
    ap.add_argument('-verify', action='store_true', help='attempt compilation')
    pa = ap.parse_args()
    
    if pa.dst or pa.tdump:
        xd = xD()
        for fn in glob.glob(os.path.join(pa.src, '*.xml')):
            xd.eat(fn)
        if pa.tdump:
            xd.vomit(pa.tdump)
        xd.emit(pa.dst, pa.verify)

if __name__ == '__main__': main()

