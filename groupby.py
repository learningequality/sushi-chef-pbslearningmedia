import json
import re
from collections import Counter
text = []
with open("shares.txt") as f:
    text.extend(f.readlines())
with open("modifys.txt") as f:
    text.extend(f.readlines())

text = [json.loads(x) for x in text]

chunks = Counter()
for t in text:
    print(t)
    bits = re.split('[:|]',t)
    assert ":" not in ''.join(bits), t
    assert "|" not in ''.join(bits), t
    chunks.update([x.lower().strip() for x in bits])

keywords = []
for x,y in chunks.most_common():
    if y>5 \
        and not x.startswith("segment") \
        and not x.startswith("chapter") \
        and not x.startswith("part ")\
        and not x.startswith("topic "):
            keywords.append(x)
with open("keywords.json", "w") as f:
    f.write(json.dumps(keywords))

