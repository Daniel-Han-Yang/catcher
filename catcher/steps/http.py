from requests import request

from catcher.steps.step import Step
from catcher.utils.file_utils import read_file
from catcher.utils.misc import fill_template, fill_template_str
from catcher.utils.logger import debug


class Http(Step):
    def __init__(self, body: dict) -> None:
        super().__init__(body)
        [method] = [k for k in body.keys() if k != 'register']  # get/post/put...
        self._method = method.lower()
        conf = body[method]
        self._url = conf['url']
        self._headers = conf.get('headers', {})
        self._body = None
        self._code = conf.get('response_code', 200)
        if self.method != 'get':
            self._body = conf.get('body', None)
            if self.body is None:
                self._file = conf['body_from_file']

    @property
    def method(self) -> str:
        return self._method

    @property
    def body(self) -> any:
        return self._body

    @property
    def file(self) -> str:
        return self._file

    @property
    def url(self) -> str:
        return self._url

    @property
    def headers(self) -> dict:
        return self._headers

    @property
    def code(self) -> int:
        return self._code

    def action(self, includes: dict, variables: dict) -> dict:
        url = fill_template(self.url, variables)
        headers = dict(
            [(fill_template_str(k, variables), fill_template_str(v, variables)) for k, v in self.headers.items()])
        body = self.__form_body(variables)
        debug('http ' + str(self.method) + ' ' + str(url) + ', ' + str(headers) + ', ' + str(body))
        r = request(self.method, url, params=None, headers=headers, data=body)
        if r.status_code != self.code:
            raise RuntimeError('Code mistatch: ' + str(r.status_code) + ' vs ' + str(self.code))
        try:
            response = r.json()
        except ValueError:
            response = r.text
        return self.process_register(variables, response)

    def __form_body(self, variables):
        if self.method == 'get':
            return None
        body = None
        if self.body is None:
            body = read_file(fill_template_str(self.file, variables))
        return fill_template_str(body, variables)
