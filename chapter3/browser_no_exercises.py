"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 3 (Formatting Text),
without exercises.
"""

import socket
import ssl
import tkinter
import tkinter.font

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wbetools
from chapter1.browser_no_exercises import URL
from chapter2.browser_no_exercises import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP, Browser

class Text:
    def __init__(self, text):
        self.text = text

    @wbetools.js_hide
    def __repr__(self):
        return "Text('{}')".format(self.text)

class Tag:
    def __init__(self, tag):
        self.tag = tag

    @wbetools.js_hide
    def __repr__(self):
        return "Tag('{}')".format(self.tag)

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
        font = tkinter.font.Font(size=size, weight=weight,
            slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

class Layout:
    def __init__(self, tokens):
        self.tokens = tokens
        self.display_list = []

        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        self.line = []
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
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
        
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    def flush(self):
        # This function is responsible for laying out a line of text and adding it to the display list.
        # It handles vertical alignment of text with different font sizes on the same line.

        # If there's no content in the current line, exit early
        if not self.line: return

        # Record the initial y position and line content for debugging
        wbetools.record("initial_y", self.cursor_y, self.line);

        # Get font metrics for each word in the line
        metrics = [font.metrics() for x, word, font in self.line]
        wbetools.record("metrics", metrics)

        # Find the maximum ascent (height above the baseline) among all fonts in the line
        max_ascent = max([metric["ascent"] for metric in metrics])

        # Calculate the baseline position for this line
        # The 1.25 factor adds some extra vertical spacing between lines
        baseline = self.cursor_y + 1.25 * max_ascent
        wbetools.record("max_ascent", max_ascent);

        # Position each word on the line
        for x, word, font in self.line:
            # Calculate the y position for this word, aligning it to the baseline
            y = baseline - font.metrics("ascent")
            # Add the word to the display list
            self.display_list.append((x, y, word, font))
            wbetools.record("aligned", self.display_list);

        # Find the maximum descent (height below the baseline) among all fonts in the line
        max_descent = max([metric["descent"] for metric in metrics])
        wbetools.record("max_descent", max_descent);

        # Update the cursor_y for the next line
        # Again, the 1.25 factor adds some extra vertical spacing
        self.cursor_y = baseline + 1.25 * max_descent

        # Reset the cursor_x for the next line
        self.cursor_x = HSTEP

        # Clear the current line buffer
        self.line = []

        # Record the final y position for debugging
        wbetools.record("final_y", self.cursor_y);

@wbetools.patch(Browser)
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.display_list = []

    def load(self, url):
        body = url.request()
        tokens = lex(body)
        print(f"\nPRINTING TOKENS {tokens}")
        self.display_list = Layout(tokens).display_list
        print(f"\nPRINTINT DISPLAY LIST {self.display_list}")
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + font.metrics("linespace") < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()