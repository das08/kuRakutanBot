import main as ap
import json
import math


def prepareFlexMessage(token, color_theme, json_name, alt_text):
    send = ap.Send(token)
    f = open(f'./theme/{color_theme}/{json_name}.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, alt_text, alt_text)


def prepareOmikuji(token, color_theme, omikuji_type, alt_text, uid):
    send = ap.Send(token)
    db = ap.DB()
    prepare = ap.Prepare()

    with db.connect() as client:
        conn = client[ap.mongo_db]
        get_omikuji = db.get_omikuji(conn, omikuji_type)

        if get_omikuji[0] == "success":
            getRakutanInfo = db.get_by_id(conn, get_omikuji[1])
            if getRakutanInfo[0] == 'success':
                array = getRakutanInfo[1]
                fetch_fav = db.get_userfav(conn, uid, array['id'])

                json_content = prepare.rakutan_detail(array, fetch_fav, color_theme, omikuji_type)
                send.send_result(json_content, alt_text, 'omikuji')
            else:
                send.send_text(getRakutanInfo[0])
        else:
            send.send_text("おみくじに失敗しました。もう一度引いてください。")


def helps(token, lists):
    color_theme = lists[2]
    prepareFlexMessage(token, color_theme, 'help', 'ヘルプ')


def rakutanHantei(token, lists):
    color_theme = lists[2]
    prepareFlexMessage(token, color_theme, 'hantei', '判定詳細')


def selectTheme(token, lists):
    color_theme = lists[2]
    prepareFlexMessage(token, color_theme, 'theme_select', 'テーマ変更')


def inquiry(token, lists):
    prepareFlexMessage(token, 'etc', 'inquiry', 'お問い合わせ')


def showVersion(token, lists):
    prepareFlexMessage(token, 'etc', 'icon', '京大楽単bot')


def normalOmikuji(token, lists):
    color_theme = lists[2]
    prepareOmikuji(token, color_theme, 'normal', '楽単おみくじ結果', lists[0])


def shrineOmikuji(token, lists):
    color_theme = lists[2]
    prepareOmikuji(token, color_theme, 'shrine', '人社おみくじ結果', lists[0])


def oniOmikuji(token, lists):
    color_theme = lists[2]
    prepareOmikuji(token, color_theme, 'oni', '鬼単おみくじ結果', lists[0])


def changeTheme(token, lists):
    send = ap.Send(token)
    db = ap.DB()
    uid = lists[0]
    theme = lists[1][7:]
    db.update_db(uid, theme, 'theme')
    send.send_text("カラーテーマを変更しました！")


def myUID(token, lists):
    send = ap.Send(token)
    uid = lists[0]
    send.send_text(uid)


def sorry(token, lists):
    send = ap.Send(token)
    send.send_text("申し訳ありません。現在この機能はご利用いただけません。")


def unavailable(token, lists):
    send = ap.Send(token)
    send.send_text("このテーマはゴールドユーザー限定です。")


def checkKakomon(token, lists):
    ap.push_flex()


def getFavList(token, lists):
    send = ap.Send(token)
    db = ap.DB()
    uid = lists[0]
    with db.connect() as client:
        conn = client[ap.mongo_db]
        get_fav = db.get_userfav(conn, uid, types='count')

    json_contents = []
    processed_count = 0
    record_count = len(get_fav['lectureid'])
    number_of_pages = math.ceil(record_count / 10)

    # load templates
    f = open(f'./theme/default/fav.json', 'r', encoding='utf-8')
    f_data = json.dumps(json.load(f))

    # put all pages into json_contents list
    json_contents.append(ap.LoadJSON(f_data))
    for _ in range(number_of_pages - 1):
        json_contents.append(ap.LoadJSON(f_data))

    # generate list for each page
    for i in range(1, number_of_pages + 1):
        json_contents[i - 1]["header"]["contents"][1]["text"] = f"({i}/{number_of_pages})"

        json_fav_row = []
        # 20 lecturename lists per page
        for j in range(10):
            if processed_count == record_count:
                break

            # template for lecturename row
            socket = {'type': 'box', 'layout': 'horizontal',
                      'contents': [
                          {'type': 'text', 'text': '[Lecture Name]', 'size': 'sm', 'color': '#555555', 'flex': 7},
                          {'type': 'text', 'text': '選択', 'size': 'md', 'color': '#4c7cf5', 'align': 'end',
                           'weight': 'bold', 'decoration': 'underline', 'margin': 'none',
                           'action': {'type': 'message', 'label': 'action', 'text': '#[Lecture ID]'},
                           'offsetBottom': '3px',
                           'flex': 2},
                          {'type': 'text', 'text': '×', 'size': 'md', 'color': '#881111', 'align': 'end',
                           'weight': 'bold', 'decoration': 'none', 'margin': 'none',
                           'action': {'type': 'postback', 'label': 'action', 'data': '#123456'},
                           'offsetBottom': '3px'
                           }
                      ], 'margin': 'lg'}
            # socket['contents'][1]['color'] = colorCode[color_theme]

            socket['contents'][0]['text'] = f"{get_fav['lecturename'][processed_count]}"
            socket["contents"][1]['action']['text'] = '#' + str(get_fav['lectureid'][processed_count])

            socket["contents"][2]['action'][
                'data'] = f"type=favdel&id={get_fav['lectureid'][processed_count]}&lecname={get_fav['lecturename'][processed_count]}"

            # add row to the page
            json_fav_row.append(socket.copy())
            processed_count += 1

        # overwrite old page with new one
        json_contents[i - 1]["body"]["contents"][0]["contents"] = json_fav_row
    if record_count == 0:
        send.send_text("お気に入りは登録されていません。\n講義名の左上にある★マークを押すとお気に入り登録できます。")
    else:
        send.send_result(json_contents, types='お気に入り一覧')


def setRichMenu(token, lists):
    send = ap.Send(token)
    uid = lists[0]
    menu = lists[1][5:]
    text = "リッチメニューを変更しました。"

    if menu == 'birdman':
        menu_id = "richmenu-fb2161dd36ae54baf01b17158eb22ca5"
        text += "\n@set:defaultで元に戻せます。"
    elif menu == 'ad':
        menu_id = "richmenu-fb2161dd36ae54baf01b17158eb22ca5"
        text += "\n@set:defaultで元に戻せます。"
    else:
        menu_id = "richmenu-66a5b2117176dfd7d98055e2b6c85aed"
    ap.line_bot_api.link_rich_menu_to_user(uid, menu_id)
    send.send_text(text)
