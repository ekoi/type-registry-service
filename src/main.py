import importlib.metadata
import logging

import requests
import uvicorn
from dynaconf import Dynaconf
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jsonpath_ng.ext import parse
from starlette import status

settings = Dynaconf(settings_files=["conf/settings.toml", "conf/.secrets.toml"],
                    environments=True)
logging.basicConfig(filename=settings.LOG_FILE, level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT)


__version__ = importlib.metadata.metadata(settings.SERVICE_NAME)["version"]


api_keys = [
    settings.DANS_TYPE_REGISTRY_SERVICE_API_KEY
]  #

#Authorization Form: It doesn't matter what you type in the form, it won't work yet. But we'll get there.
#See: https://fastapi.tiangolo.com/tutorial/security/first-steps/
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # use token authentication


def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key not in api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden"
        )


app = FastAPI(title=settings.FASTAPI_TITLE, description=settings.FASTAPI_DESCRIPTION,
              version=__version__)

data = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event('startup')
def common_data():
    logging.debug("startup")

    url_resp = requests.get(settings.DANS_FORMATS_URL)
    if url_resp.status_code == 200:
        data.update({'dans_formats': url_resp.json()})
        return data
    # TODO: error or exit?
    exit(1)


@app.get('/')
def info():
    logging.info("Type registry service")
    logging.debug("info")
    return {"name": "Type registry service", "version": __version__}


@app.get('/type/{filetype}')
def check_type(filetype: str):
    logging.info("Type registry service")
    logging.debug("info")
    dans_formats = data['dans_formats']
    jsonpath_exp = parse("$..format[*].file-extension")

    for match in jsonpath_exp.find(dans_formats):
        if match.value == filetype:
            logging.debug(f'Filetype match: {match.value}')
            return {"checked": filetype, "accepted": True}
            break

    return {"checked": filetype, "accepted": False}


@app.get('/type-list-simple')
def retrieve_simple_list():
    logging.info("Type registry service")
    logging.debug("info")
    dans_formats = data['dans_formats']
    jsonpath_exp = parse("$..format[*].file-extension")
    list_type = []
    for match in jsonpath_exp.find(dans_formats):
        list_type.append(match.value)

    return {"list": list_type}


@app.get('/type-list-grouped')
def retrieve_grouped_list():
    logging.info("Type registry service")
    logging.debug("info")
    dans_formats = data['dans_formats']
    jsonpath_exp = parse("$..type[*]")
    list_type = []
    for match in jsonpath_exp.find(dans_formats):
        list_extension = []
        for file_ext in match.context.context.value['format']:
            list_extension.append(file_ext['file-extension'])

        list_type.append({match.value: list_extension})

    return {"type": list_type}


@app.get('/dans-formats')
def retrieve_dans_formats():
    logging.info("Type registry service")
    logging.debug("info")

    return data['dans_formats']


@app.post('/dans-formats/refresh', dependencies=[Depends(api_key_auth)])
def refresh_dans_formats():
    url_resp = requests.get(settings.DANS_FORMATS_URL)
    if url_resp.status_code == 200:
        data.clear()
        data.update({'dans_formats': url_resp.json()})
        return data

    else:
        return HTTPException(400, f"Response status code '{url_resp.status_code}' from '{settings.DANS_FORMATS_URL}'")


if __name__ == "__main__":
    logging.info("Start")

    uvicorn.run("src.main:app", host="0.0.0.0", port=2023, reload=False)
