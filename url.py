import socket
import ssl
import base64
import time

DEFAULT_FILE = "file:///hello.txt"

# Global cache dictionary
cache = {}

# Global dictionary to store connections
connections = {}

def get_connection(scheme, host, port, is_redirect=False):
    connection_key = (scheme, host, port)
    if connection_key in connections and not is_redirect:
        return connections[connection_key]
    
    s = socket.socket(
        family=socket.AF_INET, 
        type=socket.SOCK_STREAM, 
        proto=socket.IPPROTO_TCP
    )
    
    if scheme == 'https':
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)
    
    s.connect((host, port))
    connections[connection_key] = s
    return s

class URL:
    def __init__(self, url=DEFAULT_FILE, is_redirect=False):
        self.is_redirect = is_redirect
        
        if url.startswith('data:'):
            self.scheme = 'data'
            self.host = ''
            self.port = None
            self.path = url[5:]  # Remove 'data:' prefix
            return

        # Handle file paths
        if url.startswith('/') or ':' not in url:
            self.scheme = 'file'
            self.host = ''
            self.path = url
            self.port = None
            return
        
        # Scheme: Indicates the protocol (e.g., 'http', 'https')
        self.scheme, url = url.split("://", 1)

        # Adjust scheme for view-source
        if self.scheme == "view-source":
            self.scheme = "view-source"

        # Ensure there's a path, even if it's just "/"
        if "/" not in url:
            url = url + "/"
        
        # Host: The domain name or IP address of the server
        # Path: The specific resource location on the server
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # Port: The network port to connect to
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
            
        # Default is 443 for HTTPS, 80 for HTTP
        if not hasattr(self, 'port'):
            self.port = 443 if self.scheme == 'https' else 80

        print(f"URL: {self.scheme}://{self.host}:{self.port}{self.path}")


    def request(self):
        print(f"Requesting {self.scheme}://{self.host}:{self.port}{self.path} with redirect: {self.is_redirect}")
        cache_key = f"{self.scheme}://{self.host}{self.path}"
        if cache_key in cache:
            cached_response, expiry_time = cache[cache_key]
            if time.time() < expiry_time:
                print(f"Cache hit for {cache_key}")
                return cached_response
            else:
                print(f"Cache expired for {cache_key}")
                del cache[cache_key]

        s = get_connection(self.scheme, self.host, self.port, self.is_redirect)

        # make request
        # note: important to use \r\n for newlines instead of \n
        user_agent = "SimpleCustomBrowser/1.0"
        request = f"GET {self.path} HTTP/1.1\r\n" \
                  f"Host: {self.host}\r\n" \
                  f"Connection: close\r\n" \
                  f"User-Agent: {user_agent}\r\n" \
                  f"\r\n"
        s.send(request.encode("utf8"))

        # read response
        # makefile helper hides the loop for reading bits of the response
        # as it comes in from the socket
        # it creates a file-like object containing every byte we receive
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline().strip()
        if not statusline:
            s.close()
            return ""

        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        if status in ["301", "302"]:
            location = response_headers['location']
            new_url = self.join(location)
            print(f"redirecting to {new_url}")
            return URL(new_url, True).request()
        else:
            # read the response body
            content_length = int(response_headers.get('content-length', 0))
            content = response.read(content_length)

            cache_control = response_headers.get('cache-control', '')
            if 'no-store' not in cache_control:
                max_age = self.get_max_age(cache_control)
                if max_age is not None:
                    expiry_time = time.time() + max_age
                    cache[cache_key] = (content, expiry_time)
                    print(f"Cached {cache_key} for {max_age} seconds")

            return content
        
    def join(self, url):
        if "://" in url:
            return url
        elif url.startswith("/"):
            return self.scheme + "://" + self.host + url
        else:
            return self.scheme + "://" + self.host + self.path.rsplit("/", 1)[0] + "/" + url
        
    @staticmethod
    def get_max_age(cache_control):
        for directive in cache_control.split(','):
            if directive.strip().startswith('max-age='):
                try:
                    return int(directive.split('=')[1])
                except ValueError:
                    return None
        return None
    
def show(body):
    in_tag = False
    entity = ""
    for c in body:
        if c == "<" and not in_tag:
            in_tag = True
        elif c == ">" and in_tag:
            in_tag = False
        elif not in_tag:
            if c == "&" and not entity:
                entity = "&"
            elif entity:
                if c == ";":
                    if entity == "&lt":
                        print("<", end="")
                    elif entity == "&gt":
                        print(">", end="")
                    else:
                        print(entity + c, end="")
                    entity = ""
                elif c.isalnum():
                    entity += c
                else:
                    print(entity + c, end="")
                    entity = ""
            else:
                print(c, end="")

def load(url):
    print(f"Loading {url.scheme}")
    if url.scheme == "file":
        with open(url.path[1:], "r") as f:
            body = f.read()
    elif url.scheme == "data":
        media_type, data = url.path.split(',', 1)
        if ';base64' in media_type:
            body = base64.b64decode(data).decode('utf-8')
        else:
            body = data
    elif "view-source" in url.scheme or url.scheme in ["http", "https"]:
        body = url.request()
    
    if "view-source" in url.scheme:
        print(body)
    else:
        show(body)

if __name__ == "__main__":
    print("Starting browser...")
    import sys

    if len(sys.argv) > 1:
        load(URL(sys.argv[1]))
    else:
        load(URL())
