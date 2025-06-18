from flask import Flask 
from flask_cors import CORS
import os

from dotenv import load_dotenv
load_dotenv()

from routes.chatbotRoutes import chat_blueprint
from routes.resumeRoutes import resumeProcessBlueprint
from routes.candidateRoutes import candidateBlueprint


app = Flask(__name__)
CORS(app)

# Register routes
app.register_blueprint(candidateBlueprint)
app.register_blueprint(chat_blueprint)
app.register_blueprint(resumeProcessBlueprint)

if __name__ == '__main__':
    # Get port from environment variable (Render sets this) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Run on all interfaces (0.0.0.0) instead of just localhost
    app.run(host='0.0.0.0', port=port, debug=False)

