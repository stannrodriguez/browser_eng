import tkinter
import tkinter.font
from url import URL

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18    

class Text: 
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return f"Text({self.text})"

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.children = []
        self.attributes = attributes
        self.parent = parent
    
    def __repr__(self):
        return f"<{self.tag} attributes={self.attributes}>"

SELF_CLOSING_TAGS = ["area", "base", "br", "col", "command", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]
class HTMLParser:
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    def __init__(self, body):
        self.body = body
        self.unfinished = []
    
    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == '<':
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == '>':
                in_tag = False
                self.add_tag(text)
                text=""
            else:
                text += c

        if not in_tag and text: self.add_text(text)

        return self.finish()
    
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)

        parent = self.unfinished[-1] if self.unfinished else None
        node = Text(text, parent)
        parent.children.append(node)
    
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)

        if tag.startswith("/"):
            if len(self.unfinished) == 1: return

            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else: 
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)

        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        return self.unfinished.pop()
    
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                attr, value = attrpair.split("=", 1)
                attributes[attr.casefold()] = value.strip("\"'")
            else:
                attributes[attrpair.casefold()] = True
        return tag, attributes

FONTS = {}

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)

    return FONTS[key][0]

class Layout:
    def __init__(self, tree, width=WIDTH):
        self.tokens = tree
        self.width = width
        self.display_list = []

        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.is_title = False
        self.is_superscript = False
        self.is_abbr = False

        self.line = []
        self.recurse(tree)
        self.flush()

    def open_tag(self, tag):
        if tag == 'i':
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "sup":
            self.is_superscript = True
            self.size = self.normal_size // 2
        elif tag == "abbr":
            self.is_abbr = True

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "sup":
            self.is_superscript = False
            self.size = self.normal_size
        elif tag == "abbr":
            self.is_abbr = False

    def recurse(self, tree):
        if isinstance(tree, Text):
            self.text(tree)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def token(self, tok):
        if isinstance(tok, Text):
            self.text(tok)
        elif "h1" in tok.tag and 'title' in tok.tag: 
            self.is_title = True
        elif tok.tag == "/h1":
            self.is_title = False
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "sup":
            self.is_superscript = True
            self.size = self.normal_size // 2
        elif tok.tag == "/sup":
            self.is_superscript = False
            self.size = self.normal_size
        elif tok.tag == "abbr":
            self.is_abbr = True
        elif tok.tag == "/abbr":
            self.is_abbr = False
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP

    def text(self, tok):
        if not isinstance(tok, Text):
            return
        elif self.is_title:
            font = get_font(self.size, self.weight, self.style)
            lines = tok.text.split("\n")
            for line in lines:
                if line.strip():
                    line_width = font.measure(line)
                    x = (self.width - line_width) / 2
                    self.display_list.append((x, self.cursor_y, line, font, 0))
                    self.cursor_y += font.metrics("linespace")
            return
        else:
            for word in tok.text.split():
                self.word(word)
        
    def word(self, word):
        if self.is_abbr:
            self.abbr_word(word)
            return
        
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w > self.width - HSTEP:
            self.flush()

        if self.is_superscript:
            y_offset = font.metrics("ascent") / 2
        else:
            y_offset = 0

        self.line.append((self.cursor_x, word, font, y_offset))
        self.cursor_x += w + font.measure(" ")

    def abbr_word(self, word):
        normal_font = get_font(self.size, self.weight, self.style)
        small_font = get_font(int(round(self.size * 0.8,2)), "bold", self.style)
        
        x = self.cursor_x
        for char in word:
            if char.islower():
                font = small_font
                char = char.upper()
            else:
                font = normal_font
            
            w = font.measure(char)
            if x + w > self.width - HSTEP:
                self.flush()
                x = HSTEP
            
            y_offset = 0 if not self.is_superscript else -normal_font.metrics("ascent") // 2
            self.line.append((x, char, font, y_offset))
            x += w
        
        self.cursor_x = x + normal_font.measure(" ")

    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font, y_offset in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font, y_offset in self.line:
            y = baseline - font.metrics("ascent") + y_offset
            self.display_list.append((x, y, word, font, y_offset))
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []

counter = 0
class Browser:
    def __init__(self):
        self.window = tkinter.Tk() 
        self.width, self.height = WIDTH, HEIGHT
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.is_loaded = False

        self.scroll = 0
        self.max_scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        # Only works on macOS and Windows, not Linux
        self.window.bind("<MouseWheel>", self.on_mousewheel)
        # Bind to the <Configure> event to handle resizing
        self.window.bind("<Configure>", self.on_resize)

    def on_resize(self, e):
        # Don't resize until the page is loaded for the first time
        if not self.is_loaded and self.canvas.winfo_width() >= WIDTH and self.canvas.winfo_height() >= HEIGHT:
            self.is_loaded = True
            return

        # We should update the canvas size if:
        # 1. The page has not fully loaded yet
        # 2. The user has resized the window
        should_update = False
        if not self.is_loaded:
            self.canvas.config(width=WIDTH, height=HEIGHT)
            should_update = True

        is_width_resized = not self.width in range(e.width - 7, e.width + 7)
        is_height_resized = not self.height in range(e.height - 7, e.height + 7)
        if is_width_resized or is_height_resized:
            self.width = e.width
            self.height = e.height
            self.canvas.config(width=self.width, height=self.height)
            should_update = True

     
        if should_update:
            self.display_list = Layout(self.nodes, e.width).display_list
            self.max_scroll = max(y for x, y, c, font, y_offset in self.display_list) - self.height + VSTEP
            self.scroll = min(self.scroll, self.max_scroll)
            self.draw()


    def scrolldown(self, e):
        if self.scroll < self.max_scroll:
            self.scroll = min(self.scroll + SCROLL_STEP, self.max_scroll)
            self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            self.scroll = max(self.scroll - SCROLL_STEP, 0)
            self.draw()

    def on_mousewheel(self, e):
        if e.delta > 0:
            self.scrollup(e)
        else:
            self.scrolldown(e)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font, y_offset in self.display_list:
            if y > self.scroll + self.height: continue
            if y + font.metrics("linespace") < self.scroll: continue

            self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

        # Draw scrollbar
        if self.max_scroll > 0:
            scrollbar_height = max(20, self.height * (self.height / (self.max_scroll + self.height)))
            scrollbar_position = self.scroll / self.max_scroll * (self.height - scrollbar_height)
            self.canvas.create_rectangle(
                self.width - 10, scrollbar_position,
                self.width, scrollbar_position + scrollbar_height,
                fill="blue"
            )


    def load(self, url):  
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        self.display_list = Layout(self.nodes, self.width).display_list
        self.max_scroll = max(y for x, y, c, font, y_offset in self.display_list) - self.height + VSTEP
        self.scroll = 0
        self.draw()

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
