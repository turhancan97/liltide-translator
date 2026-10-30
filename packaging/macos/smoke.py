"""Explicit, offline bundle diagnostic. No discovery, capture, Keychain or Azure calls."""
import json
import multiprocessing
from pathlib import Path


def child(queue):
    try:
        import azure.cognitiveservices.speech
        import soundcard.coreaudio
        import numpy as np
        import soxr
        samples = soxr.resample(np.zeros(480, dtype=np.float32), 48000, 16000)
        queue.put({'imports': True, 'resampled_frames': len(samples)})
    except Exception:
        queue.put({'imports': False})


def run(report_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from liltide.gui_settings import Preferences, MacCredentials, AzureSetupDialog
    from liltide.gui_window import MainWindow
    # Imports and a real frozen spawn, without entering either live audio worker.
    context = multiprocessing.get_context('spawn')
    queue = context.Queue(maxsize=1)
    process = context.Process(target=child, args=(queue,))
    process.start()
    try:
        child_result = queue.get(timeout=20)
    finally:
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)
        queue.close()
        queue.join_thread()
    app = QApplication.instance() or QApplication([])
    # Temporary settings are kept beside the explicitly requested diagnostic report.
    # Never use the operator's preferences or Keychain in this mode.
    preferences = Preferences(QSettings(str(Path(report_path).with_suffix('.ini')), QSettings.Format.IniFormat))
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline diagnostic cannot start discovery, capture, provider or Keychain')
    credentials = MacCredentials(forbidden)
    window = MainWindow(discovery_factory=forbidden, worker_factory=forbidden,
                        credentials=credentials, preferences=preferences)
    window.show()
    app.processEvents()
    dialog = AzureSetupDialog(credentials, window)
    dialog.show()
    app.processEvents()
    result = {'frozen_spawn': process.exitcode == 0, 'child': child_result,
              'gui': window.isVisible(), 'setup_dialog': dialog.isVisible(),
              'audio_started': window.worker is not None,
              'platform': app.platformName()}
    dialog.reject()
    window.close()
    app.processEvents()
    Path(report_path).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return 0 if (result['frozen_spawn'] and child_result.get('imports') and
                 child_result.get('resampled_frames') == 160 and result['gui'] and
                 result['setup_dialog'] and not result['audio_started']) else 1
