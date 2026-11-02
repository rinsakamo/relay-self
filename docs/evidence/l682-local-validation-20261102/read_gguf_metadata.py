import struct,json
from pathlib import Path
p=Path('/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf')
f=p.open('rb')
def unpack(fmt):return struct.unpack('<'+fmt,f.read(struct.calcsize('<'+fmt)))[0]
def string():return f.read(unpack('Q')).decode('utf-8')
formats={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
def value(t,keep=True):
 if t in formats:return unpack(formats[t])
 if t==8:return string()
 if t==9:
  subtype=unpack('I');n=unpack('Q')
  if not keep and subtype in formats:f.seek(n*struct.calcsize('<'+formats[subtype]),1);return None
  out=[]
  for _ in range(n):
   v=value(subtype,keep)
   if keep:out.append(v)
  return out if keep else None
 raise ValueError(t)
assert f.read(4)==b'GGUF'
version=unpack('I');tensors=unpack('Q');count=unpack('Q');d={'gguf_version':version,'tensor_count':tensors,'metadata_count':count}
for _ in range(count):
 k=string();t=unpack('I');keep=k.startswith('general.') or k.endswith('.context_length') or k.endswith('.block_count')
 v=value(t,keep)
 if keep:d[k]=v
Path(__file__).with_name('gguf-metadata.json').write_text(json.dumps(d,indent=2));print(json.dumps(d,indent=2))
