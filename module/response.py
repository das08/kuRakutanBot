import module.func as fn

response = {
    "help": fn.helps,
    "Help": fn.helps,
    "ヘルプ": fn.helps,
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
