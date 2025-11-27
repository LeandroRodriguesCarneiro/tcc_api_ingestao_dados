import spacy
from spacy.cli import download
from typing import List

download("pt_core_news_sm")
nlp = spacy.load("pt_core_news_sm")

def chunk_by_sentences_with_overlap(
    text: str,
    chunk_size: int = 1000,   # tamanho aproximado em caracteres
    overlap: int = 200        # overlap em caracteres
) -> List[str]:
    """
    1) Segmentar o texto em sentenças (spaCy).
    2) Agrupar sentenças até atingir chunk_size (em chars).
    3) Para overlap, retroceder sentenças suficientes para aproximar o overlap desejado.
    Preserva sentenças inteiras e evita regex frágil.
    """
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    chunks = []
    i = 0
    n = len(sentences)

    while i < n:
        curr_sentences = []
        curr_len = 0
        j = i
        while j < n and (curr_len + len(sentences[j]) + 1) <= chunk_size:
            curr_sentences.append(sentences[j])
            curr_len += len(sentences[j]) + 1
            j += 1

        if not curr_sentences:
            curr_sentences.append(sentences[j])
            curr_len = len(sentences[j])
            j += 1

        chunk_text = " ".join(curr_sentences).strip()
        chunks.append(chunk_text)

        if overlap <= 0:
            i = j
        else:
            cum = 0
            k = j
            while k - 1 >= 0 and cum < overlap:
                k -= 1
                cum += len(sentences[k]) + 1
            if k <= i:
                i = j
            else:
                i = k

    return chunks
