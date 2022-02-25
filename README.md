# pandoc-sphinxjs-filter

Pandoc filter which converts sphinx-js blocks to markdown.

````
.. js:function:: M.onReady( handler )

     .. versionchanged:: 2.1.0

     :param Function handler: Event Handler

     .. js-function:: handler( event )

         :param event: 이벤트 객체
         :type event: :ref:`PageEventObject`


     * 화면 로딩이 최종 완료시 한번만 호출
     * 데이타 초기화, 서버로의 데이타 요청 등에 사용
     * iframe 등 으로 외부 페이지 오픈시 iframe 내 페이지까지 모두 완료되야 호출됨
     * DOM Content Loaded 와는 별개로 동작함

     Example:

     .. code-block:: javascript

         M.onReady( function(e) {
             // TODO : ready event handle code here
         });

````

## Usage

Install it with pip:

```
pip install pandocfilters
```

And use it like any other pandoc filter:

```
> sed -i "" "s/js:function/js-function/g" api.rst
> pandoc -f rst -t markdown --wrap=none -o api.md --F pandoc_sphinxjs_filter.py api.rst
```
