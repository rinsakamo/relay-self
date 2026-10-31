from pathlib import Path
import hashlib,json,subprocess,urllib.request
r=Path('/home/rinsa/work/l23-evidence-20261031')
a=r/'assets'
s=Path('/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar')
p=r/'s-owner-source/adapters/mineflayer/m02_paper_dev/target/relay-metabolism-paper-dev-0.2.0-dev.jar'
c=(r/'s-owner-source/adapters/mineflayer/m02_paper_dev/src/main/resources/config.yml').read_text().replace('dev-enabled: false','dev-enabled: true')+'\ns50-tick-meter-dev: true\n'
(a/'config.yml').write_text(c)
req=urllib.request.Request('https://fill.papermc.io/v3/projects/paper/versions/1.21.8/builds/60',headers={'User-Agent':'RelaySelf-L23-DEV/1.0 (rinsakamo/relay-self)'})
raw=urllib.request.urlopen(req,timeout=30).read()
(a/'paper-official-build60.json').write_bytes(raw)
d=json.loads(raw)['downloads']['server:default']
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(s)==d['checksums']['sha256'] and s.stat().st_size==d['size']
assets={'server':{'path':str(s),'sha256':sha(s)},'plugin':{'path':str(p),'sha256':sha(p),'source_head':'3240691a29e1f02bcb89cc20cf650ac9a0e83662','source_unchanged':True},'config':{'path':str(a/'config.yml'),'sha256':sha(a/'config.yml')},'intervention':'ACTIVE_METABOLISM_NOT_PASSIVE'}
(a/'pins.json').write_text(json.dumps(assets,indent=2)+'\n')
print(json.dumps(assets,indent=2))
