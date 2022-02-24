#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandocfilters
from pandocfilters import toJSONFilters, BulletList, DefinitionList, SoftBreak, Code, Strong, CodeBlock, Header, Plain, \
    Table, Para, Link, BlockQuote, Emph, RawBlock, RawInline, HorizontalRule, \
    Str, Span, Space, walk, Div, LineBreak
import sys
import re

# sphinx-js 처리를 위한 전역 변수
jsf = dict()
bookmarks = dict()


def log(value):
    sys.stderr.write(value + '\n')


# 헤더 참조 형식으로 문자 변환
def reference(code):
    toc = '#'
    idx = 0
    last = -1
    for ch in code:
        if ch.isupper():
            if idx == 0 or last == idx - 1:
                toc += ch.lower()
            else:
                toc += '-' + ch.lower()
            last = idx
        else:
            toc += ch
        idx += 1
    return toc


# Sphinx JS format converter
def sphinx_js(key, value, format, metadata):
    global jsf
    jsf['count'] += 1
    if 'sub_count' in jsf:
        jsf['sub_count'] += 1

    if key == 'Para' and (jsf['count'] == 0 or ('sub_count' in jsf and jsf['sub_count'] == 0)):
        # 하위 함수가 존재하는 경우를 대비하여 패키지 명 추출
        if jsf.get('package') is None:
            func = pandocfilters.stringify(value)
            idx = func.rfind('.')
            if idx >= 0:
                jsf['package'] = func[0:idx]
        # 함수명을 header로 설정
        if jsf.get('header') is None:
            jsf['header'] = True
            level = 4
            func = value[0].get('c')
            if jsf.get('package') is not None and jsf.get('sub_function') is not None:
                value[0]['c'] = jsf.get('package') + '.' + func
                level = 5
            log('function: ' + pandocfilters.stringify(value))
            return Header(level, ['', [], []], value)
    elif key == 'BulletList' and jsf['count'] == 0:  # iOS의 instance method 지시자가 붙는 경우
        jsf['count'] = -1
        value[0][0]['c'] = [Str('-'), Space()] + value[0][0]['c']
        return [sphinx_js('Para', value[0][0]['c'], format, metadata), BulletList(value[1:])]
    elif key == 'Para':
        # JSON 구문으로 판단 CodeBlock으로 변환
        if isinstance(value[0]['c'], str) and pandocfilters.stringify(value).strip().startswith('{'):
            return CodeBlock(['', ['json'], []], pandocfilters.stringify(value))
    elif key == 'DefinitionList':
        items = dict()
        for term, desc in value:
            _type = term[0]['c']
            if _type not in items:
                items[_type] = []
            if _type == 'param':  # 인자 값
                if len(term) == 5:  # 인자명, 타입, 설명 구조
                    param_name = term[4]
                    param_type = term[2]
                    paragraph = [param_name, Str('('), Strong([param_type]), Str(')'), Space(), Str('-'), Space()]
                    if len(desc[0]) > 0:
                        paragraph += desc[0][0]['c']
                    items['param'].append([Plain(paragraph)])
                elif len(term) == 3:  # 인자명, 타입 참조 구조
                    param_name = term[2]
                    paragraph = [param_name, Str('('), Strong([param_name]), Str(')'), Space(), Str('-'), Space()]
                    if len(desc[0]) > 0:
                        paragraph += desc[0][0]['c']
                    items['param'].append([Plain(paragraph)])
            elif _type == 'type':
                p = items['param']
                assert len(p) > 0, 'Type 참조 대상 Parameter가 없습니다.'
                paragraph = p[len(p) - 1][0]['c']
                assert len(desc[0]) > 0 and isinstance(desc[0][0], dict), 'Type 참조 정의를 찾을 수 없습니다.'
                p[len(p) - 1][0]['c'] = paragraph[0:2] + desc[0][0]['c'] + paragraph[3:]
            elif _type == "returns":
                items['returns'].append(desc[0])
            elif _type == "return":
                assert len(desc[0]) > 0 and isinstance(desc[0][0], dict), 'Return Type 정의를 찾을 수 없습니다.'
                items[_type].append(desc[0])
            elif _type == "rtype":
                items[_type] += [desc[0]]

        block = []
        for _key in ["param", "returns", "return", "rtype"]:
            if _key not in items:
                continue
            title = {"param": "Arguments", "returns": "Returns", "return": "Returns", "rtype": "Return Types"}
            item = items.get(_key)
            block.append(Para([Strong([Str(title[_key])])]))
            block.append(BulletList(item))
        return Div(['', [], []], block)
    elif key == 'Div':
        [[ident, classes, kvs], code] = value
        if 'js-function' in classes:  # 하위 함수에 대한 sphinx-js를 markdown 형식으로 변환
            jsf['header'] = None
            jsf['sub_function'] = True
            jsf['sub_count'] = -1
            return Div([ident, ['js-sub-function'], kvs], walk(code, sphinx_js, format, metadata))


def sphinx_table(key, value, format, metadata):
    def func(key, value, format, metadata):
        if key == "LineBlock":
            value[0] = [RawInline("html", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")] + value[0]

    if key == "BlockQuote":
        return walk(value, func, format, metadata)


def sphinx_blockquote(key, value, format, metadata):
    if key == "BlockQuote":
        return walk(value, sphinx_blockquote, format, metadata)
    else:
        return _filter(key, value, format, metadata)


def _filter(key, value, format, metadata):
    if key == 'BlockQuote':
        return walk(value, sphinx_blockquote, format, metadata)
    elif key == 'DefinitionList':
        return
    elif key == 'Div':
        [[ident, classes, kvs], code] = value
        if 'title' in classes:
            code[0]['c'][0] = Strong([code[0]['c'][0]])
            return code
        elif 'versionadded' in classes:  # sphinx directive
            return Para([Strong([Str('New'), Space(), Str('in'), Space(), Str('version'), Space()] + code[0]['c'])])
        elif 'versionchanged' in classes:  # sphinx directive
            return Para([Strong([Str('Changed'), Space(), Str('in'), Space(), Str('version'), Space()] + code[0]['c'])])
        elif 'js-function' in classes:  # sphinx-js를 markdown 형식으로 변환
            global jsf
            jsf = {'count': -1}
            div = Div([ident, classes, kvs], walk(code, sphinx_js, format, metadata))
            return div
        elif 'note' in classes:  # RST의 Note 인용문 보정
            return BlockQuote(code)
        elif 'warning' in classes:  # RST의 Warning 인용문 보정
            code = code + [RawBlock('markdown', '{.is-warning}')]
            return BlockQuote(code)
    elif key == 'Code':  # 참조 Link로 변환
        [[ident, classes, kvs], code] = value
        if pandocfilters.get_value(kvs, 'role', '')[0] == 'ref':
            if code in bookmarks:
                bookmark = bookmarks[code]
                return Link(['', [], []], bookmark['caption'], [bookmark['bookmark'], ''])
            else:
                log("존재하지 않는 헤더 발견 : " + str(code))
            return Link(['', [], []], [Str(code)], [reference(code), ''])
    elif key == 'CodeBlock':  # CodeBlock Highlight Code 보정
        [[ident, classes, kvs], code] = value
        if 'objective-c' in classes:  # Objective-C
            return CodeBlock(['', ['objc'], []], code)
    elif key == "Table":
        value[4] = walk(value[4], sphinx_table, format, metadata)
    elif key == "SoftBreak":
        return RawInline('html', "<br/>\n")


def init(key, value, format, metadata):
    global bookmarks
    if key == 'Para' and len(value) >= 3:  # RST의 잘못된 제목 형식 보정
        idx = 0
        found = False
        for i in value:
            if ('c' in i and isinstance(i['c'], str)) and found and re.match(r'^([=]{2,}|[-]{2,})?$', i['c']) is not None:
                log("비정상 타이틀 발견 : " + pandocfilters.stringify(value[:idx - 1]))
                level = 3
                if str(i['c'])[0] == '-':
                    level = 4
                if len(value) > idx + 2:
                    return [Header(level, ['', [], []], value[:idx - 1]), Para(value[idx + 2:])]
                else:
                    return [Header(level, ['', [], []], value[:idx - 1])]
            if i['t'] == 'SoftBreak':
                found = True
            else:
                found = False
            idx += 1


def header(key, value, format, metadata):
    if key == 'Header':
        [level, [ident, classes, kvs], code] = value
        if pandocfilters.stringify(code).strip().replace(" ", "") == ident:
            bookmark = '#' + str(pandocfilters.stringify(code)).strip().replace(" ", "-").lower()
            bookmarks[ident] = {'caption': code, 'bookmark': bookmark}
        else:
            bookmark = '#' + pandocfilters.stringify(code).strip().replace(" ", "-").lower()
            if re.match(r"[0-9]{1}.+", pandocfilters.stringify(code).strip()):
                bookmark = '#h-' + pandocfilters.stringify(code).strip().replace(" ", "-").replace(".", "").lower()
            bookmarks[ident] = {'caption': code, 'bookmark': bookmark}


if __name__ == '__main__':
    toJSONFilters([init, header, _filter])
