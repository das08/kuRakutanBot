import main as ap
import json


def help(token):
    send = ap.Send(token)
    f = open('./theme/yellow/help.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "ヘルプ", "ヘルプ")
    return


def rakutan_hantei(token):
    send = ap.Send(token)
    f = open('./theme/yellow/hantei.json', 'r', encoding='utf-8')
    json_content = [json.load(f)]
    send.send_result(json_content, "判定詳細", "判定詳細")
    return
