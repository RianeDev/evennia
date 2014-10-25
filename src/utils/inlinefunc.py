"""
Inlinefunc

This is a simple inline text language for use to custom-format text
in Evennia. It is applied BEFORE ANSI/MUX parsing is applied.

The format is straightforward:


{funcname([arg1,arg2,...]) text {/funcname


Example:
    "This is {pad(50,c,-) a center-padded text{/pad of width 50."
    ->
    "This is -------------- a center-padded text--------------- of width 50."

This can be inserted in any text, operated on by the parse_inlinefunc
function.  funcname() (no space is allowed between the name and the
argument tuple) is picked from a selection of valid functions from
settings.INLINETEXT_FUNC_MODULES.

Commands can be nested, and will applied inside-out. For correct
parsing their end-tags must match the starting tags in reverse order.

Example:
    "The time is {pad(30){time(){/time{/padright now."
    ->
    "The time is         Oct 25, 11:09         right now."

An inline function should have the following call signature:

    def funcname(text, *args)

where the text is always the part between {funcname(args) and
{/funcname and the *args are taken from the appropriate part of the
call. It is important that the inline function properly clean the
incoming args, checking their type and replacing them with sane
defaults if needed. If impossible to resolve, the unmodified text
should be returned. The inlinefunc should never cause a traceback.

"""

import re
from django.conf import settings
from src.utils import utils


# inline functions

def pad(text, *args):
    "Pad to width. pad(text, width=78, align='c', fillchar=' ')"
    width = 78
    align = 'c'
    fillchar = ' '
    for iarg, arg in enumerate(args):
        if iarg == 0:
            width = int(arg) if arg.isdigit() else width
        elif iarg == 1:
            align = arg if arg in ('c', 'l', 'r') else align
        elif iarg == 2:
            fillchar = arg[0]
        else:
            break
    return utils.pad(text, width=width, align=align, fillchar=fillchar)

def crop(text, *args):
    "Crop to width. crop(text, width=78, suffix='[...]')"
    width = 78
    suffix = "[...]"
    for iarg, arg in enumerate(args):
        if iarg == 0:
            width = int(arg) if arg.isdigit() else width
        elif iarg == 1:
            suffix = arg
        else:
            break
    return utils.crop(text, width=width, suffix=suffix)

def wrap(text, *args):
    "Wrap/Fill text to width. fill(text, width=78, indent=0)"
    width = 78
    indent = 0
    for iarg, arg in enumerate(args):
        if iarg == 0:
            width = int(arg) if arg.isdigit() else width
        elif iarg == 1:
            indent = int(arg) if arg.isdigit() else indent
    return utils.wrap(text, width=width, indent=indent)

def time(text, *args):
    "Inserts current time"
    import time
    strformat = "%h %d, %H:%M"
    if args and args[0]:
        strformat = str(args[0])
    return time.strftime(strformat)

# load functions from module (including this one, if using default settings)
_INLINE_FUNCS = {}
for module in utils.make_iter(settings.INLINEFUNC_MODULES):
    _INLINE_FUNCS.update(utils.all_from_module(module))
_INLINE_FUNCS.pop("inline_func_parse", None)

# dynamically build regexes for found functions
_RE_FUNCFULL = r"\{%s\((.*?)\)(.*?){/%s"
_RE_FUNCSTART = r"\{((?:%s))"
_RE_FUNCEND = r"\{/((?:%s))"
_RE_FUNCSPLIT = r"(\{/*(?:%s)(?:\(.*?\))*)"
_RE_FUNCCLEAN = r"\{%s\(.*?\)|\{/%s"

_INLINE_FUNCS = dict((key, (func, re.compile(_RE_FUNCFULL % (key, key), re.DOTALL &  re.MULTILINE)))
                          for key, func in _INLINE_FUNCS.items() if callable(func))
_FUNCSPLIT_REGEX = re.compile(_RE_FUNCSPLIT % r"|".join([key for key in _INLINE_FUNCS]), re.DOTALL & re.MULTILINE)
_FUNCSTART_REGEX = re.compile(_RE_FUNCSTART % r"|".join([key for key in _INLINE_FUNCS]), re.DOTALL & re.MULTILINE)
_FUNCEND_REGEX = re.compile(_RE_FUNCEND % r"|".join([key for key in _INLINE_FUNCS]), re.DOTALL & re.MULTILINE)
_FUNCCLEAN_REGEX = re.compile("|".join([_RE_FUNCCLEAN % (key, key) for key in _INLINE_FUNCS]), re.DOTALL & re.MULTILINE)


# inline parser functions

def _execute_inline_function(funcname, text):
    """
    Get the enclosed text between {funcname(...) and {/funcname
    and execute the inline function to replace the whole block
    with the result.
    Note that this lookup is "dumb" - we just grab the first end
    tag we find. So to work correctly this function must be called
    "inside out" on a nested function tree, so each call only works
    on a "flat" tag.
    """
    def subfunc(match):
        "replace the entire block with the result of the function call"
        args = [part.strip() for part in match.group(1).split(",")]
        intext = match.group(2)
        return _INLINE_FUNCS[funcname][0](intext, *args)
    return _INLINE_FUNCS[funcname][1].sub(subfunc, text)


def parse_inlinefunc(text, strip=False):
    """
    Parse inline function-replacement.

    Default is to ignore such functions,
    use strip=False to leave them in.
    """

    if strip:
        return _FUNCCLEAN_REGEX.sub("", text)

    stack = []
    for part in _FUNCSPLIT_REGEX.split(text):
        endtag = _FUNCEND_REGEX.match(part)
        if endtag:
            # an end tag
            endname = endtag.group(1)
            while stack:
                new_part = stack.pop()
                part = new_part + part  # add backwards -> fowards
                starttag = _FUNCSTART_REGEX.match(new_part)
                if starttag:
                    startname = starttag.group(1)
                    if startname == endname:
                        part = _execute_inline_function(startname, part)
                        break
        stack.append(part)
    return "".join(stack)

def _test():
    # this should pad everything
    s = "This is a {crop()text at {time(){/time with a{pad(78,r,-)text {pad(5)of{/pad {pad(8)nice{/pad size{/pad inside {pad(4,l)it{/pad.{/crop"
    print " intext:", s
    t = parse_inlinefunc(s)
    print "outtext:", t
