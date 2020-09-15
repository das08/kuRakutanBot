import module.func as fn

command = {
    "help": fn.helps,
    "Help": fn.helps,
    "ヘルプ": fn.helps,
    "テーマ変更": fn.selectTheme,
    "きせかえ": fn.selectTheme,
    "着せ替え": fn.selectTheme,
    "テーマ": fn.selectTheme,
    "色テーマ": fn.selectTheme,
    "色テーマ変更": fn.selectTheme,
    "theme": fn.selectTheme,
    "色": fn.selectTheme,
    "色変更": fn.selectTheme,
    "はんてい詳細": fn.rakutanHantei,
    "詳細": fn.rakutanHantei,
    "判定": fn.rakutanHantei,
    "判定詳細": fn.rakutanHantei,
    "楽単詳細": fn.rakutanHantei,

    "お気に入り": fn.getFavList,
    "お気に入り一覧": fn.getFavList,
    "おきにいり": fn.getFavList,
    "fav": fn.getFavList,
    "favs": fn.getFavList,

    "楽単おみくじ": fn.normalOmikuji,
    "おみくじ 楽単": fn.normalOmikuji,
    "おみくじ": fn.normalOmikuji,
    "楽単": fn.normalOmikuji,

    "人社おみくじ": fn.sorry,
    "おみくじ 人社": fn.sorry,
    "人社": fn.sorry,

    "鬼単おみくじ": fn.oniOmikuji,
    "おみくじ 鬼単": fn.oniOmikuji,
    "鬼単": fn.oniOmikuji,
    "鬼": fn.oniOmikuji,

    "お問い合わせ": fn.inquiry,
    "PandA": fn.cpanda,
    "panda": fn.cpanda,
    "@info": fn.cpanda,

    "CB": fn.sorry,
    "京大楽単bot": fn.showVersion,
    "d@s08": fn.checkKakomon,
    "myuid": fn.myUID,
    "@set:birdman": fn.setRichMenu,
    "@set:ad": fn.setRichMenu,
    "@set:default": fn.setRichMenu,

    "@theme:default": fn.changeTheme,
    "@theme:yellow": fn.sorry,
    "@theme:blue": fn.sorry,
    "@theme:gold": fn.unavailable
}
