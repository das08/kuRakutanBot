import main as ap
import json


def helps(token, lists):
    send = ap.Send(token)
    color_theme = lists[2]
    f = open(f'./theme/{color_theme}/help.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "ヘルプ", "ヘルプ")
    return


def rakutan_hantei(token, lists):
    send = ap.Send(token)
    color_theme = lists[2]
    f = open(f'./theme/{color_theme}/hantei.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "判定詳細", "判定詳細")
    return


def omikuji(token, lists):
    send = ap.Send(token)
    db = ap.DB()
    prepare = ap.Prepare()

    fetch_omikuji = db.get_omikuji('normal')

    if fetch_omikuji[0] == "success":
        fetch_result = db.get_by_id(fetch_omikuji[1])
        if fetch_result[0] == 'success':
            array = fetch_result[1]
            json_content = prepare.rakutan_detail(array, lists[2], "normal")
            send.send_result(json_content, '楽単おみくじ結果', 'omikuji')
        else:
            send.send_text(fetch_result[0])
    else:
        send.send_text("おみくじに失敗しました。もう一度引いてください。")


def onitan(token, lists):
    send = ap.Send(token)
    db = ap.DB()
    prepare = ap.Prepare()

    fetch_omikuji = db.get_omikuji('oni')

    if fetch_omikuji[0] == "success":
        fetch_result = db.get_by_id(fetch_omikuji[1])
        if fetch_result[0] == 'success':
            array = fetch_result[1]
            json_content = prepare.rakutan_detail(array, lists[2], "oni")
            send.send_result(json_content, '鬼単おみくじ結果', 'omikuji')
        else:
            send.send_text(fetch_result[0])
    else:
        send.send_text("おみくじに失敗しました。もう一度引いてください。")


def select_theme(token, lists):
    send = ap.Send(token)
    color_theme = lists[2]
    f = open(f'./theme/{color_theme}/theme_select.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "テーマ変更", "テーマ変更")


def change_theme(token, lists):
    send = ap.Send(token)
    db = ap.DB()

    uid = lists[0]
    theme = lists[1][7:]
    db.update_db(uid, theme, 'theme')
    send.send_text("カラーテーマを変更しました！")


def inquiry(token, lists):
    send = ap.Send(token)
    color_theme = lists[2]
    f = open(f'./theme/etc/inquiry.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "お問い合わせ", "お問い合わせ")
    return


def my_uid(token, lists):
    send = ap.Send(token)
    uid = lists[0]
    send.send_text(f"Your uid: {uid}")


def say_sorry(token, lists):
    send = ap.Send(token)
    send.send_text("申し訳ありません。現在この機能はご利用いただけません。")


def say_sorry2(token, lists):
    send = ap.Send(token)
    send.send_text("このテーマはゴールドユーザー限定です。")


def show_version(token, lists):
    send = ap.Send(token)
    f = open(f'./theme/etc/icon.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "京大楽単bot", "京大楽単bot")
    return


def merge(token, lists):
    ap.push_flex()


def set_menu(token, lists):
    send = ap.Send(token)
    uid = lists[0]
    menu = lists[1][5:]
    text = "リッチメニューを変更しました。"

    if menu == 'birdman':
        menu_id = "richmenu-fb2161dd36ae54baf01b17158eb22ca5"
        text += "\n@set:defaultで元に戻せます。"
    else:
        menu_id = "richmenu-66a5b2117176dfd7d98055e2b6c85aed"

    ap.line_bot_api.link_rich_menu_to_user(uid, menu_id)
    send.send_text(text)
