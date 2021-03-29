import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formatdate
import os
import setting

FROM_ADDRESS = 'rakutanbot@gmail.com'
ENDPOINT = os.environ["endpoint"]
PASSWORD = os.environ["gmail_pass"]
SUBJECT = '【京大楽単bot】認証リンクのお知らせ'
BODY = """京大楽単botをご利用いただきありがとうございます。\n
過去問閲覧機能有効化のための認証リンクをお送りします。\n\n
【認証リンク】\n"""

FOOTER = """\n\n
----------
京大楽単bot運営
お問い合わせ：support@das82.com
"""


class Gmail:
    def __init__(self, to, code):
        self.to_addr = to
        self.from_addr = 'rakutanbot@gmail.com'
        self.code = code

    def create_message(self):
        verificationAddress = "{}/verification?code={}".format(ENDPOINT, self.code)
        msg = MIMEText(BODY + verificationAddress + FOOTER)
        msg['Subject'] = SUBJECT
        msg['From'] = str(Header('京大楽単bot <rakutanbot@gmail.com>'))
        msg['To'] = self.to_addr
        msg['Date'] = formatdate()
        return msg

    def send(self, msg):
        smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
        smtpobj.ehlo()
        smtpobj.starttls()
        smtpobj.ehlo()
        smtpobj.login(FROM_ADDRESS, PASSWORD)
        smtpobj.sendmail(self.from_addr, self.to_addr, msg.as_string())
        smtpobj.close()

    def sendVerificationCode(self):
        try:
            message = self.create_message()
            self.send(message)
            return True
        except:
            return False
