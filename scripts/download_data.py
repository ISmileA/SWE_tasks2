"""Мы скачиваем исходный MovieLens, проверяем MD5 и безопасно распаковываем архив."""
from pathlib import Path
import hashlib, json, re, urllib.request, zipfile


def parse_md5(text):
    matches=re.findall(r'\b[a-fA-F0-9]{32}\b',text)
    if len(matches)!=1: raise ValueError('Unexpected checksum format')
    return matches[0].lower()


def main():
    root=Path('data'); root.mkdir(exist_ok=True)
    url='https://files.grouplens.org/datasets/movielens/ml-100k.zip'
    archive=root/'ml-100k.zip'
    if not archive.exists(): urllib.request.urlretrieve(url,archive)
    raw=archive.read_bytes()
    checksum=parse_md5(urllib.request.urlopen(url+'.md5',timeout=30).read().decode())
    actual=hashlib.md5(raw).hexdigest()
    if actual!=checksum: raise RuntimeError(f'MD5 mismatch: {actual} != {checksum}')
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target=(root/member.filename).resolve()
            if not target.is_relative_to(root.resolve()): raise ValueError('Unsafe archive path')
        z.extractall(root)
    manifest={'url':url,'md5':actual,'sha256':hashlib.sha256(raw).hexdigest(),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'ml-100k').iterdir()) if p.is_file()}}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
