from flask import Flask

app = Flask(__name__)
app.secret_key = 'keysecret'

import route

# if __name__ == '__main__':
#     app.run()
