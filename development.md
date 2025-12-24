## Subtasks
- **bold** versions are currently used in this project

### compress PDFs

- [pdfsizeopt](https://github.com/pts/pdfsizeopt) - old
- [pdfc](https://github.com/theeko74/pdfc) - small sideproject
  - [usage Example](https://itheo.nl/repair-and-compress-pdf-files-with-python/)
  - **[CompressPDF](https://github.com/tvdsluijs/pdfc) - more modern Version**
- [pyPDF2](https://stackoverflow.com/questions/22776388/pypdf2-compression) - dead for 4 years
    - [List of alternatives](https://stackoverflow.com/questions/63199763/maintained-alternatives-to-pypdf2)
- [pdfTron](https://www.pdftron.com/documentation/samples/py/OptimizerTest) - commercial

### improve image before OCR

- [unpaper](https://github.com/unpaper/unpaper)
- [pre-recognition lib](https://github.com/leha-bot/PRLib)
- [scantailor](https://github.com/4lex4/scantailor-advanced#-scantailor-advanced)
- **openCV2** with custom filters

### Detect Language

- [Overview Thread](https://stackoverflow.com/questions/39142778/python-how-to-determine-the-language)
- [langdetect](https://pypi.python.org/pypi/langdetect?) - requires large text portions, trouble with parallel exec
- **[langid](https://github.com/saffsd/langid.py)** - can be very slow
- [fasttext](https://fasttext.cc/) - needs separate model
    - [model for language identification](https://fasttext.cc/docs/en/language-identification.html)

### Detect Date

- **[dateparser](https://dateparser.readthedocs.io/en/latest/)**

### Extract Keywords

- **[rake](https://pypi.org/project/rake-nltk/)**
- **check against plain wordlist**
