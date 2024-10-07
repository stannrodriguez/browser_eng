import os
import importlib.util

class EmojiCache:
    def __init__(self, emoji_folder_path):
        self.cache = {}
        self.emoji_folder_path = emoji_folder_path

    def get_emoji(self, emoji_code):
        if emoji_code not in self.cache:
            emoji_file_path = os.path.join(self.emoji_folder_path, f"{emoji_code}.py")
            if os.path.exists(emoji_file_path):
                # Dynamically import the emoji file
                spec = importlib.util.spec_from_file_location(emoji_code, emoji_file_path)
                emoji_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(emoji_module)
                
                # Assuming each emoji file has a 'emoji' variable
                self.cache[emoji_code] = emoji_module.emoji
            else:
                # Handle case when emoji file doesn't exist
                self.cache[emoji_code] = None
        return self.cache[emoji_code]
