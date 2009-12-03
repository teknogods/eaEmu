import os
SEQUENCE = [x.rsplit('.', 1)[0] for x in os.listdir(os.path.dirname(__file__)) if x.endswith('.py') and '__init__' not in x]
