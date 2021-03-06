r"""
=====================================
:eql: domain for EdgeQL documentation
=====================================


Functions
---------

To declare a function use a ".. eql:function::" directive.  A few
things must be defined:

* Full function signature with a fully qualified name must be specified.

* ":param $name: description:" a short description of the $name parameter.
  $name must match the the name of the parameter in function's signature.
  If a parameter is anonymous, its number should be used instead (e.g. $1).

* ":paramtype $name: type": for every :param: there must be a
  corresponding :paramtype field.  For example: ":paramtype $name: int64"
  declares that the type of the $name parameter is `int64`.  If a parameter
  has more than one valid types list them separated by "or":
  ":paramtype $name: int64 or str".

* :return: and :returntype: are similar to :param: and
  :paramtype: but lack parameter names.  They must be used to document
  the return value of the function.

* A few paragraphs and code samples.  The first paragraph must
  be a single sentence no longer than 79 characters describing the
  function.

Example:

    .. eql:function:: std::array_agg(SET OF any, $a: any) -> array<any>

        :param $1: input set
        :paramtype $1: SET OF any

        :param $a: description of this param
        :paramtype $a: int64 or str

        :return: array made of input set elements
        :returntype: array<any>

        Return the array made from all of the input set elements.

        The ordering of the input set will be preserved if specified.


A function can be referenced from anywhere in the documentation by using
a ":eql:func:" role.  For instance:

* ":eql:func:`array_agg`";
* ":eql:func:`std::array_agg`";
* or, "look at this :eql:func:`fancy function <array_agg>`".


Operators
---------

Use ".. eql:operator::" directive to declare an operator.  Supported fields:

* ":optype NAME: TYPE" -- operand type.

The first argument of the directive must be a string in the following
format: "OPERATOR_ID: OPERATOR SIGNATURE".  For instance, for a "+"
operator it would be "PLUS: A + B":

    .. eql:operator:: PLUS: A + B

        :optype A: int64 or str or bytes
        :optype B: any
        :resulttype: any

        Arithmetic addition.

To reference an operator use the :eql:op: role along with OPERATOR_ID:
":eql:op:`plus`" or ":eql:op:`+ <plus>`".  Operator ID is case-insensitive.


Statements
----------

Use ":eql-statement:" field for sections that describe a statement.

A :eql-haswith: field should be used if the statement supports a WITH block.

Example:

    SELECT
    ------

    :eql-statement:
    :eql-haswith:

    SELECT is used to select stuff.


    .. eql:synopsis::

        [WITH [MODULE name]]
        SELECT expr
        FILTER expr


    .. eql:clause:: FILTER: A FILTER B

        :paramtype A: any
        :paramtype B: SET OF any
        :returntype: any

        FILTER should be used to filter stuff.


    More paragraphs describing intricacies of SELECT go here...

    More paragraphs describing intricacies of SELECT go here...

    More paragraphs describing intricacies of SELECT go here...

Notes:

* To reference a statement use the ":eql:stmt:" role.  For instance:

  - :eql:stmt:`SELECT`
  - :eql:stmt:`my fav statement <SELECT>`
  - :eql:stmt:`select`
  - :eql:stmt:`CREATE FUNCTION`
  - :eql:stmt:`create function <CREATE FUNCTION>`

* Synopsis section, denoted with ".. eql:synopsis::" should follow the
  format used in PostgreSQL documentation:
  https://www.postgresql.org/docs/10/static/sql-select.html

* An "inline-synopsis" role can be used as an inline highlighted code block:

  - :eql:inline-synopsis:`ADD ATTRIBUTE <attribute_name>`.


Types
-----

To declare a type use a ".. eql:type::" directive.  It doesn't have any
fields at the moment, just description.  Example:

    .. eql:type:: std::bytes

        A sequence of bytes.

To reference a type use a ":eql:type:" role, e.g.:

- :eql:type:`bytes`
- :eql:type:`std::bytes`
- :eql:type:`SET OF any`
- :eql:type:`SET OF array\<any\>`
- :eql:type:`array of \<int64\> <array<int64>>`
- :eql:type:`array\<int64\>`

Keywords
--------

To describe a keyword use a ".. eql:keyword::" directive.  Example:

    .. eql:keyword:: WITH

        The ``WITH`` block in EdgeQL is used to define aliases.

If a keyword is compound use dash to separate keywords:


    .. eql:keyword:: SET-OF

To reference a keyword use a ":eql:kw:" role.  For instance:

* :eql:kw:`WITH block <with>`
* :eql:kw:`SET OF <SET-OF>`

"""


import lxml.etree
import re

from edb.lang.edgeql.pygments import EdgeQLLexer

from edb.lang.edgeql.parser import parser as edgeql_parser
from edb.lang.edgeql import ast as ql_ast
from edb.lang.edgeql import codegen as ql_gen
from edb.lang.common import markup  # NoQA

from docutils import nodes as d_nodes
from docutils.parsers import rst as d_rst

from sphinx import addnodes as s_nodes
from sphinx import directives as s_directives
from sphinx import domains as s_domains
from sphinx import roles as s_roles
from sphinx import transforms as s_transforms
from sphinx.directives import code as s_code
from sphinx.util import docfields as s_docfields
from sphinx.util import nodes as s_nodes_utils

from . import shared


class EQLField(s_docfields.Field):

    def __init__(self, name, names=(), label=None, has_arg=False,
                 rolename=None, bodyrolename=None):
        super().__init__(name, names, label, has_arg, rolename, bodyrolename)

    def make_field(self, *args, **kwargs):
        node = super().make_field(*args, **kwargs)
        node['eql-name'] = self.name
        return node

    def make_xref(self, rolename, domain, target,
                  innernode=d_nodes.emphasis, contnode=None, env=None):

        if not rolename:
            return contnode or innernode(target, target)

        title = target
        if domain == 'eql' and rolename == 'type':
            target = EQLTypeXRef.filter_target(target)
            if target in EQLTypedField.ignored_types:
                return d_nodes.Text(title)

        refnode = s_nodes.pending_xref('', refdomain=domain,
                                       refexplicit=title != target,
                                       reftype=rolename, reftarget=target)
        refnode += contnode or innernode(title, title)
        if env:
            env.domains[domain].process_field_xref(refnode)

        refnode['eql-auto-link'] = True
        return refnode

    def make_xrefs(self, rolename, domain, target, innernode=d_nodes.emphasis,
                   contnode=None, env=None):
        delims = r'''(?x)
        (
            \s* [\[\]\(\)<>,] \s* | \s+or\s+ |
            \s*\bSET\s+OF\s+ |
            \s*\bOPTIONAL\s+
        )
        '''

        delims_re = re.compile(delims)
        sub_targets = re.split(delims, target)

        split_contnode = bool(contnode and contnode.astext() == target)

        results = []
        for sub_target in filter(None, sub_targets):
            if split_contnode:
                contnode = d_nodes.Text(sub_target)

            if delims_re.match(sub_target):
                results.append(contnode or innernode(sub_target, sub_target))
            else:
                results.append(self.make_xref(rolename, domain, sub_target,
                                              innernode, contnode, env))

        return results


INDEX_FIELD = EQLField(
    'index',
    label='Index Keywords',
    names=('index',),
    has_arg=False)


class EQLTypedField(EQLField):

    ignored_types = {
        'type'
    }

    def __init__(self, name, names=(), label=None, rolename=None,
                 *, typerolename, has_arg=True):
        super().__init__(name, names, label, has_arg, rolename, None)
        self.typerolename = typerolename

    def make_field(self, types, domain, item, env=None):
        fieldarg, fieldtype = item

        body = d_nodes.paragraph()
        if fieldarg:
            body.extend(self.make_xrefs(self.rolename, domain, fieldarg,
                                        s_nodes.literal_strong, env=env))

            body += d_nodes.Text('--')

        typename = u''.join(n.astext() for n in fieldtype)
        body.extend(
            self.make_xrefs(self.typerolename, domain, typename,
                            s_nodes.literal_emphasis, env=env))

        fieldname = d_nodes.field_name('', self.label)
        fieldbody = d_nodes.field_body('', body)

        node = d_nodes.field('', fieldname, fieldbody)
        node['eql-name'] = self.name
        node['eql-opname'] = fieldarg
        if typename:
            node['eql-optype'] = typename
        return node


class EQLTypedParamField(EQLField):

    is_typed = True

    def __init__(self, name, names=(), label=None, rolename=None,
                 *, has_arg=True, typerolename, typenames):
        super().__init__(name, names, label, has_arg, rolename)
        self.typenames = typenames
        self.typerolename = typerolename

    def make_field(self, types, domain, item, env=None):
        fieldname = d_nodes.field_name('', self.label)

        fieldarg, content = item
        body = d_nodes.paragraph()
        body.extend(self.make_xrefs(self.rolename, domain, fieldarg,
                                    s_nodes.literal_strong, env=env))

        typename = None
        if fieldarg in types:
            body += d_nodes.Text(' (')

            # NOTE: using .pop() here to prevent a single type node to be
            # inserted twice into the doctree, which leads to
            # inconsistencies later when references are resolved
            fieldtype = types.pop(fieldarg)
            if len(fieldtype) == 1 and isinstance(fieldtype[0], d_nodes.Text):
                typename = u''.join(n.astext() for n in fieldtype)
                body.extend(
                    self.make_xrefs(self.typerolename, domain, typename,
                                    s_nodes.literal_emphasis, env=env))
            else:
                body += fieldtype
            body += d_nodes.Text(')')

        body += d_nodes.Text(' -- ')
        body += content

        fieldbody = d_nodes.field_body('', body)

        node = d_nodes.field('', fieldname, fieldbody)
        node['eql-name'] = self.name
        node['eql-paramname'] = fieldarg
        if typename:
            node['eql-paramtype'] = typename
        return node


class BaseEQLDirective(s_directives.ObjectDescription):

    @staticmethod
    def strip_ws(text):
        text = text.strip()
        text = ' '.join(
            line.strip() for line in text.split() if line.strip())
        return text

    def _validate_and_extract_summary(self, node):
        desc_cnt = None
        for child in node.children:
            if isinstance(child, s_nodes.desc_content):
                desc_cnt = child
                break
        if desc_cnt is None or not desc_cnt.children:
            raise shared.DirectiveParseError(
                self, 'the directive must include a description')

        first_node = desc_cnt.children[0]
        if isinstance(first_node, d_nodes.field_list):
            if len(desc_cnt.children) < 2:
                raise shared.DirectiveParseError(
                    self, 'the directive must include a description')

            first_node = desc_cnt.children[1]

        if not isinstance(first_node, d_nodes.paragraph):
            raise shared.DirectiveParseError(
                self,
                'there must be a short text paragraph after directive fields')

        summary = self.strip_ws(first_node.astext())
        if len(summary) > 79:
            raise shared.DirectiveParseError(
                self,
                f'First paragraph is expected to be shorter than 80 '
                f'characters, got {len(summary)}: {summary!r}')

        node['summary'] = summary

    def _find_field_desc(self, field_node: d_nodes.field):
        fieldname = field_node.children[0].astext()

        if ' ' in fieldname:
            fieldtype, fieldarg = fieldname.split(' ', 1)
            fieldarg = fieldarg.strip()
            if not fieldarg:
                fieldarg = None
        else:
            fieldtype = fieldname
            fieldarg = None

        fieldtype = fieldtype.lower().strip()

        for fielddesc in self.doc_field_types:
            if fielddesc.name == fieldtype:
                return fieldtype, fielddesc, fieldarg

        return fieldtype, None, fieldarg

    def _validate_fields(self, node):
        desc_cnt = None
        for child in node.children:
            if isinstance(child, s_nodes.desc_content):
                desc_cnt = child
                break
        if desc_cnt is None or not desc_cnt.children:
            raise shared.DirectiveParseError(
                self, 'the directive must include a description')

        fields = None
        first_node = desc_cnt.children[0]
        if isinstance(first_node, d_nodes.field_list):
            fields = first_node

        for child in desc_cnt.children[1:]:
            if isinstance(child, d_nodes.field_list):
                raise shared.DirectiveParseError(
                    self, f'fields must be specified before all other content')

        if fields:
            for field in fields:
                if 'eql-name' in field:
                    continue

                # Since there is *no* validation or sane error reporting
                # in Sphinx, attempt to do it here.

                fname, fdesc, farg = self._find_field_desc(field)
                msg = f'found unknown field {fname!r}'

                if fdesc is None:
                    msg += (
                        f'\n\nPossible reason: field {fname!r} '
                        f'is not supported by the directive; '
                        f'is there a typo?\n\n'
                    )
                else:
                    if farg and not fdesc.has_arg:
                        msg += (
                            f'\n\nPossible reason: field {fname!r} '
                            f'is specified with an argument {farg!r}, but '
                            f'the directive expects it without one.\n\n'
                        )
                    elif not farg and fdesc.has_arg:
                        msg += (
                            f'\n\nPossible reason: field {fname!r} '
                            f'expects an argument but did not receive it;'
                            f'check your ReST source.\n\n'
                        )

                raise shared.DirectiveParseError(self, msg)

    def run(self):
        indexnode, node = super().run()
        self._validate_fields(node)
        self._validate_and_extract_summary(node)
        return [indexnode, node]

    def add_target_and_index(self, name, sig, signode):
        target = name.replace(' ', '-')

        if target in self.state.document.ids:
            raise shared.DirectiveParseError(
                self, f'duplicate {self.objtype} {name} description')

        signode['names'].append(target)
        signode['ids'].append(target)
        signode['first'] = (not self.names)
        self.state.document.note_explicit_target(signode)

        objects = self.env.domaindata['eql']['objects']

        if target in objects:
            raise shared.DirectiveParseError(
                self, f'duplicate {self.objtype} {name} description')
        objects[target] = (self.env.docname, self.objtype)


class EQLTypeDirective(BaseEQLDirective):

    doc_field_types = [
        INDEX_FIELD,
    ]

    def handle_signature(self, sig, signode):
        if '::' in sig:
            mod, name = sig.strip().split('::')
        else:
            name = sig.strip()
            mod = 'std'

        display = name.replace('-', ' ')
        if mod != 'std':
            display = f'{mod}::{display}'

        signode['eql-module'] = mod
        signode['eql-name'] = name
        signode['eql-fullname'] = fullname = f'{mod}::{name}'

        signode += s_nodes.desc_annotation('type', 'type')
        signode += d_nodes.Text(' ')
        signode += s_nodes.desc_name(display, display)
        return fullname

    def add_target_and_index(self, name, sig, signode):
        return super().add_target_and_index(
            f'type::{name}', sig, signode)


class EQLKeywordDirective(BaseEQLDirective):

    def handle_signature(self, sig, signode):
        signode['eql-name'] = sig
        signode['eql-fullname'] = sig

        display = sig.replace('-', ' ')
        signode += s_nodes.desc_annotation('keyword', 'keyword')
        signode += d_nodes.Text(' ')
        signode += s_nodes.desc_name(display, display)

        return sig

    def add_target_and_index(self, name, sig, signode):
        return super().add_target_and_index(
            f'keyword::{name}', sig, signode)


class EQLSynopsisDirective(s_code.CodeBlock):

    has_content = True
    optional_arguments = 0
    required_arguments = 0
    option_spec = {}

    def run(self):
        self.arguments = ['edgeql-synopsis']
        return super().run()


class EQLMigrationDirective(s_code.CodeBlock):

    has_content = True
    optional_arguments = 0
    required_arguments = 1
    option_spec = {}

    def run(self):
        migration_name = self.arguments[0]
        self.arguments = ['eschema']

        pre = f'CREATE MIGRATION {migration_name} TO eschema $$\n\n'
        suf = f'\n$$;\nCOMMIT MIGRATION {migration_name};'

        pre_node = d_nodes.literal_block(pre, pre)
        pre_node['language'] = 'edgeql'
        suf_node = d_nodes.literal_block(suf, suf)
        suf_node['language'] = 'edgeql'

        cnt = d_nodes.container()
        cnt['eql-migration'] = 'true'
        cnt += [
            pre_node,
            *super().run(),
            suf_node,
        ]
        return [cnt]


class EQLReactElement(d_rst.Directive):

    has_content = False
    optional_arguments = 0
    required_arguments = 1

    def run(self):
        node = d_nodes.container()
        node['react-element'] = self.arguments[0]
        return [node]


class EQLOperatorDirective(BaseEQLDirective):

    doc_field_types = [
        INDEX_FIELD,

        EQLTypedField(
            'operand',
            label='Operand',
            names=('optype',),
            typerolename='type'),

        EQLTypedField(
            'resulttype',
            label='Result',
            has_arg=False,
            names=('resulttype',),
            typerolename='type'),
    ]

    def handle_signature(self, sig, signode):
        try:
            name, sig = sig.split(':', 1)
        except Exception as ex:
            raise shared.DirectiveParseError(
                self,
                f':eql:operator signature must match "NAME: SIGNATURE" '
                f'template',
                cause=ex)

        name = name.strip()
        sig = sig.strip()
        if not name or not sig:
            raise shared.DirectiveParseError(
                self, f'invalid :eql:operator: signature')

        signode['eql-name'] = name
        signode['eql-fullname'] = name
        signode['eql-signature'] = sig

        signode += s_nodes.desc_annotation('operator', 'operator')
        signode += d_nodes.Text(' ')
        signode += s_nodes.desc_name(sig, sig)

        return name

    def add_target_and_index(self, name, sig, signode):
        return super().add_target_and_index(
            f'operator::{name}', sig, signode)


class EQLFunctionDirective(BaseEQLDirective):

    doc_field_types = [
        INDEX_FIELD,
    ]

    def handle_signature(self, sig, signode):
        parser = edgeql_parser.EdgeQLBlockParser()
        try:
            astnode = parser.parse(
                f'CREATE FUNCTION {sig} FROM SQL FUNCTION "xxx";')[0]
        except Exception as ex:
            raise shared.DirectiveParseError(
                self, f'could not parse function signature {sig!r}',
                cause=ex)

        if (not isinstance(astnode, ql_ast.CreateFunction) or
                not isinstance(astnode.name, ql_ast.ObjectRef)):
            raise shared.DirectiveParseError(
                self, f'EdgeQL parser returned unsupported AST')

        modname = astnode.name.module
        funcname = astnode.name.name
        if not modname:
            raise shared.DirectiveParseError(
                self, f'EdgeQL function declaration is missing namespace')

        func_repr = ql_gen.EdgeQLSourceGenerator.to_source(astnode)
        m = re.match(r'''(?xs)
            ^
            CREATE\sFUNCTION\s
            (?P<f>.*?)
            \sFROM\sSQL\sFUNCTION
            .*$
        ''', func_repr)
        if not m or not m.group('f'):
            raise shared.DirectiveParseError(
                self, f'could not recreate function signature from AST')
        func_repr = m.group('f')

        signode['eql-module'] = modname
        signode['eql-name'] = funcname
        signode['eql-fullname'] = fullname = f'{modname}::{funcname}'
        signode['eql-signature'] = func_repr

        signode += s_nodes.desc_annotation('function', 'function')
        signode += d_nodes.Text(' ')
        signode += s_nodes.desc_name(fullname, fullname)

        ret_repr = ql_gen.EdgeQLSourceGenerator.to_source(astnode.returning)
        if astnode.returning_typemod is ql_ast.ft.TypeModifier.SET_OF:
            ret_repr = f'SET OF {ret_repr}'
        elif astnode.returning_typemod is ql_ast.ft.TypeModifier.OPTIONAL:
            ret_repr = f'OPTIONAL {ret_repr}'
        signode += s_nodes.desc_returns(ret_repr, ret_repr)

        return fullname

    def add_target_and_index(self, name, sig, signode):
        return super().add_target_and_index(
            f'function::{name}', sig, signode)


class EQLConstraintDirective(BaseEQLDirective):

    doc_field_types = [
        INDEX_FIELD,
    ]

    def handle_signature(self, sig, signode):
        parser = edgeql_parser.EdgeQLBlockParser()
        try:
            astnode = parser.parse(
                f'CREATE ABSTRACT CONSTRAINT {sig};')[0]
        except Exception as ex:
            raise shared.DirectiveParseError(
                self, f'could not parse constraint signature {sig!r}',
                cause=ex)

        if (not isinstance(astnode, ql_ast.CreateConstraint) or
                not isinstance(astnode.name, ql_ast.ObjectRef)):
            raise shared.DirectiveParseError(
                self, f'EdgeQL parser returned unsupported AST')

        modname = astnode.name.module
        constr_name = astnode.name.name
        if not modname:
            raise shared.DirectiveParseError(
                self, f'Missing module in EdgeQL constraint declaration')

        constr_repr = ql_gen.EdgeQLSourceGenerator.to_source(astnode)

        m = re.match(r'''(?xs)
            ^
            CREATE\sABSTRACT\sCONSTRAINT\s
            (?P<f>.*?)(?:\s*ON(?P<subj>.*))?
            $
        ''', constr_repr)
        if not m or not m.group('f'):
            raise shared.DirectiveParseError(
                self, f'could not recreate constraint signature from AST')
        constr_repr = m.group('f')

        signode['eql-module'] = modname
        signode['eql-name'] = constr_name
        signode['eql-fullname'] = fullname = f'{modname}::{constr_name}'
        signode['eql-signature'] = constr_repr
        subject = m.group('subj')
        if subject:
            subject = subject.strip()[1:-1]
            signode['eql-subjexpr'] = subject
            signode['eql-signature'] += f' ON ({subject})'

        signode += s_nodes.desc_annotation('constraint', 'constraint')
        signode += d_nodes.Text(' ')
        signode += s_nodes.desc_name(fullname, fullname)

        return fullname

    def add_target_and_index(self, name, sig, signode):
        return super().add_target_and_index(
            f'constraint::{name}', sig, signode)


class EQLTypeXRef(s_roles.XRefRole):

    @staticmethod
    def filter_target(target):
        new_target = re.sub(r'''(?xi)
            ^ \s*\bSET\s+OF\s+ | \s*\bOPTIONAL\s+
        ''', '', target)

        if '<' in new_target:
            new_target, _ = new_target.split('<', 1)

        return new_target

    def process_link(self, env, refnode, has_explicit_title, title, target):
        new_target = self.filter_target(target)
        if not has_explicit_title:
            title = target.replace('-', ' ')
        return super().process_link(
            env, refnode, has_explicit_title, title, new_target)


class EQLFunctionXRef(s_roles.XRefRole):

    def process_link(self, env, refnode, has_explicit_title, title, target):
        if not has_explicit_title:
            title += '()'
        return super().process_link(
            env, refnode, has_explicit_title, title, target)


class EQLConstraintXRef(s_roles.XRefRole):
    pass


class EdgeQLDomain(s_domains.Domain):

    name = "eql"
    label = "EdgeQL"

    object_types = {
        'function': s_domains.ObjType('function', 'func'),
        'constraint': s_domains.ObjType('constraint', 'constraint'),
        'type': s_domains.ObjType('type', 'type'),
        'keyword': s_domains.ObjType('keyword', 'kw'),
        'operator': s_domains.ObjType('operator', 'op'),
        'statement': s_domains.ObjType('statement', 'stmt'),
    }

    _role_to_object_type = {
        role: tn
        for tn, td in object_types.items() for role in td.roles
    }

    directives = {
        'function': EQLFunctionDirective,
        'constraint': EQLConstraintDirective,
        'type': EQLTypeDirective,
        'keyword': EQLKeywordDirective,
        'operator': EQLOperatorDirective,
        'synopsis': EQLSynopsisDirective,
        'migration': EQLMigrationDirective,
        'react-element': EQLReactElement,
    }

    roles = {
        'func': EQLFunctionXRef(),
        'constraint': EQLConstraintXRef(),
        'type': EQLTypeXRef(),
        'kw': s_roles.XRefRole(),
        'op': s_roles.XRefRole(),
        'stmt': s_roles.XRefRole(),
    }

    initial_data = {
        'objects': {}  # fullname -> docname, objtype
    }

    def resolve_xref(self, env, fromdocname, builder,
                     type, target, node, contnode):

        objects = self.data['objects']
        expected_type = self._role_to_object_type[type]

        target = target.replace(' ', '-')
        if expected_type == 'keyword':
            targets = [f'keyword::{target}']
        elif expected_type == 'operator':
            targets = [f'operator::{target}']
        elif expected_type == 'statement':
            targets = [f'statement::{target}']
        elif expected_type in {'type', 'function', 'constraint'}:
            targets = [f'{expected_type}::{target}']
            if '::' not in target:
                targets.append(f'{expected_type}::std::{target}')
        else:
            targets = [target]

        docname = None
        obj_type = None
        for target in targets:
            try:
                docname, obj_type = objects[target]
            except KeyError:
                continue

        if docname is None:
            if not node.get('eql-auto-link'):
                raise shared.DomainError(
                    f'cannot resolve :eql:{type}: targeting {target!r}')
            else:
                return

        if obj_type != expected_type:
            raise shared.DomainError(
                f'cannot resolve :eql:{type}: targeting {target!r}: '
                f'the type of referred object {expected_type!r} '
                f'does not match the reftype')

        node = s_nodes_utils.make_refnode(
            builder, fromdocname, docname, target, contnode, None)
        node['eql-type'] = obj_type
        return node

    def clear_doc(self, docname):
        for fullname, (fn, _l) in list(self.data['objects'].items()):
            if fn == docname:
                del self.data['objects'][fullname]

    def merge_domaindata(self, docnames, otherdata):
        for fullname, (fn, objtype) in otherdata['objects'].items():
            if fn in docnames:
                self.data['objects'][fullname] = (fn, objtype)

    def get_objects(self):
        for refname, (docname, type) in self.data['objects'].items():
            yield (refname, refname, type, docname, refname, 1)

    def get_full_qualified_name(self, node):
        fn = node.get('eql-fullname')
        if not fn:
            raise shared.DirectiveParseError(
                self, 'no eql-fullname attribute')
        return fn


class StatementTransform(s_transforms.SphinxTransform):

    default_priority = 5  # before ReferencesResolver

    def apply(self):
        for section in self.document.traverse(d_nodes.section):
            x = lxml.etree.XML(section.asdom().toxml())

            fields = set(x.xpath('field_list/field/field_name/text()'))
            if 'eql-statement' not in fields:
                continue

            title = x.xpath('title/text()')[0]
            if not re.match(r'^([A-Z]+\s?)+$', title):
                raise shared.EdgeSphinxExtensionError(
                    f'section {title!r} is marked with an :eql-statement: '
                    f'field, but does not satisfy pattern for valid titles: '
                    f'UPPERCASE WORDS separated by single space characters')

            nested_statements = x.xpath(
                '//field_list/field/field_name[text()="eql-statement"]')
            if len(nested_statements) > 1:
                raise shared.EdgeSphinxExtensionError(
                    f'section {title!r} has a nested section with '
                    f'a :eql-statement: field set')

            first_para = x.xpath('paragraph[1]/descendant-or-self::*/text()')
            if not len(first_para):
                raise shared.EdgeSphinxExtensionError(
                    f'section {title!r} is marked with an :eql-statement: '
                    f'and is required to have at least one paragraph')
            first_para = ''.join(first_para)
            summary = BaseEQLDirective.strip_ws(first_para)
            if len(summary) > 79:
                raise shared.EdgeSphinxExtensionError(
                    f'section {title!r} is marked with an :eql-statement: '
                    f'and its first paragraph is longer than 79 characters')

            section['eql-statement'] = 'true'
            section['eql-haswith'] = ('true' if 'eql-haswith' in fields
                                      else 'false')
            section['summary'] = summary

            objects = self.env.domaindata['eql']['objects']
            target = 'statement::' + title.replace(' ', '-')

            if target in objects:
                raise shared.EdgeSphinxExtensionError(
                    f'duplicate {title!r} statement')

            objects[target] = (self.env.docname, 'statement')

            section['ids'].append(target)


def setup_domain(app):
    app.add_lexer("edgeql", EdgeQLLexer())
    app.add_lexer("edgeql-repl", EdgeQLLexer())
    app.add_lexer("edgeql-synopsis", EdgeQLLexer())

    app.add_role(
        'eql:synopsis',
        shared.InlineCodeRole('edgeql-synopsis'))

    app.add_domain(EdgeQLDomain)

    app.add_transform(StatementTransform)
