"""One reusable local parser process per API process, with a hard deadline."""
import json
import multiprocessing
import os


def run_worker(pipe):
    # OCR dependencies may write diagnostics containing extracted values.
    with open(os.devnull, 'wb') as sink, pipe:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
        pipe.send_bytes(b'ready')
        while True:
            try:
                job = pipe.recv()
            except EOFError:
                return
            try:
                from .document_analysis import analyze_document
                result = analyze_document(**job)
            except Exception:
                result = None
            encoded = json.dumps(result, ensure_ascii=False).encode('utf-8')
            pipe.send_bytes(encoded if len(encoded) <= 262_144 else b'null')


class AnalysisWorker:
    def __init__(self, timeout=60):
        self.timeout = timeout
        self.context = multiprocessing.get_context('spawn')
        self.process = self.pipe = None

    def close(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.kill()
            self.process.join()
            self.process.close()
            self.pipe.close()
            self.process = self.pipe = None

    def run(self, **job):
        try:
            if self.process is None:
                parent, child = self.context.Pipe()
                process = self.context.Process(target=run_worker, args=(child,), daemon=True)
                try:
                    process.start()
                except OSError:
                    parent.close()
                    return None
                finally:
                    child.close()
                self.pipe, self.process = parent, process
                if not self.pipe.poll(10) or self.pipe.recv_bytes(16) != b'ready':
                    self.close()
                    return None
            self.pipe.send(job)
            if not self.pipe.poll(self.timeout):
                self.close()
                return None
            return json.loads(self.pipe.recv_bytes(262_144))
        except (EOFError, OSError):
            self.close()
            return None
