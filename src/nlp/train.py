# Import requirements
from pathlib import Path
import random
import json

from spacy import load
from spacy.util import minibatch, compounding
from spacy.tokens import Doc
from spacy.training import Example

nlp = load("es_core_news_sm")
ner = nlp.get_pipe("ner")

data = json.load(open("files/ner-training.json", encoding="latin1"))
print(data[0].keys())
train_data = [
    Example.from_dict(
        nlp(entry["text"]),
        {
            "text": entry["text"],
            "entities": [
                (lab["start"], lab["end"], lab["labels"][0])
                for lab in entry.get("label", [])
            ]
        }
    ) for entry in data
]

pipe_exceptions = ["ner", "trf_wordpiecer", "trf_tok2vec"]
unaffected_pipes = [pipe for pipe in nlp.pipe_names if pipe not in pipe_exceptions]

with nlp.disable_pipes(*unaffected_pipes):
  for iteration in range(30):
    random.shuffle(train_data)
    losses = {}
    batches = minibatch(train_data, size=compounding(4.0, 32.0, 1.001))
    
    for batch in batches:
        nlp.update(
            batch,
            drop=0.5,  # dropout - make it harder to memorise data
            losses=losses,
        )
        print("Losses", losses)

output_dir = Path('files/nlp_model/')
nlp.to_disk(output_dir)
print("Saved model to", output_dir)
