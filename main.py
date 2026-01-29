import os 
from Data.loader import loader
from Data.features.parser import parsing
from Data.features.builder import build
from dotenv import load_dotenv

load_dotenv()
data = loader(os.getenv('DATASET_PATH'))
parsed = data['result'].apply(parsing)
data = build(parsed_result=parsed, df=data)
print(data)