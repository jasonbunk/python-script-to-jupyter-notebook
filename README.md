### python-script-to-jupyter-notebook, handling argparse
Uses Jupytext for conversion; removes argparse within the script.

**It replaces argparse with a cell in the notebook** that defines the args directly into a dictionary, <br>
so that the args are specified within the notebook

### Files in this repo

* ```extract_argparse.py``` is the main script that does the conversion. <br>
It will actually ```eval()``` the argparse configuration in the script being converted; <br>
any non-default arguments will need to be provided.

* ```MutableClassDict.py``` should be copied to your project folder somewhere; <br>
it will be used to replace ```argparse``` in the script.
