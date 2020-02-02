from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage

from pdfminer.psparser import PSKeyword, PSLiteral, LIT
from pdfminer.pdftypes import PDFObjRef, resolve1


from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTContainer, LTRect, LTLine, LTTextBox
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager

from pdfminer.layout import LAParams

def display_pageno(pdffile):
    result = []
    fp = open(pdffile, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument(parser)

    pages = dict( (page.pageid, pageno) for (pageno,page)
                    in enumerate(PDFPage.create_pages(doc), 1) )

    def resolve_dest(dest):
        if isinstance(dest, str) or isinstance(dest, bytes):
            dest = resolve1(doc.get_dest(dest))
        elif isinstance(dest, PSLiteral):
            dest = resolve1(doc.get_dest(dest.name))
        if isinstance(dest, dict):
            dest = dest['D']
        if isinstance(dest, PDFObjRef):
            dest = dest.resolve()
        return dest                  

    outlines = doc.get_outlines()
    for (level,title,dest,a,se) in outlines:
        pageno = None
        pageid = None
        if dest:
            dest = resolve_dest(dest)
            pageid = dest[0].objid
            pageno = pages[pageid]
        elif a:
            action = a
            if isinstance(action, dict):
                subtype = action.get('S')
                if subtype and repr(subtype) == '/\'GoTo\'' and action.get('D'):
                    dest = resolve_dest(action['D'])
                    pageid = dest[0].objid
                    pageno = pages[pageid]
        # print (level, title, pageno, pageid)
        result.append({"level": level, "title": title, "pageno": pageno, "pageid": pageid})
    return result

pagenolst = display_pageno('./sampleh.pdf')
# print(pagenolst)

 
def find_item_recursively(layout_obj, cls):
    """
    再帰的にClassを探して、テキストボックスのリストを取得する。
    """
    # LTTextBoxを継承するオブジェクトの場合は1要素のリストを返す。
    if isinstance(layout_obj, cls):
        return [layout_obj]

    # LTContainerを継承するオブジェクトは子要素を含むので、再帰的に探す。
    if isinstance(layout_obj, LTContainer):
        items = []
        for child in layout_obj:
            items.extend(find_item_recursively(child, cls))

        return items

    return []  # その他の場合は空リストを返す。


def getLineMargin(pdffile, pageNo):
    # Layout Analysisのパラメーターを設定。縦書きの検出を有効にする。
    laparams = LAParams(detect_vertical=True)

    # 共有のリソースを管理するリソースマネージャーを作成。
    resource_manager = PDFResourceManager()

    # ページを集めるPageAggregatorオブジェクトを作成。
    device = PDFPageAggregator(resource_manager, laparams=laparams)

    # Interpreterオブジェクトを作成。
    interpreter = PDFPageInterpreter(resource_manager, device)

    with open(pdffile, 'rb') as f:
        for page in PDFPage.get_pages(f, pagenos=[pageNo]):
            interpreter.process_page(page)  # ページを処理する。
            layout = device.get_result()  # LTPageオブジェクトを取得。

            # ページ内のテキストボックスのリストを取得する。
            boxes = find_item_recursively(layout, LTTextBox)

            # テキストボックスの左上の座標の順でテキストボックスをソートする。
            # y1（Y座標の値）は上に行くほど大きくなるので、正負を反転させている。
            boxes.sort(key=lambda b: (-b.y1, b.x0))

            # 1行目はヘッダのため2行目行目のマージンを取る
            row_margin = boxes[1].y0 - boxes[2].y1
            if row_margin / boxes[1].height > laparams.line_margin:
                line_margin = row_margin / boxes[1].height
            else:
                line_margin = laparams.line_margin
        return line_margin
line_margin = getLineMargin('./sampleh.pdf', pagenolst[0]["pageno"] -1)
print(line_margin)


def getPageText(pdffile, line_margin, fromPageid):
    resulst = []

    # Layout Analysisのパラメーターを設定。縦書きの検出を有効にする。
    laparams = LAParams(detect_vertical=True, line_margin=line_margin)

    # 共有のリソースを管理するリソースマネージャーを作成。
    resource_manager = PDFResourceManager()

    # ページを集めるPageAggregatorオブジェクトを作成。
    device = PDFPageAggregator(resource_manager, laparams=laparams)

    # Interpreterオブジェクトを作成。
    interpreter = PDFPageInterpreter(resource_manager, device)

    pagestart = False
    with open(pdffile, 'rb') as f:
        for page in PDFPage.get_pages(f):
            if pagestart or page.pageid == fromPageid:
                pagestart = True
                interpreter.process_page(page)  # ページを処理する。
                layout = device.get_result()  # LTPageオブジェクトを取得。

                # ページ内のテキストボックスのリストを取得する。
                boxes = find_item_recursively(layout, LTTextBox)

                # テキストボックスの左上の座標の順でテキストボックスをソートする。
                # y1（Y座標の値）は上に行くほど大きくなるので、正負を反転させている。
                boxes.sort(key=lambda b: (-b.y1, b.x0))
                result.extend({"pageno": page.pageNo, "box": boxes})
        return result
page_boxes = getPageText('./sampleh.pdf', 1.0, pagenolst[0]["pageid"])