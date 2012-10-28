#
# invRegex.py
#
# Copyright 2008, Paul McGuire
#
# pyparsing script to expand a regular expression into all possible matching strings
# Supports:
# - {n} and {m,n} repetition, but not unbounded + or * repetition
# - ? optional elements
# - [] character ranges
# - () grouping
# - | alternation
#

__all__ = ["count", "invregexp"]

from pyparsing import Combine
from pyparsing import Literal
from pyparsing import ParseFatalException
from pyparsing import ParseResults
from pyparsing import ParserElement
from pyparsing import SkipTo
from pyparsing import Suppress
from pyparsing import Word
from pyparsing import nums
from pyparsing import oneOf
from pyparsing import opAssoc
from pyparsing import operatorPrecedence
from pyparsing import printables
from pyparsing import srange


class CharacterRangeEmitter(object):
    def __init__(self, chars):
        # remove duplicate chars in character range, but preserve original order
        seen = set()
        self.charset = "".join(seen.add(c) or c for c in chars if c not in seen)

    def __str__(self):
        return '[' + self.charset + ']'

    def __repr__(self):
        return '[' + self.charset + ']'

    def make_generator(self):
        def gen_chars():
            for s in self.charset:
                yield s
        return gen_chars


class OptionalEmitter(object):
    def __init__(self, expr):
        self.expr = expr

    def make_generator(self):
        def optional_gen():
            yield ""
            for s in self.expr.make_generator()():
                yield s
        return optional_gen


class DotEmitter(object):
    def make_generator(self):
        def dot_gen():
            for c in printables:
                yield c
        return dot_gen


class GroupEmitter(object):
    def __init__(self, exprs):
        self.exprs = ParseResults(exprs)

    def make_generator(self):
        def group_gen():
            def recurse_list(elist):
                if len(elist) == 1:
                    for s in elist[0].make_generator()():
                        yield s
                else:
                    for s in elist[0].make_generator()():
                        for s2 in recurse_list(elist[1:]):
                            yield s + s2
            if self.exprs:
                for s in recurse_list(self.exprs):
                    yield s

        return group_gen


class AlternativeEmitter(object):
    def __init__(self, exprs):
        self.exprs = exprs

    def make_generator(self):
        def alt_gen():
            for e in self.exprs:
                for s in e.make_generator()():
                    yield s

        return alt_gen


class LiteralEmitter(object):
    def __init__(self, lit):
        self.lit = lit

    def __str__(self):
        return "Lit:" + self.lit

    def __repr__(self):
        return "Lit:" + self.lit

    def make_generator(self):
        def lit_gen():
            yield self.lit

        return lit_gen


def handle_range(toks):
    return CharacterRangeEmitter(srange(toks[0]))


def handle_repetition(toks):
    toks = toks[0]
    if toks[1] in "*+":
        raise ParseFatalException("", 0, "unbounded repetition operators not supported")
    if toks[1] == "?":
        return OptionalEmitter(toks[0])
    if "count" in toks:
        return GroupEmitter([toks[0]] * int(toks.count))
    if "minCount" in toks:
        mincount = int(toks.minCount)
        maxcount = int(toks.maxCount)
        optcount = maxcount - mincount
        if optcount:
            opt = OptionalEmitter(toks[0])
            for i in range(1, optcount):
                opt = OptionalEmitter(GroupEmitter([toks[0], opt]))
            return GroupEmitter([toks[0]] * mincount + [opt])
        else:
            return [toks[0]] * mincount


def handle_literal(toks):
    lit = ""
    for t in toks:
        if t[0] == "\\":
            if t[1] == "t":
                lit += '\t'
            else:
                lit += t[1]
        else:
            lit += t
    return LiteralEmitter(lit)


def handle_macro(toks):
    macroChar = toks[0][1]
    if macroChar == "d":
        return CharacterRangeEmitter("0123456789")
    elif macroChar == "w":
        return CharacterRangeEmitter(srange("[A-Za-z0-9_]"))
    elif macroChar == "s":
        return LiteralEmitter(" ")
    else:
        raise ParseFatalException("", 0, "unsupported macro character (" + macroChar + ")")


def handle_sequence(toks):
    return GroupEmitter(toks[0])


def handle_dot():
    return CharacterRangeEmitter(printables)


def handle_alternative(toks):
    return AlternativeEmitter(toks[0])


_parser = None
def parser():
    global _parser
    if _parser is None:
        ParserElement.setDefaultWhitespaceChars("")
        lbrack, rbrack, lbrace, rbrace, lparen, rparen = map(Literal, "[]{}()")

        reMacro = Combine("\\" + oneOf(list("dws")))
        escapedChar = ~ reMacro + Combine("\\" + oneOf(list(printables)))
        reLiteralChar = "".join(c for c in printables if c not in r"\[]{}().*?+|") + " \t"

        reRange = Combine(lbrack + SkipTo(rbrack, ignore=escapedChar) + rbrack)
        reLiteral = (escapedChar | oneOf(list(reLiteralChar)))
        reDot = Literal(".")
        repetition = (
                      (lbrace + Word(nums).setResultsName("count") + rbrace) |
                      (lbrace + Word(nums).setResultsName("minCount") + "," + Word(nums).setResultsName("maxCount") + rbrace) |
                      oneOf(list("*+?"))
                      )

        reRange.setParseAction(handle_range)
        reLiteral.setParseAction(handle_literal)
        reMacro.setParseAction(handle_macro)
        reDot.setParseAction(handle_dot)

        reTerm = (reLiteral | reRange | reMacro | reDot)
        reExpr = operatorPrecedence(reTerm, [
                (repetition, 1, opAssoc.LEFT, handle_repetition),
                (None, 2, opAssoc.LEFT, handle_sequence),
                (Suppress('|'), 2, opAssoc.LEFT, handle_alternative),
            ])

        _parser = reExpr

    return _parser


def count(gen):
    """Simple function to count the number of elements returned by a generator."""
    i = 0
    for s in gen:
        i += 1
    return i


def invregexp(regex):
    """Call this routine as a generator to return all the strings that
       match the input regular expression.
           for s in invregexp("[A-Z]{3}\d{3}"):
               print s
    """
    invReGenerator = GroupEmitter(parser().parseString(regex)).make_generator()
    return invReGenerator()


def main():
    tests = r"""
    [A-EA]
    [A-D]*
    [A-D]{3}
    X[A-C]{3}Y
    X[A-C]{3}\(
    X\d
    foobar\d\d
    foobar{2}
    foobar{2,9}
    fooba[rz]{2}
    (foobar){2}
    ([01]\d)|(2[0-5])
    ([01]\d\d)|(2[0-4]\d)|(25[0-5])
    [A-C]{1,2}
    [A-C]{0,3}
    [A-C]\s[A-C]\s[A-C]
    [A-C]\s?[A-C][A-C]
    [A-C]\s([A-C][A-C])
    [A-C]\s([A-C][A-C])?
    [A-C]{2}\d{2}
    @|TH[12]
    @(@|TH[12])?
    @(@|TH[12]|AL[12]|SP[123]|TB(1[0-9]?|20?|[3-9]))?
    @(@|TH[12]|AL[12]|SP[123]|TB(1[0-9]?|20?|[3-9])|OH(1[0-9]?|2[0-9]?|30?|[4-9]))?
    (([ECMP]|HA|AK)[SD]|HS)T
    [A-CV]{2}
    A[cglmrstu]|B[aehikr]?|C[adeflmorsu]?|D[bsy]|E[rsu]|F[emr]?|G[ade]|H[efgos]?|I[nr]?|Kr?|L[airu]|M[dgnot]|N[abdeiop]?|Os?|P[abdmortu]?|R[abefghnu]|S[bcegimnr]?|T[abcehilm]|Uu[bhopqst]|U|V|W|Xe|Yb?|Z[nr]
    (a|b)|(x|y)
    (a|b) (x|y)
    """.split('\n')

    for t in tests:
        t = t.strip()
        if not t:
            continue

        print '-' * 50
        print t
        try:
            print count(invregexp(t))
            for s in invregexp(t):
                print s

        except ParseFatalException,pfe:
            print pfe.msg
            print
            continue

        print


if __name__ == "__main__":
    main()
