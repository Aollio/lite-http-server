import socket, threading, os

"""
A simple lite static web server based Python with **less 200 line**  
"""

log = print

STATIC_DIR = 'static'
PAGE_404 = '404.html'
PAGE_METHOD_NOT_SUPPORT = 'method_not_support.html'
REQUEST_MAX_LENGTH = 1024 * 1024

HEADER_CONTENT_TYPE = ('Content-Type', 'text/html; charset=UTF-8')
RESPONSE_FIRST_VERSION = 'HTTP-Version: HTTP/1.0'

static_list = []


class Request():
    def __init__(self, orign_request, addr):
        self.path = None
        self.method = None
        self.signature = None
        self.headers = dict()
        self.body = None
        self.orignal_request = orign_request

        self.host, self.port = addr

        self.__parse_request__(orign_request)

    def __parse_request__(self, request):
        twopart = [x for x in request.split('\r\n\r\n') if x]
        self.__parse_headers_and_signature__(twopart[0])
        if len(twopart) == 2:
            # request have body
            self.body = twopart[1]

    def __parse_headers_and_signature__(self, headers_part):
        lines = headers_part.split("\r\n")
        self.signature = lines[0]
        # headers of request
        for header in range(1, len(lines)):
            if lines[header].startswith('Host'):
                self.headers['Host'] = lines[header].split(":")[1:]
                continue
            item = lines[header].split(":", 2)
            self.headers[item[0]] = item[1].strip()

        # parse like 'GET / HTTP/1.1'
        self.method, self.path, *other = self.signature.split(' ')


class Response():
    """
    Http Response. Note: The body's type is bytes
    """

    def __init__(self, status=200, headers={}, body=None, message='ok'):
        self.status = status
        self.headers = headers
        self.body = body
        self.message = message

    @classmethod
    def ok(cls, body=None):
        res = Response(body=body)
        res.body = body
        if body:
            res.headers['Content-Length'] = str(len(body))
        return res

    @classmethod
    def not_found(cls):
        return Response(status=404, message='Not Found')

    @classmethod
    def bad_request(cls):
        return Response(status=400, message='Bad Request')

    def source_view(self):
        """
        将Response转换为Source模式, Type is Bytes
        """
        header_of_response = str()
        signature = ' '.join([RESPONSE_FIRST_VERSION, str(self.status), self.message])
        headers_str = str()

        for title, content in self.headers.items():
            headers_str += ': '.join([title, content])
            headers_str += '\r\n'
        headers_str = headers_str[:-2]  # 去除最后多的一个 '\r\n'
        body = self.body
        header_of_response += '\r\n'.join([signature, headers_str])
        response = bytes(header_of_response + '\r\n\r\n', encoding='utf-8')
        if body:
            response += body
        return response


def file(page) -> bytes:
    """
    Open file and return it's content(type:bytes)
    """
    with open(os.path.join(STATIC_DIR, page), 'rb') as file:
        body = file.read()
    return body


def handle_get_request(request) -> Response:
    path = request.path
    if path == '/':
        return Response.ok(body=file('index.html'))
    global static_list
    if not static_list:
        static_list = os.listdir(STATIC_DIR)
    if path[1:] in static_list:
        return Response.ok(body=file(path[1:]))
    else:
        return Response.ok(body=file(PAGE_404))


def method_not_support(method) -> Response:
    try:
        body = file(PAGE_METHOD_NOT_SUPPORT)
        return Response(405, body=body, message='Method %s Not Allowed' % method)
    except FileNotFoundError as e:
        return Response.bad_request()


def handle_request(request: Request) -> Response:
    if request.method.lower() == 'get':
        return handle_get_request(request)
    if request.method.lower() == 'options':
        return Response().ok()
    return method_not_support(request.method.lower())


def after_handle_response(response):
    # handle cross request
    # 处理跨域请求 可以用于测试
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers[
        "Access-Control-Allow-Headers"] = ("Content-Type,Content-Length, "
                                           "Authorization, Accept,X-Requested-With")
    response.headers["Access-Control-Allow-Methods"] = "PUT,POST,GET,DELETE,OPTIONS"


def accept_socket(sock: socket, addr):
    ori_request = sock.recv(REQUEST_MAX_LENGTH)
    # parse original request to the special format for human
    request = Request(ori_request.decode('utf-8'), addr)
    log("Accept new http request: %s" % request.signature)
    log("   original http request:\n", ori_request)

    response = handle_request(request)
    after_handle_response(response)
    response_bytes = response.source_view()

    log('Send http response:', response_bytes)
    sock.send(response_bytes)
    sock.close()


def start(host, port):
    """start web server, it will run forever
    """
    global _main
    _main = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _main.bind((host, port))
    _main.listen()
    while True:
        sock, addr = _main.accept()
        log('Accept new connection %s:%s' % addr)
        threading.Thread(target=accept_socket, args=(sock, addr)).start()


if __name__ == '__main__':
    start("0.0.0.0", 8080)
