function post(url, data) {
    return new Promise(function(res, rej) {
        const request = new XMLHttpRequest();
        request.open('POST', url, true);
        request.onreadystatechange = function() {
            if (request.readyState !== 4) {
                // リクエスト中
            } else if (request.status !== 200) {
                rej(request.status);
            } else {
                res(request.responseText);
            }
        };
        request.send(data);
    });
}

async function translate(text, fro, to) {
    const data = new FormData();
    data.append('text', text);
    data.append('fro', fro);
    if (to) {
        data.append('to', to);
    }
    return await post(location.origin + '/translate', data);
}

async function process(dom, lang) {
    if (dom.nodeType === 3) {
        if (!/^[\x20-\x7E\s]*$/.test(dom.nodeValue)) { // ASCII文字列でないなら
            const translated = await translate(dom.nodeValue, lang);
            if (translated) {
                dom.nodeValue = translated;
            }
        }
    } else if (dom.nodeType === 1 && ['NOSCRIPT', 'SCRIPT', 'STYLE', 'IFRAME'].indexOf(dom.tagName) < 0) {
        const style = window.getComputedStyle(dom);
        if (style.display !== 'none' && style.visibility !== 'hidden') {
            await translateTree(dom, lang);
        }
    }
}

function translateTree(node, lang) {
    const promises = [];
    node.childNodes.forEach(function(e) {
        promises.push(process(e, lang));
    });
    return Promise.all(promises);
}

window.addEventListener('load', async function() {
    const match = location.search.match(/lang=([A-Z]{2})/);
    const lang = match ? match[1] : 'CH';
    document.title = await translate(document.title, lang);
    translateTree(document.body, lang);
});
