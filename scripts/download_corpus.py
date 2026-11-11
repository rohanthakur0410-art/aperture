"""Download the employer-linked primary source for local analysis; do not commit it."""
from pathlib import Path
from urllib.request import urlopen
import hashlib
URL='https://www.cs.cmu.edu/~tom/files/MachineLearningTomMitchell.pdf'
dest=Path(__file__).resolve().parents[1]/'backend'/'data'/'corpus'/'mitchell.pdf'
dest.parent.mkdir(parents=True,exist_ok=True)
if dest.exists():
    print('Already present:',dest)
else:
    temporary=dest.with_suffix('.download')
    try:
        with urlopen(URL,timeout=90) as r,temporary.open('wb') as f:
            first=r.read(1024)
            if not first.startswith(b'%PDF'):raise RuntimeError('Source did not return a PDF.')
            f.write(first)
            while True:
                chunk=r.read(1024*1024)
                if not chunk:break
                f.write(chunk)
        temporary.replace(dest)
    finally:
        if temporary.exists():temporary.unlink()
    print('Downloaded:',dest)
print('SHA256:',hashlib.sha256(dest.read_bytes()).hexdigest())
