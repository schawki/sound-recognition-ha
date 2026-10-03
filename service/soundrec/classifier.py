"""YAMNet (TFLite / LiteRT) wrapper. One window = 15600 samples of 16 kHz mono float32 in [-1, 1] -> 521 scores."""
import threading
import numpy as np

SAMPLE_RATE = 16000
WINDOW = 15600  # 0.975 s


class YamnetClassifier:
    def __init__(self, model_path, threads=1):
        try:
            from ai_edge_litert.interpreter import Interpreter
        except ImportError:  # pragma: no cover - older environments
            from tflite_runtime.interpreter import Interpreter
        self._it = Interpreter(model_path=model_path, num_threads=threads)
        self._it.allocate_tensors()
        self._in = self._it.get_input_details()[0]["index"]
        outs = self._it.get_output_details()
        self._out = next(o["index"] for o in outs if tuple(o["shape"]) == (1, 521))
        self._lock = threading.Lock()

    def predict(self, window):
        """window: float32 array of 15600 samples. Returns float32 array of 521 scores."""
        x = np.asarray(window, dtype=np.float32).reshape(1, WINDOW)
        with self._lock:
            self._it.set_tensor(self._in, x)
            self._it.invoke()
            return self._it.get_tensor(self._out)[0].copy()
