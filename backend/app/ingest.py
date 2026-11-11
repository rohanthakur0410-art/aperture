from .rag import ingest
from .config import DATA
if __name__=='__main__':
    import sys
    print('Indexed chunks:',ingest(sys.argv[1] if len(sys.argv)>1 else DATA/'corpus'/'mitchell.pdf'))
