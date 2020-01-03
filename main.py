import func as fn
# import response as res

from flask import Flask, request, abort
import os
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
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage, PostbackEvent, Postback
)

app = Flask(__name__)

# 環境変数取得
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
db_host = os.environ["db_host"]
db_port = os.environ["db_port"]
db_name = os.environ["db_name"]
db_user = os.environ["db_user"]
db_pass = os.environ["db_pass"]

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
        pass

    def connect(self):
        """
        Connect to database.
        :return:
        """
        dsn = "host={} port={} dbname={} user={} password={}".format(db_host, db_port, db_name, db_user, db_pass)
        return psycopg2.connect(dsn)

    def get_by_id(self, search_id):
        """
        Get lecture data that matches lecture id from database.
        :param search_id: int
        :return: Single lecture data
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = """
                  SELECT
                  id, facultyname, lecturename, groups, credits, total_prev, accept_prev, total_prev2, accept_prev2, total_prev3, accept_prev3, url
                  FROM rakutan
                  WHERE (id) = (%s)
                  """
                    cur.execute(sqlStr, (int(search_id),))
                    results = cur.fetchall()
                    rakutan_data = {}

                    if len(results) > 0:
                        mes = "success"
                    else:
                        mes = "そのIDは存在しません。"

                    for row in results:
                        rakutan_data['id'] = row[0]
                        rakutan_data['facultyname'] = row[1]
                        rakutan_data['lecturename'] = row[2]
                        rakutan_data['groups'] = row[3]
                        rakutan_data['credits'] = row[4]
                        rakutan_data['total_prev'] = row[5]
                        rakutan_data['accept_prev'] = row[6]
                        rakutan_data['total_prev2'] = row[7]
                        rakutan_data['accept_prev2'] = row[8]
                        rakutan_data['total_prev3'] = row[9]
                        rakutan_data['accept_prev3'] = row[10]
                        rakutan_data['url'] = row[11]
                    return mes, rakutan_data

                except:
                    return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
                finally:
                    if cur:
                        cur.close()

    def get_query_result(self, search_word):
        """
        Get lecture list that matches search_word from database.
        Default: forward match
        :param search_word: str
        :return: List of lecture data
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = """
                  SELECT
                  id, facultyname, lecturename, groups, credits, total_prev, accept_prev, total_prev2, accept_prev2, total_prev3, accept_prev3, url
                  FROM rakutan
                  WHERE (lecturename) ILIKE (%s)
                  """
                    cur.execute(sqlStr, (search_word + "%",))
                    results = cur.fetchall()
                    rakutan_data = {}

                    if len(results) > 0:
                        mes = "success"
                    else:
                        mes = f"「{search_word}」は見つかりませんでした。\n(Tips) %を頭に付けて検索すると部分一致検索になります。"

                    rakutan_data['id'] = [row[0] for row in results]
                    rakutan_data['facultyname'] = [row[1] for row in results]
                    rakutan_data['lecturename'] = [row[2] for row in results]
                    rakutan_data['groups'] = [row[3] for row in results]
                    rakutan_data['credits'] = [row[4] for row in results]
                    rakutan_data['total_prev'] = [row[5] for row in results]
                    rakutan_data['accept_prev'] = [row[6] for row in results]
                    rakutan_data['total_prev2'] = [row[7] for row in results]
                    rakutan_data['accept_prev2'] = [row[8] for row in results]
                    rakutan_data['total_prev3'] = [row[9] for row in results]
                    rakutan_data['accept_prev3'] = [row[10] for row in results]
                    rakutan_data['url'] = [row[11] for row in results]

                    return mes, rakutan_data
                except:
                    return "DB接続エラーです", "exception"
                finally:
                    if cur:
                        cur.close()

    def get_merge_list(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = """
                  SELECT
                  search_id, url
                  FROM urlmerge
                  """
                    cur.execute(sqlStr)
                    results = cur.fetchall()

                    lecture_name = []
                    lecture_id = []
                    lecture_url = []

                    if len(results) > 0:
                        mes = "success"
                        for row in results:
                            search_id = row[0]
                            url = row[1]

                            get_lecture = self.get_by_id(search_id)[1]['lecturename']
                            lecture_id.append(search_id)
                            lecture_name.append(get_lecture)
                            lecture_url.append(url)
                    else:
                        mes = "error"

                    return mes, lecture_id, lecture_name, lecture_url
                except:
                    return "DB接続エラーです", "exception"
                finally:
                    if cur:
                        cur.close()

    def add_to_db(self, value, types):
        dates = datetime.datetime.now()
        if types == "uid":
            sqlStr = "INSERT INTO usertable (uid,register_time) VALUES (%s,%s)"
        # elif types == "count":
        #     sqlStr = "INSERT INTO usertable (count) VALUES (%s)"
        else:
            return "invalid types"
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(sqlStr, (value, dates))
                    return 'success'
                except:
                    print("Error: Cannnot add")
                    return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
                finally:
                    if cur:
                        cur.close()

    def update_db(self, uid, value="", types=""):
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    if types == "count":
                        sqlStr = "UPDATE usertable SET count = count+1 WHERE (uid)=(%s)"
                        cur.execute(sqlStr, (uid,))
                    elif types == "theme":
                        sqlStr = "UPDATE usertable SET color_theme = (%s) WHERE (uid)=(%s)"
                        cur.execute(sqlStr, (value, uid))
                    elif types == "url":
                        sqlStr = "UPDATE rakutan SET url = (%s) WHERE (id)=(%s)"
                        cur.execute(sqlStr, (value, uid))
                        print("merge ok")
                    return 'success'
                except:
                    print("Error: Cannnot update")
                    return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
                finally:
                    if cur:
                        cur.close()

    def delete_db(self, search_id, url):
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "DELETE FROM urlmerge WHERE (search_id)=(%s) and (url)=(%s)"
                    cur.execute(sqlStr, (search_id, url))
                    return 'success'
                except:
                    print("Error: Cannnot delete")
                    return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
                finally:
                    if cur:
                        cur.close()

    def kakomon_wait_for_merge(self, received_message, uid):
        dates = datetime.datetime.now()
        search_id = received_message[2:7]
        url = received_message[8:].strip()

        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "INSERT INTO urlmerge (search_id, url, uid, send_time) VALUES (%s,%s,%s,%s)"
                    cur.execute(sqlStr, (search_id, url, uid, dates))
                    return 'success'
                except:
                    print("Error: Cannnot update")
                    return "DB接続エラーです。時間を空けて再度お試しください。", "exception"
                finally:
                    if cur:
                        cur.close()

    def isinDB(self, uid):
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    sqlStr = "SELECT uid,color_theme FROM usertable WHERE (uid) = (%s)"
                    cur.execute(sqlStr, (uid,))
                    results = cur.fetchall()

                    if len(results) > 0:
                        color_theme = results[0][1]
                    else:
                        self.add_to_db(uid, "uid")

                    return True, color_theme
                except:
                    print("Error: Cannnot isin")
                    color_theme = "default"
                    return False, color_theme
                finally:
                    if cur:
                        cur.close()


class Prepare:
    """
    Prepares json file for sending flex message.
    """

    def __init__(self, received_message="", token=""):
        self.received_message = received_message
        self.token = token
        self.json_content = {}
        self.json_contents = []

    def rakutan_detail(self, array):
        """
        Rakutan detail for a specific lecture.
        Inside this function, json file for flex message is generated.
        :param array: lecture data from db
        :return: json_content
        """
        # load template
        f = open(f'./theme/{color_theme}/rakutan_detail.json', 'r', encoding='utf-8')

        data = json.dumps(json.load(f))
        self.json_content = LoadJSON(data)

        # modify header
        # self.json_content.header.contents[0]['text'] = f"Search ID: #{array['id']}"
        self.json_content.header.contents[0]['contents'][0]['text'] = f"Search ID: #{array['id']}"
        self.json_content.header.contents[0]['contents'][1]['color'] = "#3C3C3A"
        self.json_content.header.contents[1]['text'] = f"{array['lecturename']}"
        self.json_content.header.contents[3]['contents'][1]['text'] = f"{array['facultyname']}"
        self.json_content.header.contents[4]['contents'][1]['text'] = f"{self.isSet(array['groups'])}"
        self.json_content.header.contents[4]['contents'][3]['text'] = f"{self.isSet(array['credits'])}"
        # adjust font size if long
        length = self.lecturename_len(array['lecturename'])
        if length > 24:
            self.json_content.header.contents[1]['size'] = 'lg'
        elif length > 18:
            self.json_content.header.contents[1]['size'] = 'xl'

        # modify body
        self.json_content.body.contents[0]['contents'][1]['contents'][1]['text'] = '{}% ({}/{})'.format(
            self.cal_percentage(array['accept_prev'], array['total_prev']), self.isSet(array['accept_prev']),
            self.isSet(array['total_prev']))
        self.json_content.body.contents[0]['contents'][2]['contents'][1]['text'] = '{}% ({}/{})'.format(
            self.cal_percentage(array['accept_prev2'], array['total_prev2']), self.isSet(array['accept_prev2']),
            self.isSet(array['total_prev2']))
        self.json_content.body.contents[0]['contents'][3]['contents'][1]['text'] = '{}% ({}/{})'.format(
            self.cal_percentage(array['accept_prev3'], array['total_prev3']), self.isSet(array['accept_prev3']),
            self.isSet(array['total_prev3']))
        # rakutan judge
        rakutan_percent = self.rakutan_percentage(array)
        percent = [90, 85, 80, 75, 70, 60, 50, 0]
        judge = ['SSS', 'SS', 'S', 'A', 'B', 'C', 'D', 'F']
        judge_color = ['#c3c45b', '#c3c45b', '#c3c45b', '#cf2904', '#098ae0', '#f48a1c', '#8a30c9', '#837b8a']
        judge_list_data = {k: (v1, v2) for k, v1, v2 in zip(percent, judge, judge_color)}
        for key, value in judge_list_data.items():
            if rakutan_percent >= key:
                self.json_content.body.contents[0]['contents'][5]['contents'][1]['text'] = f"{value[0]}　"
                self.json_content.body.contents[0]['contents'][5]['contents'][1]['color'] = f"{value[1]}"
                break
        # modify url
        if array['url'] is not None:
            self.json_content.body.contents[0]['contents'][6]['contents'][1]['text'] = '〇'
            self.json_content.body.contents[0]['contents'][6]['contents'][1]['color'] = '#0fd142'
            self.json_content.body.contents[0]['contents'][6]['contents'][2]['text'] = 'リンク'
            self.json_content.body.contents[0]['contents'][6]['contents'][2]['color'] = '#4c7cf5'
            self.json_content.body.contents[0]['contents'][6]['contents'][2]['decoration'] = 'underline'
            self.json_content.body.contents[0]['contents'][6]['contents'][2]['action']['uri'] = array['url']
        else:
            url_provide_template = {"type": "postback", "label": "action", "data": "type=url&id="}
            url_provide_template['data'] += str(array['id'])
            self.json_content.body.contents[0]['contents'][6]['contents'][2]['action'] = url_provide_template
            self.json_content.body.contents[0]['contents'][6]['contents'][2]['text'] = '追加'

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
        facultyname_abbr = {'文学部': '文', '教育学部': '教', '法学部': '法', '経済学部': '経', '理学部': '理', '医学部': '医医', '医学部（人間健康科学科）': '人健',
                            '薬学部': '薬', '工学部': '工', '農学部': '農', '総合人間学部': '総人', '国際高等教育院': '般教'}
        color_theme_font = {'default': '#4c7cf5', 'yellow': '#D17A22'}
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
                              {'type': 'text', 'text': '選択', 'size': 'md', 'color': '#4c7cf5', 'align': 'end', 'weight': 'bold',
                               'decoration': 'underline', 'margin': 'none',
                               'action': {'type': 'message', 'label': 'action', 'text': '#[Lecture ID]'}, 'offsetBottom': '3px',
                               'flex': 2}], 'margin': 'lg'}
                socket['contents'][1]['color'] = color_theme_font[color_theme]
                socket['contents'][0][
                    'text'] = f"[{facultyname_abbr[array['facultyname'][processed_count]]}]{array['lecturename'][processed_count]}"
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

    def isURL(self, text):
        """
        Checks if received text is in URL-format or not. Has to start and end with brackets and include sharp-id.
        :param text: received_text
        :return: Bool
        """
        pattern = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
        url = text[8:].split()

        if text[0] == "[" and (text[1] == "#" or text[1] == "＃") and text[7] == "]" and text[2:7].isdigit():
            # check if is in correct url-format.
            if re.match(pattern, url):
                return True
            else:
                return False

    def isSet(self, value):
        """
        Check if value is None type.
        :param value: value
        :return:
        """
        if value is None:
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
        """
        Calculates percentage.
        :param accepted: int
        :param total: int
        :return: int percent
        """
        if accepted == 0 or total == 0:
            return '---'
        else:
            return round(100 * accepted / total, 1)

    def rakutan_percentage(self, array):
        """
        Returns percentage for judging rakurtan.
        Priority: prev -> prev2 -> prev3
        :param array: lecture data from db
        :return: int percent
        """
        if array['total_prev'] != 0:
            percent = round(100 * array['accept_prev'] / array['total_prev'], 1)
        elif array['total_prev2'] != 0:
            percent = round(100 * array['accept_prev2'] / array['total_prev2'], 1)
        else:
            percent = round(100 * array['accept_prev3'] / array['total_prev3'], 1)
        return percent

    def lecturename_len(self, text):
        count = 0
        for c in text:
            if unicodedata.east_asian_width(c) in 'FWA':
                count += 2
            else:
                count += 1
        return count

    def merge_url(self, lecture_id, lecture_name, lecture_url):
        f = open(f'./theme/default/merge.json', 'r', encoding='utf-8')
        json_content = json.load(f)

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

    def send_result(self, json_content, search_text, types):
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

            # make it json fotmat
            page = str(page).replace("'", '"').replace("True", "true")

            flex_message = FlexSendMessage(
                alt_text=alt_text,
                contents=json.loads(page)
            )
            content.append(flex_message)
            page_count += 1

        line_bot_api.reply_message(self.token, messages=content)

    def send_text(self, message):
        """
        Sends plain text.
        :param message: str
        :return: Nothing
        """
        line_bot_api.reply_message(
            self.token,
            TextSendMessage(text=message),
        )

    def send_multiline_text(self, message_list):
        """
        Sends multiline text.
        :param message_list: List
        :return: Nothing
        """
        message = []
        for row in message_list:
            mes = TextSendMessage(text=row)
            message.append(mes)

        line_bot_api.reply_message(
            self.token,
            messages=message
        )

    def push_flex(self, message_list):
        f = open(f'./theme/default/hantei.json', 'r', encoding='utf-8')
        json_content = json.load(f)

        flex_message = FlexSendMessage(
            alt_text="alt_text",
            contents=json_content
        )

        line_bot_api.push_message(
            "U97cd032cffb520dfa79de4c21cd94df5",
            messages=flex_message
        )

    def push_text(self, message):
        line_bot_api.push_message(
            "U97cd032cffb520dfa79de4c21cd94df5",
            TextSendMessage(text=message),
        )


@app.route("/")
def hello_world():
    return "hello world!"


@app.route("/wakeandpush")
def push_flex():
    prepare = Prepare()
    db = DB()
    result = db.get_merge_list()

    if result[0] != 'success':
        line_bot_api.reply_message(
            "U97cd032cffb520dfa79de4c21cd94df5",
            TextSendMessage(text="[merge]db error:Could not fetch."),
        )
    else:
        lecture_id = result[1]
        lecture_name = result[2]
        lecture_url = result[3]
        json_content = prepare.merge_url(lecture_id, lecture_name, lecture_url)
        flex_message = FlexSendMessage(
            alt_text="過去問提供URL確認",
            contents=json_content
        )
        line_bot_api.push_message(
            "U97cd032cffb520dfa79de4c21cd94df5",
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


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global color_theme
    token = event.reply_token
    uid = event.source.user_id
    received_message = event.message.text.strip()

    send = Send(token)
    db = DB()
    prepare = Prepare(received_message, token)

    # load reserved word dict
    # response = res.response
    response = {
        "help": fn.help,
        "Help": fn.help,
        "ヘルプ": fn.help,
        "テーマ変更": fn.select_theme,
        "テーマ": fn.select_theme,
        "色": fn.select_theme,
        "はんてい詳細": fn.rakutan_hantei,
        "判定": fn.rakutan_hantei,
        "判定詳細": fn.rakutan_hantei,
        "おみくじ": fn.say_sorry,
        "CB": fn.say_sorry,
        "d@s08": fn.merge,
        "@theme:default": fn.change_theme,
        "@theme:yellow": fn.change_theme
    }

    check_user = db.isinDB(uid)
    if check_user[0]:
        # add 1 to search counter
        db.update_db(uid, types='count')
    color_theme = check_user[1]

    if received_message in response:
        lists = [uid, received_message, color_theme]
        # 1.Check if reserved word is sent.
        response[received_message](token, lists)
    else:
        # 2.Check if kakomon URL is sent:
        if prepare.isURL(received_message):
            fetch_result = db.get_by_id(received_message[2:7])
            if fetch_result[0] == 'success':
                fetch_result = db.kakomon_wait_for_merge(received_message, uid)
                if fetch_result == 'success':
                    send.send_text("過去問リンクの提供ありがとうございます！確認ができ次第反映されます。")
                else:
                    send.send_text("DB接続エラーが発生しました。時間を空けてお試しください。")
            else:
                send.send_text("指定された講義IDは存在しません。")
        # 3.Check if ID is sent:
        elif prepare.isID(received_message):
            fetch_result = db.get_by_id(received_message[1:6])
            if fetch_result[0] == 'success':
                array = fetch_result[1]
                json_content = prepare.rakutan_detail(array)
                send.send_result(json_content, received_message, 'rakutan_detail')
            else:
                send.send_text(fetch_result[0])

        # 4. Check if lecturename is sent:
        else:
            fetch_result = db.get_query_result(received_message)
            if fetch_result[0] == 'success':
                array = fetch_result[1]
                record_count = len(array['id'])
                # if query result is :
                if record_count == 1:
                    array = prepare.list_to_str(array)
                    json_content = prepare.rakutan_detail(array)
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


@handler.add(PostbackEvent)
def handle_message(event):
    token = event.reply_token
    received_postback = event.postback.data
    print(received_postback)
    send = Send(token)
    db = DB()

    params = urllib.parse.parse_qs(received_postback)
    types = params.get('type')[0]
    search_id = params.get('id')[0]
    url = params.get('url')

    if types == 'url':
        message_list = ["下の講義IDをそのままコピーし、その後ろに続けて過去問URLを貼り付けて送信してください。", f"[#{search_id}]"]
        send.send_multiline_text(message_list)

    # for admin only #
    elif types == 'decline':
        result = db.delete_db(search_id, url[0])
        if result == 'success':
            db.delete_db(search_id, url[0])
            message = f"#[{search_id}] を削除しました。"
        else:
            message = f"#[{search_id}] の削除に失敗しました。"
        send.push_text(message)

    # for admin only #
    elif types == 'merge':
        result = db.update_db(search_id, url[0], "url")
        if result == 'success':
            db.delete_db(search_id, url[0])
            message = f"#[{search_id}] をマージしました。"
        else:
            message = f"#[{search_id}] のマージに失敗しました。"
        send.push_text(message)


if __name__ == "__main__":
    #    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
