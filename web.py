import sys
import os
import re
from urllib.parse import urlparse
from subprocess import Popen, PIPE, TimeoutExpired, check_output
from queue import Queue
import requests
from requests.adapters import HTTPAdapter
from pyquery import PyQuery as pq
from bottle import hook, get, post, run, template, request, response, abort, static_file
import paste
from go_translator.go_translator import GoTranslator as Translator


translator = Translator()

def get_with_retry(url, max_retries=5):
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=max_retries))
    s.mount('https://', HTTPAdapter(max_retries=max_retries))
    try:
        return s.get(url)
    except:
        print(sys.exc_info())
        return None

def get_charset(html):
    d = pq(html)
    charset = d.find('head meta[charset]')
    if len(charset) > 0:
        return charset.attr('charset')
    charset = d.find('head meta[http-equiv="content-type"]')
    if len(charset) > 0:
        match = re.search(r'charset=([^;]*)', charset.attr('content'))
        if match:
            return match.group(1)
    charset = d.find('head meta[http-equiv="Content-Type"]')
    if len(charset) > 0:
        match = re.search(r'charset=([^;]*)', charset.attr('content'))
        if match:
            return match.group(1)
    return None

def set_charset(d, charset):
    charset = d.find('head meta[charset]')
    if len(charset) > 0:
        charset.attr('charset', 'UTF-8')
    charset = d.find('head meta[http-equiv="content-type"]')
    if len(charset) > 0:
        match = re.search(r'charset=([^;]*)', charset.attr('content'))
        if match:
            charset.attr('content', re.sub(r'(?<=charset=)[^;]*', 'UTF-8', charset.attr('content')))
    charset = d.find('head meta[http-equiv="Content-Type"]')
    if len(charset) > 0:
        match = re.search(r'charset=([^;]*)', charset.attr('content'))
        if match:
            charset.attr('content', re.sub(r'(?<=charset=)[^;]*', 'UTF-8', charset.attr('content')))

def uni_pq_from(url):
    r = get_with_retry(url)
    if r is None:
        return None

    charset = get_charset(r.content)
    r.encoding = r.apparent_encoding if charset is None else charset
    d = pq(r.text)
    set_charset(d, 'UTF-8')
    encode = r.encoding.upper()
    if encode == 'EUC-KR' or encode == 'KSC5601':
        d.attr('lang', 'ko')
    elif encode == 'GB2312':
        d.attr('lang', 'zh')
    return d


@hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'

@post('/translate')
def translate():
    text = request.forms.get('text', '')
    fro = request.forms.get('fro', '')
    to = request.forms.get('to', '')
    headline = request.forms.get('headline', 'false')
    if text == '' or fro == '':
        return ''
    translate = lambda t: translator.translate(t, fro + to)
    if fro == 'CH' and headline == 'true':
        result = ' '.join(map(translate, text.split(' ')))
    else:
        result = translate(text)
    return result

@get('/translate-web-page')
def translate_web_page():
    translator.load_dic()
    url = request.query.get('url', '')
    if url == '':
        return 'NG'
    d = uni_pq_from(url)
    d('script').remove()
    head = d('head')
    base = head.children('base')
    if len(base) == 0:
        head_children = head.children('*')
        if len(head_children) > 0:
            d(head.children('*')[0]).before('<base>')
        else:
            head.append('<base>')
        base = head.children('base')
    parsed_url = urlparse(url)
    base.attr['href'] = parsed_url.scheme + '://' + parsed_url.netloc + parsed_url.path
    parsed_url = urlparse(request.url)
    head.append('<script src="{}://{}/js/translate.js"> </script>'.format(parsed_url.scheme, parsed_url.netloc)) # pyQueryのバグ？ </script>の前に文字がないと<script>が開放になる
    head.append('<style>* {font-family: "SF Pro JP","SF Pro Text","SF Pro Icons","Hiragino Kaku Gothic Pro","ヒラギノ角ゴ Pro W3","メイリオ","Meiryo","ＭＳ Ｐゴシック","Helvetica Neue","Helvetica","Arial",sans-serif !important;}</style>')
    if 'sports.sina.cn' in url: # 新浪体育のモバイルサイト。フォントをJSで初期化するのでその代わりを務める
        d('html').attr('style', 'font-size: 62px;') # 新浪体育のモバイルサイト。フォントをJSで初期化するのでその代わりを務める
    result = d.outerHtml()
    return result

@get('/js/<filepath:path>')
def images(filepath):
    return static_file(filepath, root='./public/js/')


@get('/')
def index():
    return template("""
    <form action="http://35.203.161.100/gnugo" method="post">
    <input type="text" name="move" value="est">
    <input type="text" name="sgf" value="(;SZ[19])">
    <input type="text" name="num">
    <button>Submit</button>
    </form>
    """)


gnugo_long_lock = Queue() # finishかaftermathの場合、1リクエストずつ処理する。
gnugo_long_lock.put(1, block=False)
count = 0
@post('/gnugo')
def gnugo():
    TIMEOUT = 29
    print('gnugo')
    global count
    count += 1
    c = count
    print('gnugo start', c)

    sgf = request.forms.sgf
    if not (sgf and request.forms.move == 'est'):
        print('gnugo Bad Request', c)
        abort(400, 'Bad Request')

    method = request.forms.get('method', 'estimate')
    if method != 'estimate':
        try:
            gnugo_long_lock.get(block=True, timeout=10)
        except:
            print('gnugo wait timeout', c)
            abort(408, 'Request Timeout')
            return
    args = [
        'gnugo',
        '--' + request.forms.get('rule', 'japanese') + '-rules',
        '--score',
        method,
        '--infile',
        '-'
    ]
    mn = request.forms.get('mn')
    if mn:
        args.extend(['--until', mn])
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=False, universal_newlines=True)
    try:
        outs, errs = p.communicate(input=sgf, timeout=TIMEOUT)
        print('gnugo done', c)
        return outs
    except TimeoutExpired:
        p.kill()
        print('gnugo process timeout', c)
        abort(408, 'Request Timeout')
    finally:
        if method != 'estimate':
            gnugo_long_lock.put(1, block=False)


#app = default_app()
run(server='paste', host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
