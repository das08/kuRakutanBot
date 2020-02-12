import random

import module
# import setting

from flask import Flask, request, abort
from pymongo import MongoClient
import os
import sys
import re
import json
import datetime
import math
import copy
import psycopg2
import unicodedata
import urllib

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

# 環境変数取得
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
ADMIN_UID = os.environ["ADMIN_UID"]
db_host = os.environ["db_host"]
db_port = os.environ["db_port"]
db_name = os.environ["db_name"]
db_user = os.environ["db_user"]
db_pass = os.environ["db_pass"]
mongo_db = os.environ["mongo_db"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
color_theme = ""


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
        """Connect to database"""
        uri = "mongodb://das08rw:Takeda0802rw@178.128.89.239:27017"
        client = MongoClient(uri)
        return client  # ['rakutanDB']

    def get_by_id(self, conn, search_id):
        """Get lecture data that matches lecture id from database."""
        try:
            query = {'id': int(search_id)}

            collection = conn['rakutan']
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            rakutan_data = {}

            if count > 0:
                mes = "success"
            else:
                mes = "そのIDは存在しません。"

            for row in results:
                # # set value to rakutan_data
                rakutan_data = row

            return mes, rakutan_data

        except:
            stderr(f"[error]get-by-id:Cannot #{search_id}")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
        # finally:
        #     if cur:
        #         cur.close()

    def get_query_result(self, conn, searchWord):
        """
        Get lecture list that matches search_word from database.
        Default: forward match
        :param searchWord: str
        :return: List of lecture data
        """
        try:
            # sqlStr = """
            #   SELECT
            #   id, facultyname, lecturename, groups, credits, total_prev, accept_prev, total_prev2, accept_prev2, total_prev3, accept_prev3, url
            #   FROM rakutan
            #   WHERE (lecturename) ILIKE (%s)
            #   """
            query = {'lecturename': {'$regex': f'^{searchWord}', '$options': 'i'}}

            collection = conn['rakutan']
            results = collection.find(filter=query, projection={'_id': False})
            count = collection.count_documents(filter=query)

            rakutan_data = {}
            mongoToList = []

            if count > 0:
                mes = "success"
            else:
                mes = f"「{searchWord}」は見つかりませんでした。\n【検索のヒント】\n%を頭に付けて検索すると部分一致検索になります。デフォルトは前方一致検索です。"
            for row in results:
                mongoToList.append(row)

            # set value to rakutan_data
            for column in self.columnNameRakutan:
                rakutan_data[column] = [row[column] for row in mongoToList]
            return mes, rakutan_data
        except:
            stderr(f"[error]get-query-result:Cannot {searchWord}")
            return "DB接続エラーです", "exception"
        # finally:
        #     if cur:
        #         cur.close()

    def get_userfav(self, conn, uid, lectureID="", types=""):
        try:
            if types == "count":
                query = {'uid': uid}
                # sqlStr = "SELECT lectureid, lecturename FROM userfav WHERE (uid = (%s))"
            else:
                query = {'$and': [{'uid': uid}, {'lectureid': lectureID}]}
                # sqlStr = "SELECT lectureid FROM userfav WHERE (uid = (%s) and lectureid = (%s))"

            collection = conn['userfav']
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            if count > 0:
                mes = "already"
            else:
                mes = "notyet"
            if types == "count":
                mongoToList = []
                fav_list = {}

                for row in results:
                    mongoToList.append(row)

                # set value to fav_list
                for column in self.columnNameFav:
                    fav_list[column] = [row[column] for row in mongoToList]
                mes = fav_list

            return mes
        except:
            stderr(f"[error]get-userfav:Cannot {lectureID}")
            return "error"
        # finally:
        #     if cur:
        #         cur.close()

    def get_merge_list(self, conn):
        # with conn.cursor() as cur:
        try:
            query = {'search_id': {'$ne': ''}}
            # sqlStr = "SELECT search_id, url FROM urlmerge"
            collection = conn['urlmerge']
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            lecture_name = []
            lecture_id = []
            lecture_url = []

            if count > 0:
                mes = "success"
                for row in results:
                    search_id = row['id']
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
        # finally:
        #     if cur:
        #         cur.close()

    def get_omikuji(self, conn, types):
        # with conn.cursor() as cur:
        try:
            if types == "normal":
                query = {'$and': [{'facultyname': '国際高等教育院'}, {'accept_prev': {'$gt': 15}},
                                  {'$expr': {'$gt': ['$accept_prev', {'$multiply': [0.8, '$total_prev']}]}}]}
                # sqlStr = "select id from rakutan where (facultyname='国際高等教育院' and accept_prev > 15 and accept_prev > 0.8*total_prev) order by random() limit 1"
            else:
                query = {'$and': [{'facultyname': '国際高等教育院'}, {'total_prev': {'$gt': 4}},
                                  {'$expr': {'$lt': ['$accept_prev', {'$multiply': [0.31, '$total_prev']}]}}]}
                # sqlStr = "select id from rakutan where (facultyname='国際高等教育院' and total_prev > 4 and accept_prev < 0.31 *total_prev) order by random() limit 1"
            collection = conn['rakutan']
            results = collection.find(filter=query, projection={'id': True})
            count = collection.count_documents(filter=query)

            omikujiID = random.choice([row['id'] for row in results])

            stderr(f"[success]omikuji:Omikuji {types}!")
            return 'success', omikujiID
        except:
            stderr("[error]omikuji:Cannot get omikuji.")
            return "DB接続エラーです", "exception"
        # finally:
        #     if cur:
        #         cur.close()

    def add_to_db(self, conn, uid, types, lectureID="", lectureName=""):
        dates = str(datetime.datetime.now()).replace('.', '/')
        if types == "uid":
            query = {'uid': uid, 'register_time': dates}
            collection = conn['usertable']
            # sqlStr = "INSERT INTO usertable (uid,register_time) VALUES (%s,%s)"

        elif types == "fav":
            res = self.get_userfav(conn, uid, lectureID)
            if res == "already":
                return "already"
            query = {'uid': uid, 'lectureid': lectureID, 'lecturename': lectureName}
            collection = conn['userfav']
            # sqlStr = "INSERT INTO userfav (uid,lectureid,lecturename) VALUES (%s,%s,%s)"

        else:
            return "invalid types"

        # with conn.cursor() as cur:
        try:
            results = collection.insert(query)
            # count = collection.count_documents(filter=query)

            return 'success'
        except:
            stderr("[error]addDB:Cannnot add to usertable/userfav.")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
        # finally:
        #     if cur:
        #         cur.close()

    def update_db(self, conn, uid, value="", types=""):
        dates = str(datetime.datetime.now()).replace('.', '/')
        # with conn.cursor() as cur:
        try:
            if types == "count":
                collection = conn['usertable']
                collection.update({'uid': uid}, {'$inc': {'count': 1}})
                # sqlStr = "UPDATE usertable SET count = count+1 WHERE (uid)=(%s)"
                # cur.execute(sqlStr, (uid,))
            elif types == "theme":
                collection = conn['usertable']
                collection.update({'uid': uid}, {'$set': {'color_theme': value}})
                # sqlStr = "UPDATE usertable SET color_theme = (%s) WHERE (uid)=(%s)"
                # cur.execute(sqlStr, (value, uid))
            elif types == "url":
                collection = conn['rakutan']
                collection.update({'id': uid}, {'$set': {'url': value}})
                # sqlStr = "UPDATE rakutan SET url = (%s) WHERE (id)=(%s)"
                # cur.execute(sqlStr, (value, uid))
            return 'success'
        except:
            stderr(f"[error]updateDB:Cannnot update [{types}].")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
        # finally:
        #     if cur:
        #         cur.close()

    def delete_db(self, conn, search_id, uid="", types="", url=""):
        # with conn.cursor() as cur:
        try:
            if types == "fav":
                query = {'$and': [{'uid': uid}, {'lectureid': search_id}]}
                collection = conn['userfav']
                # sqlStr = "DELETE FROM userfav WHERE (uid)=(%s) and (lectureid)=(%s)"
                # cur.execute(sqlStr, (uid, search_id))
            else:
                query = {'$and': [{'search_id': search_id}, {'url': url}]}
                collection = conn['urlmerge']
                # sqlStr = "DELETE FROM urlmerge WHERE (search_id)=(%s) and (url)=(%s)"
                # cur.execute(sqlStr, (search_id, url))

            results = collection.remove(query)

            return 'success'
        except:
            stderr("[error]deleteDB:Cannnot delete urlmarge/userfav.")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
        # finally:

    #     if cur:
    #         cur.close()

    def kakomon_wait_for_merge(self, conn, received_message, uid):
        dates = str(datetime.datetime.now()).replace('.', '/')
        search_id = received_message[2:7]
        url = received_message[8:].strip()

        # with conn.cursor() as cur:
        try:
            query = {'search_id': search_id, 'url': url, 'uid': uid, 'send_time': dates}
            # sqlStr = "INSERT INTO urlmerge (search_id, url, uid, send_time) VALUES (%s,%s,%s,%s)"
            collection = conn['urlmerge']
            results = collection.insert(query)
            return 'success'
        except:
            stderr("[error]kakomon-merge:Cannot insert.")
            return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
        # finally:
        #     if cur:
        #         cur.close()

    def isinDB(self, conn, uid):
        # with conn.cursor() as cur:
        try:
            # sqlStr = "SELECT uid,color_theme FROM usertable WHERE (uid) = (%s)"
            query = {'uid': uid}
            collection = conn['usertable']
            results = collection.find(filter=query)
            count = collection.count_documents(filter=query)

            if count > 0:
                # color_theme = results[0][1]
                for row in results:
                    color_theme = row['color_theme']
            else:
                self.add_to_db(conn, uid, "uid")
                color_theme = "default"

            return True, color_theme
        except:
            stderr(f"[error]isinDB:Cannnot isin {uid}")
            color_theme = "default"
            return False, color_theme
        # finally:
        # if cur:
        #     cur.close()


class Prepare:
    """
    Prepares json file for sending flex message.
    """

    def __init__(self, received_message="", token=""):
        self.received_message = received_message
        self.token = token
        self.json_content = {}
        self.json_contents = []

    def rakutan_detail(self, array, fav="notyet", color="", omikuji=""):
        """
        Rakutan detail for a specific lecture.
        Inside this function, json file for flex message is generated.
        :param fav:
        :param omikuji:
        :param array: lecture data from db
        :param color: FOR fn.omikuji
        :return: json_content
        """
        if color != "":
            f = open(f'./theme/{color}/rakutan_detail.json', 'r', encoding='utf-8')
        else:
            f = open(f'./theme/{color_theme}/rakutan_detail.json', 'r', encoding='utf-8')

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
            body_contents[0]['contents'][year]['contents'][1]['text'] = '{}% ({}/{})'.format(
                self.cal_percentage(array[f'accept_prev{_year}'], array[f'total_prev{_year}']),
                self.isSet(array[f'accept_prev{_year}']), self.isSet(array[f'total_prev{_year}']))

        # rakutan judge
        rakutan_percent = self.rakutan_percentage(array)
        percent = [90, 85, 80, 75, 70, 60, 50, 0]
        judge = ['SSS', 'SS', 'S', 'A', 'B', 'C', 'D', 'F']
        judge_color = ['#c3c45b', '#c3c45b', '#c3c45b', '#cf2904', '#098ae0', '#f48a1c', '#8a30c9', '#837b8a']
        judge_list_data = {k: (v1, v2) for k, v1, v2 in zip(percent, judge, judge_color)}
        for key, value in judge_list_data.items():
            if rakutan_percent >= key:
                judge_view = body_contents[0]['contents'][5]['contents'][1]
                judge_view['text'] = f"{value[0]}　"
                judge_view['color'] = f"{value[1]}"
                break
        # modify url
        kakomon_symbol = body_contents[0]['contents'][6]['contents'][1]
        kakomon_link = body_contents[0]['contents'][6]['contents'][2]

        if array['url'] != "":
            kakomon_symbol['text'] = '〇'
            kakomon_symbol['color'] = '#0fd142'
            kakomon_link['text'] = 'リンク'
            kakomon_link['color'] = '#4c7cf5'
            kakomon_link['decoration'] = 'underline'
            kakomon_link['action']['uri'] = array['url']
        else:
            url_provide_template = {"type": "postback", "label": "action", "data": "type=url&id="}
            url_provide_template['data'] += str(array['id'])
            kakomon_link['action'] = url_provide_template
            kakomon_link['text'] = '追加する'

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
                           '医学部（人間健康科学科）': '人健',
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
        """
        Checks if received text is in ID-format or not. Has to start with sharp.
        :param text: received_text
        :return: Bool
        """
        if len(text) == 6 and (text[0] == "#" or text[0] == "＃") and text[1:5].isdigit():
            return True

    def isURLID(self, text):
        """
        Checks if received text is in URLID-format or not. Has to start and end with brackets and include sharp-id.
        :param text: received_text
        :return: Bool
        """
        if text[0] == "[" and (text[1] == "#" or text[1] == "＃") and text[7] == "]" and text[2:7].isdigit():
            return True

    def isURL(self, text):
        """Checks if received text is in URL-format or not. Has to start with http:// or https://"""
        # regex for judging URL format.
        pattern = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
        url = text[8:].strip()
        # judge if is in correct url-format.
        if re.match(pattern, url):
            return True
        else:
            return False

    def isSet(self, value):
        """Return '---' if value is None type."""
        if value == "":
            return '---'
        else:
            return value

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
        """Returns percentage for judging rakurtan"""
        if array['total_prev'] != 0:
            percent = round(100 * array['accept_prev'] / array['total_prev'], 1)
        elif array['total_prev2'] != 0:
            percent = round(100 * array['accept_prev2'] / array['total_prev2'], 1)
        else:
            percent = round(100 * array['accept_prev3'] / array['total_prev3'], 1)
        return percent

    def lecturename_len(self, text):
        """Find length of lecturename based on unicode"""
        length = 0
        for c in text:
            if unicodedata.east_asian_width(c) in 'FWA':
                length += 2
            else:
                length += 1
        return length

    def merge_url(self, lecture_id, lecture_name, lecture_url):
        """For ADMIN. Prepares flex message for merging/declining kakomon url."""
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
    prepare = Prepare(received_message, token)

    with db.connect() as client:
        conn = client[mongo_db]
        # conn = db.connect()
        check_user = db.isinDB(conn, uid)
        if check_user[0]:
            # add 1 to search counter
            db.update_db(conn, uid, types='count')
        color_theme = check_user[1]

        # load reserved command dict
        response = module.response.command

        if received_message in response:
            # prepare params to pass
            lists = [uid, received_message, color_theme]

            # 1.Check if reserved word is sent.
            response[received_message](token, lists)
        else:
            # 2.Check if kakomon URL is sent:
            if prepare.isURLID(received_message):
                if prepare.isURL(received_message):
                    fetch_result = db.get_by_id(conn, received_message[2:7])
                    if fetch_result[0] == 'success':
                        fetch_result = db.kakomon_wait_for_merge(conn, received_message, uid)
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
                    json_content = prepare.rakutan_detail(array, fetch_fav)
                    send.send_result(json_content, received_message, 'rakutan_detail')
                else:
                    send.send_text(fetch_result[0])

            # 4. Check if lecturename is sent:
            else:
                fetch_result = db.get_query_result(conn, received_message)
                stderr(f"[success]{uid}: {received_message}")
                if fetch_result[0] == 'success':
                    array = fetch_result[1]
                    record_count = len(array['id'])
                    # if query result is 1:
                    if record_count == 1:

                        array = prepare.list_to_str(array)
                        fetch_fav = db.get_userfav(conn, uid, array['id'])

                        json_content = prepare.rakutan_detail(array, fetch_fav)
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

    params = urllib.parse.parse_qs(received_postback)
    types = params.get('type')[0]
    search_id = params.get('id')[0]
    lectureName = params.get('lecname')
    url = params.get('url')
    with db.connect() as client:
        conn = client[mongo_db]
        # conn = db.connect()

        # send template for sending kakomon url
        if types == 'url':
            message_list = ["下の講義IDをそのままコピーし、その後ろに続けて過去問URLを貼り付けて送信してください。", f"[#{search_id}]\n"]
            send.send_multiline_text(message_list)

        elif types == 'fav':
            # with db.connect() as conn:
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
                res_count = db.get_userfav(conn, uid, 12345, "count")
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
                    json_content = prepare.rakutan_detail(array, fetch_fav, "default")
                    f = open(f'./theme/etc/singletext.json', 'r', encoding='utf-8')
                    json_text = [json.load(f)]
                    json_text[0]['body']['contents'][0]['text'] = text

                    json_text.append(json_content[0])
                    send.send_result(json_text, 'postback', f"「{lectureName[0]}」のらくたん情報")
                else:
                    send.send_text(fetch_result[0])
        elif types == "favdel":
            # with db.connect() as conn:
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

        # send small bubble
        elif types == "icon":
            f = open(f'./theme/etc/icon.json', 'r', encoding='utf-8')
            json_content = [json.load(f)]
            send.send_result(json_content, "京大楽単bot", "京大楽単bot")

        # for admin only #
        elif types == 'decline':
            # with db.connect() as conn:
            result = db.delete_db(conn, search_id, url[0])
            if result == 'success':
                db.delete_db(conn, search_id, url[0])
                message = f"[#{search_id}] を削除しました。"
            else:
                message = f"[#{search_id}] の削除に失敗しました。"
            send.push_text(message)

        # for admin only #
        elif types == 'merge':
            # with db.connect() as conn:
            result = db.update_db(conn, search_id, url[0], "url")
            if result == 'success':
                db.delete_db(conn, search_id, url[0])
                message = f"[#{search_id}] をマージしました。"
            else:
                message = f"[#{search_id}] のマージに失敗しました。"
            send.push_text(message)


if __name__ == "__main__":
    #    app.run()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
