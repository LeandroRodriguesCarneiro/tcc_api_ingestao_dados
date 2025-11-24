import asyncio

from .consumer.document_classifier_worker import DocumentClassifierWorker
from .consumer.pdf_splitter_worker import PDFSplitterWorker
from .consumer.docx_splitter_worker import DocxToPdfSplitterWorker
from .consumer.index_worker import IndexWorker

if __name__ == "__main__":
    import sys

    worker_map = {
        'document_spliter': DocumentClassifierWorker,
        'pdf_worker': PDFSplitterWorker,
        'docx_worker': DocxToPdfSplitterWorker,
        'index_worker': IndexWorker
    }

    if len(sys.argv) < 2 or sys.argv[1] not in worker_map:
        print("Uso: python worker.py [document_spliter|pdf_worker]")
        sys.exit(1)

    worker = worker_map[sys.argv[1]]()
    asyncio.run(worker.start())