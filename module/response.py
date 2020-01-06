import module.func as fn

command = {
    "help": fn.helps,
    "Help": fn.helps,
    "ヘルプ": fn.helps,
    "テーマ変更": fn.select_theme,
    "テーマ": fn.select_theme,
    "theme": fn.select_theme,
    "色": fn.select_theme,
    "はんてい詳細": fn.rakutan_hantei,
    "詳細": fn.rakutan_hantei,
    "判定": fn.rakutan_hantei,
    "判定詳細": fn.rakutan_hantei,
    "おみくじ": fn.omikuji,
    "楽単": fn.omikuji,
    "鬼単": fn.onitan,
    "鬼単おみくじ": fn.onitan,
    "CB": fn.say_sorry,
    "京大楽単bot": fn.show_version,
    "d@s08": fn.merge,
    "@theme:default": fn.change_theme,
    "@theme:yellow": fn.change_theme,
    "@theme:blue": fn.say_sorry,
    "@theme:gold": fn.say_sorry2
}
