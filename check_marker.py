
import pathlib, sys

text = pathlib.Path('src/uiao_core/cli/app.py').read_text(encoding='utf-8').replace('\r\n', '\n')

# Verify the marker exists before touching anything
tail = text[-200:]
print('Last 200 chars of app.py:')
print(repr(tail))
