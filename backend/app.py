import os, re, uuid, subprocess, threading, shutil
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('ORIGINS','http://localhost:5173').split(','),allow_methods=['GET','POST'],allow_headers=['*'])
ROOT=Path(os.getenv('JOB_DIR','jobs')).resolve(); ROOT.mkdir(exist_ok=True)
jobs={}; lock=threading.Lock()
def location(url):
    u=urlparse(url)
    if u.scheme!='https' or u.hostname not in ('www.google.com','maps.google.com'): raise ValueError('Expected Google Maps URL')
    m=re.search(r'@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',u.path)
    if not m: raise ValueError('Missing coordinates')
    lat,lon=map(float,m.groups())
    if abs(lat)>90 or abs(lon)>180: raise ValueError('Invalid coordinates')
    return {'latitude':lat,'longitude':lon}
def run(jid,mode,iterations):
    p=ROOT/jid
    with lock:
        try:
            with (p/'training.log').open('w') as log:
                def cmd(args): subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT)
                jobs[jid]['status']='processing'
                source=p/'input'
                cmd(['ns-process-data',mode,'--data',str(source/'video.mp4' if mode=='video' else source),'--output-dir',str(p/'dataset')])
                jobs[jid]['status']='training'
                cmd(['ns-train','splatfacto','--data',str(p/'dataset'),'--output-dir',str(p/'training'),'--max-num-iterations',str(iterations),'--vis','tensorboard'])
                configs=list((p/'training').rglob('config.yml'))
                if len(configs)!=1: raise RuntimeError('Expected one training config')
                cmd(['ns-export','gaussian-splat','--load-config',str(configs[0]),'--output-dir',str(p/'export')])
                models=list((p/'export').glob('*.ply'))
                if len(models)!=1: raise RuntimeError('Missing PLY export')
                shutil.move(models[0],p/'scene.ply'); jobs[jid]['status']='complete'
        except Exception as e: jobs[jid].update(status='failed',error=str(e))
@app.get('/health')
def health(): return {'status':'ok','training_available':bool(shutil.which('ns-train'))}
@app.post('/jobs')
async def create(url:str=Form(...),authorized:bool=Form(...),quality:str=Form('high'),files:list[UploadFile]=File(...)):
    if not authorized: raise HTTPException(400,'Authorized imagery required')
    try: coords=location(url)
    except ValueError as e: raise HTTPException(400,str(e))
    suffixes=[Path(f.filename or '').suffix.lower() for f in files]
    mode='video' if suffixes==['.mp4'] else 'images'
    if mode=='images' and (len(files)<3 or any(s not in ('.jpg','.jpeg','.png') for s in suffixes)): raise HTTPException(400,'Upload one MP4 or at least three overlapping perspective images')
    if quality not in ('fast','high','ultra'): raise HTTPException(400,'Invalid quality')
    jid=uuid.uuid4().hex; p=ROOT/jid/'input'; p.mkdir(parents=True)
    total=0
    try:
        for i,f in enumerate(files):
            with (p/('video.mp4' if mode=='video' else f'{i:06d}{suffixes[i]}')).open('wb') as out:
                while chunk:=await f.read(1024*1024):
                    total+=len(chunk)
                    if total>1024**3: raise HTTPException(413,'Upload exceeds 1 GiB')
                    out.write(chunk)
    except Exception:
        shutil.rmtree(p.parent); raise
    jobs[jid]={'id':jid,'status':'queued',**coords}
    threading.Thread(target=run,args=(jid,mode,{'fast':7000,'high':30000,'ultra':60000}[quality]),daemon=True).start()
    return jobs[jid]
@app.get('/jobs/{jid}')
def status(jid:str):
    if jid not in jobs: raise HTTPException(404)
    return jobs[jid]
@app.get('/jobs/{jid}/model')
def model(jid:str):
    if jid not in jobs or jobs[jid]['status']!='complete': raise HTTPException(404)
    return FileResponse(ROOT/jid/'scene.ply',filename='scene.ply')
