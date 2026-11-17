"""Opciós Google Drive-tárolás. A titkos kulcs csak GitHub Actions Secretből olvasható."""
from __future__ import annotations
import io
import json
import os
from pathlib import Path


def _client():
    raw=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not raw:
        return None
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    data=json.loads(raw)
    creds=Credentials.from_service_account_info(data,scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive','v3',credentials=creds,cache_discovery=False)


def _folder():
    return os.environ.get('GOOGLE_DRIVE_FOLDER_ID','').strip()


def pull(path:Path) -> str:
    client=_client()
    if not client or not _folder():
        return 'Drive nincs bekötve; GitHub Actions cache lesz használva.'
    query="name = 'press_review_state.json' and trashed = false and '"+_folder()+"' in parents"
    listing=client.files().list(q=query,fields='files(id,name,modifiedTime)',orderBy='modifiedTime desc',page_size=10).execute()
    found=listing.get('files',[])
    if not found:
        return 'Drive-ban még nincs mentett állapot.'
    data=client.files().get_media(fileId=found[0]['id']).execute()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    return 'Drive állapot betöltve.'


def push_state(path:Path) -> str:
    client=_client()
    if not client or not _folder():
        return 'Drive mentés kihagyva.'
    from googleapiclient.http import MediaFileUpload
    query="name = 'press_review_state.json' and trashed = false and '"+_folder()+"' in parents"
    listing=client.files().list(q=query,fields='files(id)',page_size=5).execute()
    media=MediaFileUpload(str(path),mimetype='application/json',resumable=False)
    files=listing.get('files',[])
    if files:
        client.files().update(fileId=files[0]['id'],media_body=media,fields='id').execute()
    else:
        client.files().create(body={'name':'press_review_state.json','parents':[_folder()]},media_body=media,fields='id').execute()
    return 'Drive állapot mentve.'


def upload_pdf(path:Path) -> dict:
    client=_client()
    if not client or not _folder():
        raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON vagy GOOGLE_DRIVE_FOLDER_ID hiányzik')
    from googleapiclient.http import MediaFileUpload
    media=MediaFileUpload(str(path),mimetype='application/pdf',resumable=False)
    result=client.files().create(body={'name':path.name,'parents':[_folder()]},media_body=media,
                                 fields='id,name,size,webViewLink,mimeType,parents').execute()
    verify=client.files().get(fileId=result['id'],fields='id,name,size,webViewLink,mimeType,parents').execute()
    if verify.get('mimeType')!='application/pdf' or _folder() not in verify.get('parents',[]):
        raise RuntimeError('Drive metaadat-visszaellenőrzés sikertelen')
    if int(verify.get('size',0))!=path.stat().st_size:
        raise RuntimeError('Drive PDF fájlméret nem egyezik')
    return verify