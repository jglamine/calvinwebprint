import sys
from printapp import app

if __name__ == '__main__':
    try:
        debug = sys.argv[1] == 'debug'
    except IndexError:
        debug = False

    app.run(debug=debug, port=5001)
