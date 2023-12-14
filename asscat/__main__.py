import os
import sys
import uvloop

# Add parent dir to module search paths
# workaround for 'textual run __main__.py --dev'
this = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(this))

from asscat.utils import build_arg_parser
from asscat.tui.ac_app import AssCatApp


async def main():
    args = build_arg_parser()

    app = AssCatApp()
    await app.run_async()


if __name__ == '__main__':
    uvloop.run(main=main(), debug=True)
    sys.exit(0)
