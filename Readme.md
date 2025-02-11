# Search in PDFs

Search for a term in all the pdfs specified in the [config.ini](config.ini.template).

## Dependencies:
* Python 3.12.7
* Redis. Either via Docker or running in your machine

The [auto installing script](#run-script) works only with these dependencies on linux machines:
* pyenv 2.4.16
* pyenv-virtualenv 1.2.4

Other dependencies to run are listed in [requirements.txt](requirements.txt).

## Installation

For manual installation, it is recommended the use of a virtual environment.
```bash
pip install -r requirements.txt
```

## Run
Call [main.py](main.py) script to start the server:
```bash
python3 main.py
```
Go to [localhost:1234](http://localhost:1234)

## Run script
(Check dependecies above)
Move it to your `.local/bin/`
```bash
sudo cp search_pdf ~/bin/search_pdf
```
You may need to personalize the path based on your machine and add the path:
```bash
export PATH=$PATH:~/bin
```
Give the script execution permissions. 
```bash
chmod +x ~/bin/search_pdf
```
Reload the terminal or open a new one and try it
```bash
search_pdf
```
Optionally you can pass it an argument of search
```bash
search_pdf mysearch
```

After executing the command, a new window in your browser will be opened with the search page or the results page if you
invoked the command with an argument.