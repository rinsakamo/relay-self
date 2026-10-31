from pathlib import Path
import hashlib,json,urllib.request,shutil
r=Path('/home/rinsa/work/s50-client-packet-evidence-20261031');a=r/'assets'
p=a/'adapters/mineflayer/m02_paper_dev'
req=urllib.request.Request('https://fill.papermc.io/v3/projects/paper/versions/1.21.8/builds/60',headers={'User-Agent':'RelaySelf-S50-DEV/1.0 (rinsakamo/relay-self)'})
raw=urllib.request.urlopen(req,timeout=30).read();(a/'paper-official-build60.json').write_bytes(raw)
d=json.loads(raw)['downloads']['server:default'];s=Path('/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(s)==d['checksums']['sha256']=='8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e' and s.stat().st_size==d['size']
plugin=a/'relay-metabolism-paper-dev.jar';shutil.copyfile(p/'target/relay-metabolism-paper-dev-0.2.0-dev.jar',plugin)
text=(p/'src/main/resources/config.yml').read_text(); assert len([s for s in text.splitlines() if s.startswith('  ')])==16
text=text.replace('dev-enabled: false','dev-enabled: true',1).replace('s50-input-witness-dev: false','s50-input-witness-dev: true',1)+'\ns50-tick-meter-dev: true\n'
c=a/'config.yml';c.write_text(text)
pins={k:{'path':str(f),'sha256':sha(f)} for k,f in [('server',s),('plugin',plugin),('config',c)]};pins['intervention']='ACTIVE_METABOLISM_NOT_PASSIVE';pins['plugin_source_head']='3bb79ed57c4a0940bdc586c72976c7ece079319f'
(a/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print(json.dumps(pins,indent=2))
