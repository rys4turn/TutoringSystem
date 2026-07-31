import json, hashlib, os, tarfile, io, requests, gzip

DEPLOY = r'D:\Code\补习班教务管理系统\docker-deploy'
OUTPUT = r'D:\Code\补习班教务管理系统\tutoring-system.tar'

print('[1/6] Authenticating with Docker Hub...')
auth_url = 'https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull'
r = requests.get(auth_url, timeout=15)
r.raise_for_status()
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}
print('  OK')

print('[2/6] Pulling manifest for python:3.11-slim...')
mh = {**headers, 'Accept': 'application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'}
r = requests.get('https://registry-1.docker.io/v2/library/python/manifests/3.11-slim', headers=mh, timeout=15)
r.raise_for_status()
manifest = r.json()
cfg_digest = manifest['config']['digest']
print(f'  {len(manifest["layers"])} layers')

print('[3/6] Downloading base layers...')
base_layers = []
for i, layer in enumerate(manifest['layers']):
    d = layer['digest']
    sz = layer['size'] / 1e6
    print(f'  Layer {i+1}/{len(manifest["layers"])}: {d[7:19]}... ({sz:.1f} MB)')
    r = requests.get(f'https://registry-1.docker.io/v2/library/python/blobs/{d}', headers=headers, timeout=120)
    r.raise_for_status()
    base_layers.append((d, r.content))
total = sum(len(d) for _, d in base_layers) / 1e6
print(f'  Downloaded: {total:.1f} MB')

print('[4/6] Downloading image config...')
r = requests.get(f'https://registry-1.docker.io/v2/library/python/blobs/{cfg_digest}', headers=headers, timeout=30)
r.raise_for_status()
base_cfg = json.loads(r.content)

print('[5/6] Building application layer...')
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w') as tf:
    be = os.path.join(DEPLOY, 'backend')
    for root, dirs, files in os.walk(be):
        for fn in files:
            fp = os.path.join(root, fn)
            arc = '/app/' + os.path.relpath(fp, be).replace('\\', '/')
            ti = tf.gettarinfo(fp, arc)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = 'root'
            with open(fp, 'rb') as f:
                tf.addfile(ti, f)
    # /app/data dir
    dti = tarfile.TarInfo('/app/data')
    dti.type = tarfile.DIRTYPE
    dti.mode = 0o755
    dti.uid = dti.gid = 0
    dti.uname = dti.gname = 'root'
    tf.addfile(dti)

raw = buf.getvalue()
zbuf = io.BytesIO()
with gzip.GzipFile(fileobj=zbuf, mode='wb') as gz:
    gz.write(raw)
app_gz = zbuf.getvalue()
app_digest = 'sha256:' + hashlib.sha256(app_gz).hexdigest()
print(f'  App layer: {len(app_gz)/1024:.1f} KB, {app_digest[:25]}...')

print('[6/6] Assembling image tar...')
new_cfg = dict(base_cfg)
new_cfg['config']['Cmd'] = ['python', 'launcher.py']
new_cfg['config']['WorkingDir'] = '/app'
new_cfg['config']['ExposedPorts'] = {'5000/tcp': {}}
env = new_cfg['config'].get('Env', [])
env += ['TUTORING_DB=/app/data/tutoring.db', 'TUTORING_HOST=0.0.0.0', 'TUTORING_PORT=5000', 'DOCKER_ENV=1']
new_cfg['config']['Env'] = env
new_cfg['history'] = base_cfg.get('history', []) + [{
    'created': '2026-07-30T00:00:00Z',
    'created_by': 'pip install && COPY backend',
    'empty_layer': False,
}]
cfg_json = json.dumps(new_cfg).encode()
cfg_d = 'sha256:' + hashlib.sha256(cfg_json).hexdigest()

all_lyr = [l[0] for l in base_layers] + [app_digest]
mf = [{
    'Config': f'{cfg_d.replace(":", "")}.json',
    'RepoTags': ['tutoring-system:latest'],
    'Layers': [f'{d.replace(":", "")}/layer.tar' for d in all_lyr],
}]
repos = {'tutoring-system': {'latest': app_digest.replace('sha256:', '')}}

with tarfile.open(OUTPUT, 'w') as tf:
    mfb = json.dumps(mf).encode()
    ti = tarfile.TarInfo('manifest.json'); ti.size = len(mfb); tf.addfile(ti, io.BytesIO(mfb))
    rpb = json.dumps(repos).encode()
    ti = tarfile.TarInfo('repositories'); ti.size = len(rpb); tf.addfile(ti, io.BytesIO(rpb))
    ti = tarfile.TarInfo(f'{cfg_d.replace(":", "")}.json'); ti.size = len(cfg_json); tf.addfile(ti, io.BytesIO(cfg_json))
    for dg, data in base_layers:
        dn = dg.replace('sha256:', '')
        ti = tarfile.TarInfo(f'{dn}/layer.tar'); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))
        lj = json.dumps({'id': dn}).encode()
        ti = tarfile.TarInfo(f'{dn}/json'); ti.size = len(lj); tf.addfile(ti, io.BytesIO(lj))
        ti = tarfile.TarInfo(f'{dn}/VERSION'); ti.size = 3; tf.addfile(ti, io.BytesIO(b'1.0'))
    ad = app_digest.replace('sha256:', '')
    ti = tarfile.TarInfo(f'{ad}/layer.tar'); ti.size = len(app_gz); tf.addfile(ti, io.BytesIO(app_gz))
    lj = json.dumps({'id': ad}).encode()
    ti = tarfile.TarInfo(f'{ad}/json'); ti.size = len(lj); tf.addfile(ti, io.BytesIO(lj))
    ti = tarfile.TarInfo(f'{ad}/VERSION'); ti.size = 3; tf.addfile(ti, io.BytesIO(b'1.0'))

sz = os.path.getsize(OUTPUT) / 1e6
print(f'  Done! {OUTPUT} ({sz:.1f} MB)')
