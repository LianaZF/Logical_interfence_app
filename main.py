"""Точка запуска программы логического вывода."""

import argparse

from inference_app.app import InferenceApp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--rules")
    parser.add_argument("--data")
    arguments, _unknown = parser.parse_known_args()
    application = InferenceApp()
    application.load_startup_files(arguments.rules, arguments.data)
    application.mainloop()
