import requests
import asyncio
from urllib.error import HTTPError

from datetime import datetime

import logging
LOGGER = logging.getLogger('DartsLive')

import json, os

dir_path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(dir_path, 'user.json')) as json_file:
    data = json.load(json_file)

TEMPTIME_RES_COUNT = 385652305

class Dartslive(object):
    def __init__(self, email, password) -> None:
        self._session = requests.Session()
        self._email = email
        self._password = password
        self._response = ''
        self._accessKey = ''
        self._accountId = 0
        self._playerId = 0
        self._missionClear = {}
        self._checkDLAuthURL="https://homeapi.dartslive.com/dlhome/action.jsp?actionid=checkDLAuth"
        self._getPlayerURL="https://homeapi.dartslive.com/dlhome/action.jsp?actionid=getPlayer"
        self._healthCheckURL="https://homeapi.dartslive.com/dlhome/action.jsp?actionid=healthCheck"
        self._getAccountMenuURL="https://homeapi.dartslive.com/dlhome/action.jsp?actionid=getAccountMenu"
        self._gameStart="https://homeapi.dartslive.com/dlhome/action.jsp?actionid=gameStart"
        self._gameEnd="https://homeapi.dartslive.com/dlhome/action.jsp?actionid=gameEnd"
    
    def oepn_jsonfile(self, filename):
        data = {}
        dir_path = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(dir_path+'/game_template', filename)) as json_file:
            data = json.load(json_file)

        return data

    def get_timenow(self):
        return int(datetime.timestamp(datetime.now()) * TEMPTIME_RES_COUNT)

    async def post(self, url, data={}):
        try:
            response = self._session.post(url, json=data)
            response.raise_for_status()
        except HTTPError as http_err:
            LOGGER.info(f'HTTP error occurred: {http_err}')
            return False
        except Exception as err:
            LOGGER.info(f'Other error occurred: {err}')
            return False
        else:
            await asyncio.sleep(int(2))
            self._response = response.json()
            return True

    async def login(self):
        jsondata = self.oepn_jsonfile('checkDLAuth_request.json')
        jsondata['res_count'] = self.get_timenow()
        jsondata['mail'] = self._email
        jsondata['password'] = self._password

        # Login
        if await self.post(self._checkDLAuthURL, jsondata):
            self._accessKey = self._response['accessKey']
            self._accountId = self._response['accountId']
        else:
            LOGGER.error('Login Error')
            return False

        jsondata = self.oepn_jsonfile('getPlayer_request.json')
        jsondata['res_count'] = self.get_timenow()
        jsondata['account_id'] = self._accountId
        jsondata['access_key'] = self._accessKey
        # PlayerId
        if await self.post(self._getPlayerURL, jsondata):
            # get first player
            self._playerId = self._response['player'][0]['id']
        else:
            LOGGER.error('PlayerId Error')
            return False

        return True

    async def startgame(self, startfilename:str, endfilename:str, gamename:str):
        jsondataStartGame = self.oepn_jsonfile(startfilename)
        jsondataStartGame['res_count'] = self.get_timenow()
        jsondataStartGame['account_id'] = self._accountId
        jsondataStartGame['access_key'] = self._accessKey
        jsondataStartGame['playerInfoList'][0]['pid'] = self._playerId

        if await self.post(self._gameStart, jsondataStartGame):
            if self._response['error'] == '':
                LOGGER.info('Start '+gamename+', wait 10s')
                await asyncio.sleep(10)
                
                jsondataEndGame = self.oepn_jsonfile(endfilename)
                jsondataEndGame['res_count'] = self.get_timenow()
                jsondataEndGame['account_id'] = self._accountId
                jsondataEndGame['access_key'] = self._accessKey
                jsondataEndGame['stats_list'][0]['pid'] = self._playerId

                if await self.post(self._gameEnd, jsondataEndGame):
                    if self._response['error'] == '':
                        self._missionClear[gamename] = self._response['missionClear']
                        LOGGER.info('Over, MissionClear:'+str(self._response['missionClear']))
            else:
                LOGGER.error('Start Fail, message:'+str(self._response['error']))

    async def playgame(self):
        # 301
        await self.startgame('301_start.json', '301_end.json', '301')
        # 501
        await self.startgame('501_start.json', '501_end.json', '501')
        # 701
        await self.startgame('701_start.json', '701_end.json', '701')
        # cricket
        await self.startgame('cricket_start.json', 'cricket_end.json', 'cricket')
        # count-up
        await self.startgame('countup_start.json', 'countup_end.json', 'count-up')
