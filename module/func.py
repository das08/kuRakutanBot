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


def say_sorry(token, lists):
    send = ap.Send(token)

    send.send_text("申し訳ありません。現在この機能はご利用いただけません。")


def merge(token, lists):
    ap.push_flex()
