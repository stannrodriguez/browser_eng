import tkinter
import tkinter.font
from emoji import emojis, load_emoji
from url import URL

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18    

class Text: 
    def __init__(self, text):
        self.text = text
    
    def __repr__(self):
        return f"Text({self.text})"

class Tag:
    def __init__(self, tag):
        self.tag = tag
    
    def __repr__(self):
        return f"Tag({self.tag})"

def lex(body):
    out = []
    buffer = ""
    in_tag = False
  
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer))

    return out

FONTS = {}

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)

    return FONTS[key][0]

class Layout:
    def __init__(self, tokens, width=WIDTH):
        self.tokens = tokens
        self.width = width
        self.display_list = []

        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.is_title = False

        self.line = []
        for tok in tokens:
            self.token(tok)
        self.flush()

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
                    self.display_list.append((x, self.cursor_y, line, font))
                    self.cursor_y += font.metrics("linespace")
            return
        else:
            for word in tok.text.split():
                self.word(word)
        
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w > self.width - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
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
            self.display_list = Layout(self.text, e.width).display_list
            self.max_scroll = max(y for x, y, c, font in self.display_list) - self.height + VSTEP
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
        for x, y, word, font in self.display_list:
            if y > self.scroll + self.height: continue
            if y + font.metrics("linespace") < self.scroll: continue

            if len(word) == 1 and ord(word) > 127:  # Simple check for non-ASCII characters
                emoji_code = hex(ord(word))[2:].lower()
                emoji_img = load_emoji(emoji_code)
                if emoji_img:
                    self.canvas.create_image(x, y - self.scroll, image=emoji_img, anchor="nw")
                    continue

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
        self.text = lex(body)
        self.display_list = Layout(self.text, self.width).display_list
        self.max_scroll = max(y for x, y, c, font in self.display_list) - self.height + VSTEP
        self.scroll = 0
        self.draw()


if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()