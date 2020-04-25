#!/usr/bin/env python
import os,sys
import argparse
import json
from copy import deepcopy
from coverage.phystokens import source_token_lines
import jupytext

def search_for_file_containing_line(basedir_:str, searchfor_:str):
  searchfor_ = searchfor_.strip('\r\n')
  for (dirpath, dirnames, filenames) in os.walk(basedir_):
    for fpath in [os.path.join(dirpath, file) for file in filenames]:
      if os.path.isfile(fpath) and fpath.endswith('.py') and os.path.getsize(fpath) > 9:
        with open(fpath,'r') as infile:
          for line in infile:
            if line.strip('\r\n') == searchfor_:
              return fpath

# the coverage tokenizer returns a line as a sequence of tuples (TYPE, TEXT)
# to get the original python text, just join all the tokens' TEXT
def join_tokens(seq_):
  return "".join([tup_[1] for tup_ in seq_]).strip('\r\n')

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--eval_until_argparse", action='store_true',
                 help='evaluate the script statement-by-statement until argparse?' \
                    +' can help fix parse errors if runtime variables were used to define args')
parser.add_argument("infile")
parser.add_argument("out_dest")
parser.add_argument("args4parser", nargs="*")
args = parser.parse_args()
assert os.path.isfile(args.infile) and args.infile.endswith('.py'), args.infile
args.infile = os.path.abspath(args.infile)
assert os.path.isfile(args.infile), args.infile
assert isinstance(args.out_dest,str), str(type(args.out_dest))
assert args.out_dest.endswith('.ipynb'), 'want to create an ipython notebook from a python file... please specify the output ipynb file'

infdir = os.path.dirname(args.infile)
filewithmutabledict = search_for_file_containing_line(infdir, 'class MutableClassDict(MutableMapping):')
assert filewithmutabledict is not None, 'need a python file that defines the MutableClassDict class, to convert argparse'
assert filewithmutabledict.startswith(infdir), '\n'+filewithmutabledict+'\n'+infdir+'\n'
py_import_path_to_file_with_mutable_dict = filewithmutabledict[len(infdir)+1:].replace('/','.').rstrip('.py')

# special parse mode: execute statements line-by-line until we reach argparse
if args.eval_until_argparse:
  sys.path.append(infdir)

# when parsing tokens, there are three categories of lines we are interested in
# in a given line, for each category, we check if all of the tokens appear in this specified order
# if all of the tokens for a category appear in order, we say that that line is of that category
check_sequences = {
  'argparse_start': [('op', '='), ('nam', 'argparse'), ('op', '.'), ('nam', 'ArgumentParser'), ('op', '(')],
  'argparse_arg': [('op', '.'), ('nam', 'add_argument'), ('op', '(')],
  'argparse_end': [('op', '='), ('op', '.'), ('nam', 'parse_args'), ('op', '(')],
 }
keyz = deepcopy(sorted(list(check_sequences.keys())))

argsasadded = []
def when_first_appear(asaddeds, argname):
  for ii_,strs_ in enumerate(asaddeds):
    if argname in strs_ or "-"+argname in strs_ or "--"+argname in strs_:
      return ii_
  return len(asaddeds)

parsingparser = None
parsingparser_ARGS = None

FINALPRINTED = ""

#with open(args.out_dest,'w') as outfile:
if True:
  with open(args.infile,'r') as infile:
    for line in source_token_lines(infile.read()):

      # make a copy, since we will destructively pop entries as we detect them in order
      chkmes = deepcopy(check_sequences)
      # afters == we will save the remainder tokens on the line after the matched tokens above
      #              (i.e., any arguments to the argparse line)
      afters = {kk:[] for kk in keyz}

      # check for matching tokens and pop_front if we find a match for a category
      for el in line:
        for kk in keyz:
          if len(chkmes[kk]) == 0:
            afters[kk].append(el)
          elif el == chkmes[kk][0]:
            chkmes[kk] = chkmes[kk][1:]

      # was any category matched? if not, just print the line as it was
      no_category_match = True
      for kk in keyz:
        if len(chkmes[kk]) == 0:
          # this category kk was entirely popped, i.e. all of its tokens were matched in order

          # switch(what category this line is) {
          if kk == 'argparse_start':
            assert parsingparser is None and parsingparser_ARGS is None, 'can only instantiate ONE argparse.ArgumentParser()'

            try:
                parsingparser = eval('argparse.ArgumentParser('+join_tokens(afters[kk]))
            except NameError:
                parsingparser = argparse.ArgumentParser()

            assert isinstance(parsingparser,argparse.ArgumentParser), str(type(parsingparser))
            # generate python code for importing the MutableClassDict and initializing an args dict
            prstr = "\n# these parameters were auto-converted from argparse\n\n" \
               +"from "+py_import_path_to_file_with_mutable_dict+" import MutableClassDict; args = MutableClassDict()"
            if parsingparser.description is not None and len(parsingparser.description) > 0:
              prstr += " \# "+parsingparser.description
            FINALPRINTED += prstr+"\n" # building to the python file we will pass to jupytext

          elif kk == 'argparse_arg':
            assert parsingparser_ARGS is None, 'not done yet!'
            assert parsingparser is not None, 'need to create an argparse.ArgumentParser() before adding args'
            eval('parsingparser.add_argument('+join_tokens(afters[kk]))
            # we will keep track of the order in which args were specified in the original file; save the parser args for matching later
            argsasadded.append( list([tup[1].strip('\'\"') for tup in afters[kk] if tup[0] == 'str']) )

          elif kk == 'argparse_end':
            assert parsingparser_ARGS is None, 'not done yet!'
            parsingparser_DONE = True
            # we were using eval() to actually reproduce the argparse parser here
            parsingparser_ARGS = vars(parsingparser.parse_args(args.args4parser))
            del parsingparser
            # match arg names to the .add_argument() args list that we were saving in order
            keys2whenapp = {k2:when_first_appear(argsasadded,k2) for k2 in parsingparser_ARGS.keys()}
            # add args line-by-line to the python file we are building in-memory
            for k2 in sorted(list(keys2whenapp.keys()), key=lambda x2:keys2whenapp[x2]):
              assert ' ' not in k2 and '\t' not in k2 and '\n' not in k2 and '\r' not in k2, k2
              dumpval = json.dumps(parsingparser_ARGS[k2]) # TODO: how to properly reproduce python CODE declaration of variable
              if isinstance(parsingparser_ARGS[k2],bool):
                dumpval = str(parsingparser_ARGS[k2])
              FINALPRINTED += "args."+k2+" = "+dumpval+"\n"

          no_category_match = False

      # if no argparse line category match, just print the line
      # although, one last conversion fix: replace __file__ with the file path, since jupyter doesnt know __file__
      if no_category_match:
        line = join_tokens(line)
        line = line.replace('(__file__)', '('+json.dumps(os.path.abspath(args.infile))+')')
        if args.eval_until_argparse and parsingparser_ARGS is None:
          evalline = line.strip('\r\n\t ')
          if len(evalline) > 0 and evalline[0] != '#':
            exec(evalline)
        FINALPRINTED += line+"\n"

jupytext.write(jupytext.reads(FINALPRINTED,fmt='py'), args.out_dest)
