import asyncio

from .consumer.document_classifier_worker import DocumentClassifierWorker
from .consumer.pdf_splitter_worker import PDFSplitterWorker

if __name__ == "__main__":
    import sys

    worker_map = {
        'document_spliter': DocumentClassifierWorker,
        'pdf_worker': PDFSplitterWorker,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in worker_map:
        print("Uso: python worker.py [document_spliter|pdf_worker]")
        sys.exit(1)

    worker = worker_map[sys.argv[1]]()
    asyncio.run(worker.start())