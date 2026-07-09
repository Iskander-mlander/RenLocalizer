import os
import sys

sys.path.append(os.getcwd())
try:
    from src.core.parser import RenPyParser
except Exception as e:
    print(e)
    sys.exit(1)

p = RenPyParser()

line = r'                                textbutton "{size=+10} Jogging with Abigail" action Notify("Chat with Abigail in the park on the weekend afternoons,\nand ask her to go jogging"):'

m = p.action_call_re.match(line)
quote = m.group('quote')
raw, text = p._extract_string_raw_and_unescaped(quote, 1, [line])
print("Text is:", repr(text))
print("Is Meaningful:", p.is_meaningful_text(text))
