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

class Tag:
    def __init__(self, tag):
        self.tag = tag

def lex(body):
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text

class Browser:
    def __init__(self):
        self.window = tkinter.Tk() 
        self.width, self.height = WIDTH, HEIGHT
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack(fill=tkinter.BOTH, expand=False)
        
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        # Only works on macOS and Windows, not Linux
        self.window.bind("<MouseWheel>", self.on_mousewheel)
        # Bind to the <Configure> event to handle resizing
        self.window.bind("<Configure>", self.on_resize)

    def on_resize(self, e):
        self.width = e.width
        self.height = e.height
        self.canvas.config(width=self.width, height=self.height)
        self.display_list = layout(self.text, self.width)
        self.max_scroll = max(y for x, y, c in self.display_list) - self.height + VSTEP
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
        for x, y, c in self.display_list:
            if y > self.scroll + self.height: continue
            if y + VSTEP < self.scroll: continue

            if len(c) == 1 and ord(c) > 127:  # Simple check for non-ASCII characters
                emoji_code = hex(ord(c))[2:].lower()
                emoji_img = load_emoji(emoji_code)
                if emoji_img:
                    self.canvas.create_image(x, y - self.scroll, image=emoji_img, anchor="nw")
                    continue

            self.canvas.create_text(x, y - self.scroll, text=c)

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
        self.display_list = layout(self.text, self.width)
        self.max_scroll = max(y for x, y, c in self.display_list) - self.height + VSTEP
        self.scroll = 0
        self.draw()

def layout(text, width):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP

    
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP

        # end the current line and start a new one when it sees a newline character
        if c == '\n':
            cursor_y += VSTEP
            cursor_x = HSTEP
            continue

        if cursor_x >= width - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP

    return display_list

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()