#!/usr/bin/env python3
import json
from random import random
from pathlib import Path

THIS_DIR = Path(__file__).parent

data = []
no_strings = True
for i in range(1_000):
    if random() > 0.5:
        if no_strings:
            data.append([v*random() for v in range(int(random()*500))])
        else:
            data.append({str(random()): v*random() for v in range(int(random()*500))})
    else:
        data.append(list(range(int(random()*500))))

(THIS_DIR / 'big.json').write_text(json.dumps(data, separators=(',', ':')))
