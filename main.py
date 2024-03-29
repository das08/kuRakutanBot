import random

import module
import setting  # TODO: デプロイ時コメントアウト

from flask import Flask, request, abort
from pymongo import MongoClient
import os
import sys
import re
import json
import datetime
import math
import copy
import unicodedata
import urllib
import urllib.parse
import requests
import socket
import requests.packages.urllib3.util.connection as urllib3_cn
from requests.exceptions import Timeout
import mojimoji
import uuid

from module.gmail import Gmail

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage, PostbackEvent
)

app = Flask(__name__)

# ##### SETTINGS ##### #
VERSION = "5.0.0"
UPDATE_DATE = "2021.09.22"
color_theme = ""

THIS_YEAR = 2021
RAKUTAN_COLLECTION = "rakutan2021"
ENABLE_TWEET_SHARE = True

if ENABLE_TWEET_SHARE:
    rakutan_json_filepath = 'rakutan_detail_tweet.json'
else:
    rakutan_json_filepath = 'rakutan_detail.json'

# #################### #


# 環境変数取得
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
ADMIN_UID = os.environ["ADMIN_UID"]
mongo_host = os.environ["mongo_host"]
mongo_port = os.environ["mongo_port"]
mongo_user = os.environ["mongo_user"]
mongo_pass = os.environ["mongo_pass"]
mongo_db = os.environ["mongo_db"]

normal_menu = os.environ["normal_menu"]
silver_menu = os.environ["silver_menu"]
gold_menu = os.environ["gold_menu"]

kuwiki_api_endpoint = os.environ["kuwiki_api"]
kuwiki_api_token = os.environ["kuwiki_token"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


class LoadJSON(object):
    """
    Load json files.
    """

    def __init__(self, data):
        if type(data) is str:
            data = json.loads(data)
        self.from_dict(data)

    def from_dict(self, data):
        self.__dict__ = {}
        for key, value in data.items():
            if type(value) is dict:
                value = LoadJSON(value)
            self.__dict__[key] = value

    def to_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if type(value) is LoadJSON:
                value = value.to_dict()
            data[key] = value
        return data

    def __repr__(self):
        return str(self.to_dict())

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]


class DB:
    """
    Connect to postgresql database on Heroku.
    +---------+-------------+-------------+-----------+-----------+-------------+------------+-----+-----------+
    | ID      | facultyname | lecturename | groups    | credits   | accept_prev | total_prev | ... | url       |
    | (int)   | (varchar)   | (varchar)   | (varchar) | (varchar) | (int)       | (int)      |     | (varchar) |
    +---------+-------------+-------------+-----------+-----------+-------------+------------+-----+-----------+
    | primary |             |             |           |           |             |            |     |           |
    +---------+-------------+-------------+-----------+-----------+-------------+------------+-----+-----------+
    groups: 群
    credits: 単位数
    accept_...: # of people accepted
    total...: # of people registered
        prev: data of a year ago
        prev2: data of two years ago
        prev3: data of three years ago
    url: Link to kakomon page (if any)
    Fetched and stored data from following page.
    http://www.kyoto-u.ac.jp/contentarea/ja/about/publication/publish-education/documents/2019/10-1.pdf
    """

    def __init__(self):
        self.columnNameRakutan = ['id', 'facultyname', 'lecturename', 'groups', 'credits', 'total_prev', 'accept_prev',
                                  'total_prev2', 'accept_prev2', 'total_prev3', 'accept_prev3', 'url']
        self.columnNameFav = ['lectureid', 'lecturename']

    def connect(self):
        """Connect to mongo database"""
        uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}"
        client = MongoClient(uri)
        return client

    def get_by_id(self, conn, search_id):
        """Get lecture info that matches lecture id"""
        try:
            collection = conn[RAKUTAN_COLLECTION]
            rakutan_data = {}

            query = {'id': int(search_id)}
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            if count > 0:
                mes = "success"
            else:
                mes = "そのIDは存在しません。"

            # set value to rakutan_data
            for row in results:
                rakutan_data = row

            return mes, rakutan_data

        except:
            stderr(f"[error]get-by-id:Cannot #{search_id}")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"

    def get_query_result(self, conn, search_word, original_search_word):
        """Get lecture list that matches search_word"""
        try:
            rakutan_data = {}
            temp_list = []
            collection = conn[RAKUTAN_COLLECTION]

            if search_word[0] == '%':
                query = {'lecturename': {'$regex': f'{original_search_word[1:]}', '$options': 'i'}}
            else:
                query = {'lecturename': {'$regex': f'^{original_search_word}', '$options': 'i'}}

            results = collection.find(filter=query, projection={'_id': False})
            count = collection.count_documents(filter=query)

            if count > 0:
                mes = "success"
            else:
                mes = f"「{original_search_word}」は見つかりませんでした。\n【検索のヒント】\n%を頭に付けて検索すると部分一致検索になります。デフォルトは前方一致検索です。"
            for row in results:
                temp_list.append(row)

            # set value to rakutan_data
            for column in self.columnNameRakutan:
                rakutan_data[column] = [row[column] for row in temp_list]

            return mes, rakutan_data
        except:
            stderr(f"[error]get-query-result:Cannot {search_word}")
            return "DB接続エラーです", "exception"

    def get_userfav(self, conn, uid, lectureID="", types=""):
        """
        Get favorite list.
        types = "count" -> Get number of favs.
        types = "" -> Check if user has faved specific lecture.
        """
        try:
            fav_list = {}
            temp_list = []
            collection = conn['userfav']

            if types == "count":
                query = {'uid': uid}
            else:
                query = {'$and': [{'uid': uid}, {'lectureid': int(lectureID)}]}

            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            if count > 0:
                mes = "already"
            else:
                mes = "notyet"
            if types == "count":
                for row in results:
                    temp_list.append(row)

                # set value to fav_list
                for column in self.columnNameFav:
                    fav_list[column] = [row[column] for row in temp_list]
                mes = fav_list
            return mes
        except:
            stderr(f"[error]get-userfav:Cannot {lectureID}")
            return "error"

    def get_merge_list(self, conn):
        """Get merge list. (NOT WORKING!)"""
        lecture_name = []
        lecture_id = []
        lecture_url = []
        try:
            collection = conn['urlmerge']

            query = {'search_id': {'$ne': ''}}
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            if count > 0:
                mes = "success"
                for row in results:
                    search_id = row['search_id']
                    url = row['url']

                    get_lecture = self.get_by_id(conn, search_id)[1]['lecturename']
                    lecture_id.append(search_id)
                    lecture_name.append(get_lecture)
                    lecture_url.append(url)
            else:
                mes = "error"
            return mes, lecture_id, lecture_name, lecture_url
        except:
            stderr("[error]fetch-merge-list:Cannot fetch from DB")
            return "DB接続エラーです", "exception"

    def get_omikuji(self, conn, types):
        """
        Get omikuji
        types = "normal" -> Get rakutan(easy) omikuji.
        types = "shrine" -> Get jinsha(humanities and social science) omikuji.
        types = "" -> Get onitan(difficult) omikuji.
        """
        try:
            collection = conn[RAKUTAN_COLLECTION]

            if types == "normal":
                query = {'$and': [{'facultyname': '国際高等教育院'}, {'accept_prev': {'$gt': 15}},
                                  {'$expr': {'$gt': ['$accept_prev', {'$multiply': [0.76, '$total_prev']}]}}]}
            elif types == "shrine":
                query = {'$and': [{'groups': '人社'}, {'accept_prev': {'$gt': 15}},
                                  {'$expr': {'$gt': ['$accept_prev', {'$multiply': [0.7, '$total_prev']}]}}]}
            else:
                query = {'$and': [{'facultyname': '国際高等教育院'}, {'total_prev': {'$gt': 4}},
                                  {'$expr': {'$lt': ['$accept_prev', {'$multiply': [0.31, '$total_prev']}]}}]}

            results = collection.find(filter=query, projection={'id': True})

            omikujiID = random.choice([row['id'] for row in results])

            stderr(f"[success]omikuji:Omikuji {types}!")

            return 'success', omikujiID
        except:
            stderr("[error]omikuji:Cannot get omikuji.")
            return "DB接続エラーです", "exception"

    def add_to_db(self, conn, uid, types, lectureID="", lectureName=""):
        """Add something to database"""
        try:
            dates = str(datetime.datetime.now()).replace('.', '/')
            if types == "uid":
                collection = conn['usertable']
                query = {'uid': uid, 'rich_menu': 'main', 'color_theme': 'default', 'register_time': dates}

            elif types == "fav":
                collection = conn['userfav']
                res = self.get_userfav(conn, uid, lectureID)
                if res == "already":
                    return "already"
                query = {'uid': uid, 'lectureid': int(lectureID), 'lecturename': lectureName}

            elif types == "ver":
                collection = conn['verification']
                query = {'uid': uid, 'code': lectureID}

            else:
                return "invalid types"

            results = collection.insert(query)

            return 'success'
        except:
            stderr("[error]addDB:Cannnot add to usertable/userfav.")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"

    def update_db(self, conn, uid, value="", types=""):
        """Update something on database"""
        try:
            count = 0
            if types == "count":
                collection = conn['usertable']
                result = collection.find_one_and_update({'uid': uid}, {'$inc': {'count': 1}})
                count = int(result['count'])
            elif types == "theme":
                collection = conn['usertable']
                collection.update({'uid': uid}, {'$set': {'color_theme': value}})
            elif types == "url":
                collection = conn[RAKUTAN_COLLECTION]
                collection.update({'id': int(uid)}, {'$set': {'url': value}})
            elif types == "ver":
                collection = conn['usertable']
                collection.update({'uid': uid}, {'$set': {'verified': int(value)}})
            return 'success', count
        except:
            stderr(f"[error]updateDB:Cannnot update [{types}].")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"

    def counter(self, conn, uid, types=""):
        """Counter for specific commands."""
        columnName = {'info': 'info', 'normalomikuji': 'normalomikuji', 'oniomikuji': 'oniomikuji', 'fav': 'fav',
                      'icon': 'icon', 'help': 'help'}
        try:
            collection = conn['counter']
            collection.find_one_and_update({'uid': uid}, {'$inc': {columnName[types]: 1}}, upsert=True)
            return 'success'
        except:
            stderr("[error]counter:Cannnot update counter")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"

    def delete_db(self, conn, search_id, uid="", types="", url=""):
        try:
            if types == "fav":
                query = {'$and': [{'uid': uid}, {'lectureid': int(search_id)}]}
                collection = conn['userfav']
            elif types == "ver":
                query = {'uid': uid}
                collection = conn['verification']
            else:
                # query = {'$and': [{'search_id': int(search_id)}, {'url': url}]}
                query = {'search_id': int(search_id)}
                collection = conn['urlmerge']

            results = collection.remove(query)

            return 'success'
        except:
            stderr("[error]deleteDB:Cannnot delete urlmarge/userfav.")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"

    def add_to_mergelist(self, conn, received_message, uid):
        """Add kakomon url to merge-waiting-list"""
        dates = str(datetime.datetime.now()).replace('.', '/')
        search_id = received_message[2:7]
        url = received_message[8:].strip()
        try:
            collection = conn['urlmerge']
            query = {'search_id': int(search_id), 'url': url, 'uid': uid, 'send_time': dates}

            results = collection.insert(query)

            return 'success'
        except:
            stderr("[error]kakomon-merge:Cannot insert.")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"

    def isinDB(self, conn, uid):
        """Check if user is registered in database"""
        verified = False
        try:
            collection = conn['usertable']
            query = {'uid': uid}
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            if count > 0:
                for row in results:
                    color_theme = row['color_theme']
                    if 'verified' in row and row['verified'] == 1:
                        verified = True
            else:
                self.add_to_db(conn, uid, "uid")
                color_theme = "default"

            return True, color_theme, verified
        except:
            stderr(f"[error]isinDB:Cannnot isin {uid}")
            color_theme = "default"
            return False, color_theme, verified

    def verification(self, conn, verificationCode):
        status = False
        try:
            collection = conn['verification']
            query = {'code': '{}'.format(verificationCode)}
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)
            uid = ""

            if count > 0:
                for row in results:
                    uid = row['uid']
                    self.update_db(conn, uid, 1, "ver")
                    self.delete_db(conn, 0, uid=uid, types="ver")
                    status = True

            return status
        except:
            stderr(f"[error]isinDB:Cannnot verify")
            return False


class KUWiki:
    def __init__(self):
        # Use ipv4 for kuwiki api
        urllib3_cn.allowed_gai_family = self.allowed_gai_family

    def allowed_gai_family(self):
        """
         https://github.com/shazow/urllib3/blob/master/urllib3/util/connection.py
        """
        family = socket.AF_INET
        return family

    def convertText(self, text):
        text = text[::-1]
        text = text.replace('Ⅰ', '1', 1)
        text = text.replace('Ⅱ', '2', 1)
        text = text.replace('Ⅲ', '3', 1)
        text = text.replace('Ⅳ', '4', 1)
        text = text.replace('Ⅴ', '5', 1)
        text = text.replace('Ⅵ', '6', 1)
        text = text.replace('Ⅶ', '7', 1)
        text = text.replace('Ⅷ', '8', 1)
        # 順番大事かつreverseに注意
        text = text.replace('IIIV', '8', 1)
        text = text.replace('IIV', '7', 1)
        text = text.replace('VI', '4', 1)
        text = text.replace('IV', '6', 1)
        text = text.replace('V', '5', 1)
        text = text.replace('III', '3', 1)
        text = text.replace('II', '2', 1)
        text = text.replace('I', '1', 1)
        text = text.replace('･', '・')
        text = text.replace('（', '(')
        text = text.replace(')', ')')

        # text = text.replace('１', '1', 1)
        # text = text.replace('２', '2', 1)
        # text = text.replace('３', '3', 1)
        # text = text.replace('４', '4', 1)
        # text = text.replace('５', '5', 1)
        # text = text.replace('６', '6', 1)
        # text = text.replace('７', '7', 1)
        # text = text.replace('８', '8', 1)

        text = text[::-1]
        return text

    def rConvertText(self, text):
        text = text.replace('1', 'I', 1)
        text = text.replace('2', 'II', 1)
        text = text.replace('3', 'III', 1)
        text = text.replace('4', 'IV', 1)
        text = text.replace('5', 'V', 1)
        text = text.replace('6', 'VI', 1)
        text = text.replace('7', 'VII', 1)
        text = text.replace('8', 'VIII', 1)

        text = text.replace('・', '･')

        text = mojimoji.han_to_zen(text)
        text = text.replace('（', '(')
        text = text.replace(')', ')')

        text = text.replace('ＶＩＩＩ', 'VIII', 1)
        text = text.replace('ＶＩＩ', 'VII', 1)
        text = text.replace('ＶＩ', 'VI', 1)
        text = text.replace('ＩＩＩ', 'III', 1)
        text = text.replace('ＩＩ', 'II', 1)
        text = text.replace('ＩＶ', 'IV', 1)
        text = text.replace('Ｖ', 'V', 1)

        text = text.replace('％', '%', 1)

        return text

    def getKakomonURL(self, lectureName, oldKakomon):
        kakomonURL = []
        lectureCount = 0
        isFromKuWiki = False
        # print("before",lectureName)
        lectureName = self.convertText(lectureName)
        # print("after", lectureName)
        try:
            header = {"Authorization": 'Token {}'.format(kuwiki_api_token)}
            param = {"name": lectureName}
            res = requests.get('{}/course/'.format(kuwiki_api_endpoint), headers=header, params=param, timeout=1.5)
            res_json = res.json()
            # print(res_json)
            if 'count' in res_json:lectureCount = res_json['count']
            isZengaku = True

            # iterate all possible lecture
            for i in range(lectureCount):
                # complete match
                if res_json['results'][i]['name'] == lectureName:
                    examCount = res_json['results'][i]['exam_count']
                    if res_json['results'][i]['field'][:2] != "全学": isZengaku = False

                    # append kakomon URL to list
                    for j in range(examCount):
                        if isZengaku:
                            kakomonURL.append(res_json['results'][i]['exam_set'][j]['drive_link'])
                            isFromKuWiki = True

            if not isZengaku and oldKakomon:
                kakomonURL.append(oldKakomon)
            # もし一致件数0の時（apiの不具合等）
            if lectureCount == 0 and oldKakomon:
                kakomonURL.append(oldKakomon)

        except json.JSONDecodeError:
            pass
        except Timeout:
            pass

        return kakomonURL, isFromKuWiki


class Prepare:
    """
    Prepares json file for sending flex message.
    """

    def __init__(self, received_message="", token=""):
        self.received_message = received_message
        self.token = token
        self.json_content = {}
        self.json_contents = []

    def rakutan_detail(self, array, fav="notyet", color="", omikuji="", verified=False):
        """
        Rakutan detail for a specific lecture.
        Inside this function, json file for flex message is generated.
        :param verified:
        :param fav:
        :param omikuji:
        :param array: lecture data from db
        :param color: FOR fn.omikuji
        :return: json_content
        """
        print(array["lecturename"])
        if color != "":
            f = open(f'./theme/{color}/{rakutan_json_filepath}', 'r', encoding='utf-8')
        else:
            f = open(f'./theme/{color_theme}/{rakutan_json_filepath}', 'r', encoding='utf-8')

        # load template
        data = json.dumps(json.load(f))
        self.json_content = LoadJSON(data)

        # modify header
        header_contents = self.json_content.header.contents

        if fav == "already":
            header_contents[0]['contents'][0][
                'url'] = "https://scdn.line-apps.com/n/channel_devcenter/img/fx/review_gold_star_28.png"
            # header_contents[0]['contents'][0]['action']['displayText'] = f"「{array['lecturename']}」をお気に入り解除しました！"
        # else:
        #     header_contents[0]['contents'][0]['action']['displayText'] = f"「{array['lecturename']}」をお気に入り登録しました！"
        header_contents[0]['contents'][0]['action'][
            'data'] = f"type=fav&id={array['id']}&lecname={array['lecturename']}"

        header_contents[0]['contents'][1]['text'] = f"Search ID: #{array['id']}"
        header_contents[1]['text'] = f"{array['lecturename']}"
        header_contents[3]['contents'][1]['text'] = str(array['facultyname'])
        header_contents[4]['contents'][1]['text'] = str(self.isSet(array['groups']))
        header_contents[4]['contents'][3]['text'] = str(self.isSet(array['credits']))

        # for omikuji
        if omikuji == "normal":
            header_contents[0]['contents'][1]['text'] = "楽単おみくじ結果"
            header_contents[0]['contents'][1]['color'] = "#ff7e41"
        elif omikuji == "oni":
            header_contents[0]['contents'][1]['text'] = "鬼単おみくじ結果"
            header_contents[0]['contents'][1]['color'] = "#6d7bff"
        elif omikuji == "shrine":
            header_contents[0]['contents'][1]['text'] = "人社おみくじ結果"
            header_contents[0]['contents'][1]['color'] = "#cc913e"

        # adjust font size if too long
        length = self.lecturename_len(array['lecturename'])
        if length > 24:
            self.json_content.header.contents[1]['size'] = 'lg'
        elif length > 18:
            self.json_content.header.contents[1]['size'] = 'xl'

        # modify body
        body_contents = self.json_content.body.contents
        for year in range(1, 4):  # [1, 3] inclusive
            if year == 1:
                _year = ""
            else:
                _year = str(year)
            body_contents[0]['contents'][year]['contents'][0]['text'] = '{}年度'.format(THIS_YEAR - year)
            body_contents[0]['contents'][year]['contents'][1]['text'] = '{}% ({}/{})'.format(
                self.cal_percentage(array[f'accept_prev{_year}'], array[f'total_prev{_year}']),
                self.isSet(array[f'accept_prev{_year}']), self.isSet(array[f'total_prev{_year}']))

        # rakutan judge
        rakutan_percent = self.rakutan_percentage(array)
        percent = [90, 85, 80, 75, 70, 60, 50, 0]
        judge = ['SSS', 'SS', 'S', 'A', 'B', 'C', 'D', 'F']
        judge_color = ['#c3c45b', '#c3c45b', '#c3c45b', '#cf2904', '#098ae0', '#f48a1c', '#8a30c9', '#837b8a']
        judge_list_data = {k: (v1, v2) for k, v1, v2 in zip(percent, judge, judge_color)}
        judgeSymbol = "---"
        for key, value in judge_list_data.items():
            if rakutan_percent >= key:
                judgeSymbol = value[0]
                judge_view = body_contents[0]['contents'][5]['contents'][1]
                judge_view['text'] = f"{judgeSymbol}　"
                judge_view['color'] = f"{value[1]}"
                break
        # modify url
        kakomon_header = body_contents[0]['contents'][6]['contents'][0]
        kakomon_symbol = body_contents[0]['contents'][6]['contents'][1]
        kakomon_link = body_contents[0]['contents'][6]['contents'][2]

        if array['url']:
            kakomon_symbol['text'] = '〇'
            kakomon_symbol['color'] = '#0fd142'

            kakomon_link['text'] = 'リンク'
            kakomon_link['color'] = '#4c7cf5'
            kakomon_link['decoration'] = 'underline'
            kakomon_link['action']['uri'] = array['url'][0]
            if len(array['url']) > 1:
                kakomon_link2 = kakomon_link.copy()
                kakomon_link2['text'] = 'リンク2'
                kakomon_link2['color'] = '#4c7cf5'
                kakomon_link2['decoration'] = 'underline'
                kakomon_link2['action']['uri'] = array['url'][1]
                body_contents[0]['contents'][6]['contents'].append(kakomon_link2)
            if array['kuWiki']:
                kakomon_header['text'] += '\n(京大wiki提供)'


        else:
            url_provide_template = {"type": "uri", "label": "action", "uri": "https://www.kuwiki.net/volunteer"}
            kakomon_symbol['text'] = '×'
            kakomon_symbol['color'] = '#ef1d2f'
            kakomon_link['action'] = url_provide_template
            kakomon_link['text'] = '追加する'

        if not verified:
            url_provide_template = {"type": "message", "label": "action", "text": "ユーザ認証"}
            kakomon_symbol['flex'] = 0
            kakomon_symbol['text'] = '△'
            kakomon_symbol['color'] = '#ffb101'
            kakomon_link['action'] = url_provide_template
            kakomon_link['flex'] = 7
            kakomon_link['text'] = 'ユーザー認証が必要です'

        if ENABLE_TWEET_SHARE:
            # make KKK shorter
            if array['facultyname'] == "国際高等教育院":
                facultyName = "般教"
            else:
                facultyName = array['facultyname']

            # adjust search type
            if omikuji == "normal":
                types = "rakutan"
            elif omikuji == "oni":
                types = "onitan"
            elif omikuji == "shrine":
                types = "jinsha"
            else:
                types = "normal"

            urlParam = f"gen?lecname={array['lecturename']}&facname={facultyName}&judge={judgeSymbol}&type={types}"
            for year in range(1, 4):  # [1, 3] inclusive
                if year == 1:
                    _year = ""
                else:
                    _year = str(year)
                urlParam += f"&a{year}={array[f'accept_prev{_year}']}&s{year}={array[f'total_prev{_year}']}"

            param = urllib.parse.quote(urlParam, safe="=&?")

            tweet_share_uri = body_contents[0]['contents'][7]['contents'][1]
            tweet_share_uri['action']['uri'] = f"https://ku-rakutan.das82.com/{param}"

        return [self.json_content]

    def search_result(self, array, search_text, record_count):
        """
        Display all possible lecturename list.
        Inside this function, json file for flex message is generated.
        :param array: list of lecture data from db (must be below 100)
        :param search_text: search text
        :param record_count: count
        :return: json_content
        """
        facultyNameAbbr = {'文学部': '文', '教育学部': '教', '法学部': '法', '経済学部': '経', '理学部': '理', '医学部': '医医',
                           '医学部（人間健康科学科）': '人健', '医学部(人間健康科学科)': '人健',
                           '薬学部': '薬', '工学部': '工', '農学部': '農', '総合人間学部': '総人', '国際高等教育院': '般教'}
        colorCode = {'default': '#4c7cf5', 'yellow': '#D17A22'}
        processed_count = 0
        number_of_pages = math.ceil(record_count / 20)

        # load templates
        # f: first page flex message
        f = open(f'./theme/{color_theme}/search_result.json', 'r', encoding='utf-8')
        f_data = json.dumps(json.load(f))
        # g: second page~ flex message
        g = open(f'./theme/{color_theme}/search_result_more.json', 'r', encoding='utf-8')
        g_data = json.dumps(json.load(g))

        # put all pages into json_contents list
        self.json_contents.append(LoadJSON(f_data))
        for _ in range(number_of_pages - 1):
            self.json_contents.append(LoadJSON(g_data))

        # header text for first page
        self.json_contents[0]['header']['contents'][1]['text'] = f"{record_count} 件の候補が見つかりました。目的の講義を選択してください。"

        # generate list for each page
        for i in range(1, number_of_pages + 1):
            self.json_contents[i - 1]["header"]["contents"][0][
                "text"] = f"「{search_text}」の検索結果 ({i}/{number_of_pages}) "

            json_lecture_row = []
            # 20 lecturename lists per page
            for j in range(20):
                if processed_count == record_count:
                    break

                # template for lecturename row
                socket = {'type': 'box', 'layout': 'horizontal',
                          'contents': [
                              {'type': 'text', 'text': '[Lecture Name]', 'size': 'sm', 'color': '#555555', 'flex': 10},
                              {'type': 'text', 'text': '選択', 'size': 'md', 'color': '#4c7cf5', 'align': 'end',
                               'weight': 'bold',
                               'decoration': 'underline', 'margin': 'none',
                               'action': {'type': 'message', 'label': 'action', 'text': '#[Lecture ID]'},
                               'offsetBottom': '3px',
                               'flex': 2}], 'margin': 'lg'}
                socket['contents'][1]['color'] = colorCode[color_theme]
                socket['contents'][0][
                    'text'] = f"[{facultyNameAbbr[array['facultyname'][processed_count]]}]{array['lecturename'][processed_count]}"
                socket["contents"][1]['action']['text'] = '#' + str(array['id'][processed_count])

                # add row to the page
                json_lecture_row.append(socket.copy())
                processed_count += 1

            # overwrite old page with new one
            self.json_contents[i - 1]["body"]["contents"][1]["contents"] = json_lecture_row

        return self.json_contents

    def isID(self, text):
        """Check if received text is in ID-format or not. Has to start with sharp."""
        if len(text) == 6 and (text[0] == "#" or text[0] == "＃") and text[1:5].isdigit():
            return True

    def isURLID(self, text):
        """Check if received text is in URLID-format or not. Has to start and end with brackets and include sharp-id."""
        if text[0] == "[" and (text[1] == "#" or text[1] == "＃") and text[7] == "]" and text[2:7].isdigit():
            return True

    def isURL(self, text):
        """Check if received url is in URL-format or not. Has to start with http:// or https://"""
        # regex for judging URL format.
        pattern = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
        url = text[8:].strip()
        # judge if is in correct url-format.
        if re.match(pattern, url):
            return True
        else:
            return False

    def isEmptyURL(self, text):
        """Check if received url is in Empty-URL-format or not. Has to be 'None'"""
        url = text[8:].strip()
        if url == "None" or url == "none":
            return True
        else:
            return False

    def isSet(self, value):
        """Return '---' if value is empty string."""
        if value == "":
            return '---'
        else:
            return value

    def isStudentAddress(self, value):
        return re.match('[A-Za-z0-9\._+]+@st\.kyoto-u\.ac\.jp', value) is not None

    def isOtherAddress(self, value):
        return re.match('[A-Za-z0-9\._+]+@[A-Za-z]+\.[A-Za-z]', value) is not None

    def list_to_str(self, array):
        """
        Removes list bracket in value.
        :param array: single-element list
        :return: new list w/ no brackets
        """
        new_array = {}
        for key, value in array.items():
            new_array[key] = value[0]
        return new_array

    def cal_percentage(self, accepted, total):
        """Calculates percentage. Return '---' if div/0"""
        if total == 0:
            return '---'
        else:
            return round(100 * accepted / total, 1)

    def rakutan_percentage(self, array):
        """Return percentage for judging rakutan"""
        if array['total_prev'] != 0:
            percent = round(100 * array['accept_prev'] / array['total_prev'], 1)
        elif array['total_prev2'] != 0:
            percent = round(100 * array['accept_prev2'] / array['total_prev2'], 1)
        else:
            percent = round(100 * array['accept_prev3'] / array['total_prev3'], 1)
        return percent

    def lecturename_len(self, text):
        """Find length of lecturename based on unicode bites"""
        length = 0
        for c in text:
            if unicodedata.east_asian_width(c) in 'FWA':
                length += 2
            else:
                length += 1
        return length

    def merge_url(self, lecture_id, lecture_name, lecture_url):
        """FOR ADMIN. Prepares flex message for merging/declining kakomon url."""
        f = open(f'./theme/etc/merge.json', 'r', encoding='utf-8')
        json_content = json.load(f)

        # store all rows
        chunk = []

        for (lec_id, lec_name, lec_url) in zip(lecture_id, lecture_name, lecture_url):
            socket = json_content['body']['contents'][0]
            socket['contents'][1]['text'] = f"[#{lec_id}] {lec_name}"
            socket['contents'][2]['text'] = lec_url
            socket['contents'][2]['action']['uri'] = lec_url
            socket['contents'][3]['contents'][0]['action']['data'] = f"type=merge&id={str(lec_id)}&url={lec_url}"
            socket['contents'][3]['contents'][1]['action']['data'] = f"type=decline&id={str(lec_id)}&url={lec_url}"
            if lec_url == "None" or lec_url == "none":
                socket['contents'][2]['action']['uri'] = "https://none.com"
            chunk.append(copy.deepcopy(socket))

        json_content['body']['contents'] = chunk

        return json_content


class Send:
    def __init__(self, token):
        self.token = token

    def send_result(self, json_content, search_text="", types=" "):
        """
        Sends search result with flex message.
        json_content MUST BE LIST.
        :param json_content: List: flex template
        :param search_text: str: ONLY for displaying search_result
        :param types: str: switch alt text
        :return: Nothing
        """
        content = []
        page_count = 1
        alt_text = types
        max_page_count = len(json_content)
        for page in json_content:
            # setting up alt text
            if types == "search_result":
                alt_text = f"({page_count}/{max_page_count})「{search_text}」の検索結果"
            elif types == "rakutan_detail":
                # fetching lecturename from json_content
                alt_text = f"「{page['header']['contents'][1]['text']}」のらくたん情報"
            elif types == "omikuji":
                alt_text = search_text

            # make it json format
            try:
                page = json.dumps(page.to_dict())
            except:
                page = json.dumps(page)

            flex_message = FlexSendMessage(
                alt_text=alt_text,
                contents=json.loads(page)
            )
            content.append(flex_message)
            page_count += 1

        line_bot_api.reply_message(self.token, messages=content)

    def send_fav(self, json_content, search_text, types):
        content = []
        page_count = 1
        alt_text = types
        max_page_count = len(json_content)
        for page in json_content:
            # setting up alt text
            if types == "search_result":
                alt_text = f"({page_count}/{max_page_count})「{search_text}」の検索結果"
            elif types == "rakutan_detail":
                # fetching lecturename from json_content
                alt_text = f"「{page['header']['contents'][1]['text']}」のらくたん情報"
            elif types == "omikuji":
                alt_text = search_text

            # make it json format
            try:
                page = json.dumps(page.to_dict())
            except:
                page = json.dumps(page)

            flex_message = FlexSendMessage(
                alt_text=alt_text,
                contents=json.loads(page)
            )
            content.append(flex_message)
            page_count += 1

        line_bot_api.reply_message(self.token, messages=content)

    def send_text(self, message):
        """Sends plain text."""
        line_bot_api.reply_message(
            self.token,
            TextSendMessage(text=message),
        )

    def send_multiline_text(self, message_list):
        """Sends multiline text."""
        message = []
        for row in message_list:
            mes = TextSendMessage(text=row)
            message.append(mes)

        line_bot_api.reply_message(
            self.token,
            messages=message
        )

    def push_text(self, message):
        """Sends push text."""
        line_bot_api.push_message(
            ADMIN_UID,
            TextSendMessage(text=message),
        )


def stderr(err_message):
    print(err_message)
    sys.stdout.flush()


@app.route("/")
def hello_world():
    return "hello world!"


@app.route("/wakeandpush")
def push_flex():
    prepare = Prepare()
    db = DB()
    with db.connect() as client:
        conn = client[mongo_db]
        result = db.get_merge_list(conn)

    if result[0] == 'success':
        lecture_id = result[1]
        lecture_name = result[2]
        lecture_url = result[3]
        json_content = prepare.merge_url(lecture_id, lecture_name, lecture_url)
        flex_message = FlexSendMessage(
            alt_text="過去問提供URL確認",
            contents=json_content
        )
        line_bot_api.push_message(
            ADMIN_UID,
            messages=flex_message
        )
    return "end"


@app.route("/verification", methods=['GET'])
def verify_user():
    verificationCode = request.args.get('code', '')
    db = DB()
    mes = "すでに認証済みか、認証コードが間違っています。"
    with db.connect() as client:
        conn = client[mongo_db]
        status = db.verification(conn, verificationCode)
    if status:
        mes = "認証に成功しました。"

    return mes


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# Handle Text message
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global color_theme

    token = event.reply_token
    uid = event.source.user_id
    received_message = event.message.text.strip().replace('％', '%')

    send = Send(token)
    db = DB()
    kuWiki = KUWiki()
    prepare = Prepare(received_message, token)

    with db.connect() as client:
        conn = client[mongo_db]
        check_user = db.isinDB(conn, uid)

        if check_user[0]:
            # add 1 to search counter
            result, count = db.update_db(conn, uid, types='count')
            if result == 'success':
                if count == 20000:
                    line_bot_api.link_rich_menu_to_user(uid, gold_menu)
                elif count == 10000:
                    line_bot_api.link_rich_menu_to_user(uid, gold_menu)
        color_theme = check_user[1]
        verified = check_user[2]

        # load reserved command dict
        response = module.response.command

        if received_message in response:
            # prepare params to pass
            lists = [uid, received_message, color_theme, conn, verified]

            # 1.Check if reserved word is sent.
            response[received_message](token, lists)
        else:
            # 2.Check if student address is sent:
            if prepare.isStudentAddress(received_message):
                if verified:
                    send.send_text("すでに認証済みです。")
                else:
                    verificationCode = uuid.uuid4()
                    db.delete_db(conn, 0, uid=uid, types="ver")
                    db.add_to_db(conn, uid, "ver", '{}'.format(verificationCode))
                    gmail = Gmail(received_message, '{}'.format(verificationCode))
                    res = gmail.sendVerificationCode()
                    if res:
                        send.send_text("認証リンクを送信しました。メール内のリンクをクリックしてください。メールが届かない場合は入力したアドレスが正しいことを確認してください。")
                    else:
                        send.send_text("認証リンクを送信に失敗しました。")

            # 2.Check if other address is sent:
            elif prepare.isOtherAddress(received_message):
                if verified:
                    send.send_text("すでに認証済みです。")
                else:
                    send.send_text("認証は学生アドレスのみ有効です。")


            # 2.Check if kakomon URL is sent:
            elif prepare.isURLID(received_message):
                if prepare.isURL(received_message) or prepare.isEmptyURL(received_message):
                    fetch_result = db.get_by_id(conn, received_message[2:7])
                    if fetch_result[0] == 'success':
                        fetch_result = db.add_to_mergelist(conn, received_message, uid)
                        if fetch_result == 'success':
                            send.send_text("過去問リンクの提供ありがとうございます！確認ができ次第反映されます。")
                        else:
                            send.send_text("DB接続エラーが発生しました。時間を空けてお試しください。")
                    else:
                        send.send_text("指定された講義IDは存在しません。")
                else:
                    send.send_text("過去問リンクは http:// または https:// から始まるものを入力してください。")

            # 3.Check if ID is sent:
            elif prepare.isID(received_message):
                fetch_result = db.get_by_id(conn, received_message[1:6])
                fetch_fav = db.get_userfav(conn, uid, received_message[1:6])
                if fetch_result[0] == 'success':
                    # get lectureinfo list
                    array = fetch_result[1]
                    kakomonURL = []
                    isFromKuWiki = False
                    if verified:
                        kakomonURL, isFromKuWiki = kuWiki.getKakomonURL(mojimoji.zen_to_han(array['lecturename'], kana=False), array["url"])

                    array["url"] = kakomonURL
                    array["kuWiki"] = isFromKuWiki

                    json_content = prepare.rakutan_detail(array, fetch_fav, verified=verified)
                    send.send_result(json_content, received_message, 'rakutan_detail')
                else:
                    send.send_text(fetch_result[0])

            # 4. Check if lecturename is sent:
            else:
                # print("before", received_message)
                # アラビア数字等を変換
                # received_message = kuWiki.rConvertText(received_message)
                # print("after", received_message)
                fetch_result = db.get_query_result(conn, kuWiki.rConvertText(received_message), received_message)
                stderr(f"[success]{uid}: {received_message}")
                if fetch_result[0] == 'success':
                    array = fetch_result[1]
                    record_count = len(array['id'])
                    # if query result is 1:
                    if record_count == 1:

                        array = prepare.list_to_str(array)
                        fetch_fav = db.get_userfav(conn, uid, array['id'])
                        kakomonURL = []
                        isFromKuWiki = False
                        if verified:
                            kakomonURL, isFromKuWiki = kuWiki.getKakomonURL(mojimoji.zen_to_han(array['lecturename'], kana=False),
                                                                            array["url"])

                        array["url"] = kakomonURL
                        array["kuWiki"] = isFromKuWiki

                        json_content = prepare.rakutan_detail(array, fetch_fav, verified=verified)
                        send.send_result(json_content, received_message, 'rakutan_detail')
                    # if query result is over 100:
                    elif record_count > 100:
                        send.send_text(f"「{received_message}」は{record_count}件あります。絞ってください。")
                    # if query result is between 2 and 100:
                    else:
                        json_contents = prepare.search_result(array, received_message, record_count)
                        send.send_result(json_contents, received_message, 'search_result')
                # Send error message(s)
                else:
                    send.send_text(fetch_result[0])


# Handle Postback message
@handler.add(PostbackEvent)
def handle_message(event):
    token = event.reply_token
    uid = event.source.user_id
    received_postback = event.postback.data
    send = Send(token)
    prepare = Prepare("postback", token)
    db = DB()
    kuWiki = KUWiki()

    params = urllib.parse.parse_qs(received_postback)
    types = params.get('type')[0]
    search_id = params.get('id')[0]
    lectureName = params.get('lecname')
    url = params.get('url')
    with db.connect() as client:
        conn = client[mongo_db]
        check_user = db.isinDB(conn, uid)
        verified = check_user[2]

        # process event when user pushes LINK ADD button
        if types == 'url':
            message_list = ["下の講義IDをそのままコピーし、その後ろに続けて過去問URLを貼り付けて送信してください。", f"[#{search_id}]\n"]
            send.send_multiline_text(message_list)

        # process event when user pushes STAR button
        elif types == 'fav':
            res_add = ""
            res_delete = ""
            getFav = db.get_userfav(conn, uid, search_id)

            # if user already faved
            if getFav == "already":
                res_delete = db.delete_db(conn, search_id, uid, 'fav')
                if res_delete == "success":
                    text = f"「{lectureName[0]}」をお気に入りから外しました！"
                else:
                    send.send_text("お気に入りを削除できませんでした。")
            # if user is not faved
            elif getFav == "notyet":
                res_count = db.get_userfav(conn, uid, '12345', "count")
                count = len(res_count)
                if count >= 50:
                    send.send_text("お気に入り登録が上限に達しました。")
                else:
                    res_add = db.add_to_db(conn, uid, 'fav', search_id, lectureName[0])
                    if res_add == "success":
                        text = f"「{lectureName[0]}」をお気に入り登録しました！"
                    else:
                        send.send_text("お気に入りを登録できませんでした。")
            else:
                send.send_text("お気に入り取得中にエラーが発生しました。")

            if res_add == "success" or res_delete == "success":
                fetch_result = db.get_by_id(conn, search_id)
                fetch_fav = db.get_userfav(conn, uid, search_id)
                if fetch_result[0] == 'success':
                    # get lectureinfo list
                    array = fetch_result[1]
                    kakomonURL = []
                    isFromKuWiki = False
                    if verified:
                        kakomonURL, isFromKuWiki = kuWiki.getKakomonURL(mojimoji.zen_to_han(array['lecturename'], kana=False),
                                                                        array["url"])

                    array["url"] = kakomonURL
                    array["kuWiki"] = isFromKuWiki

                    json_content = prepare.rakutan_detail(array, fetch_fav, "default", verified=verified)
                    f = open(f'./theme/etc/singletext.json', 'r', encoding='utf-8')
                    json_text = [json.load(f)]
                    json_text[0]['body']['contents'][0]['text'] = text

                    json_text.append(json_content[0])
                    send.send_result(json_text, 'postback', f"「{lectureName[0]}」のらくたん情報")
                else:
                    send.send_text(fetch_result[0])

        # process event when user pushes X button
        elif types == "favdel":
            getFav = db.get_userfav(conn, uid, search_id)
            if getFav == "already":
                res_delete = db.delete_db(conn, search_id, uid, 'fav')
                if res_delete == "success":
                    text = f"「{lectureName[0]}」をお気に入りから外しました！"
                else:
                    text = "お気に入りを削除できませんでした。"
                send.send_text(text)
            elif getFav == "notyet":
                send.send_text(f"「{lectureName[0]}」は既に削除しているかお気に入り登録されていません。")

        # process event when user pushes MAGNIFYING GLASS button
        elif types == "icon":
            f = open(f'./theme/etc/icon.json', 'r', encoding='utf-8')
            json_content = [json.load(f)]
            send.send_result(json_content, "京大楽単bot", "京大楽単bot")

        # for admin only #
        elif types == 'decline':
            result = db.delete_db(conn, search_id, url[0])
            if result == 'success':
                db.delete_db(conn, search_id, url[0])
                message = f"[#{search_id}] を削除しました。"
            else:
                message = f"[#{search_id}] の削除に失敗しました。"
            send.push_text(message)

        # for admin only #
        elif types == 'merge':
            if url[0] == "None" or url[0] == "none":
                url[0] = ""
            result = db.update_db(conn, search_id, url[0], "url")
            if result[0] == 'success':
                db.delete_db(conn, search_id, url[0])
                message = f"[#{search_id}] をマージしました。"
            else:
                message = f"[#{search_id}] のマージに失敗しました。"
            send.push_text(message)


if __name__ == "__main__":
    #    app.run()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
